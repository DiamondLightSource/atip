"""Module containing an interface with the AT simulator."""
import logging
from dataclasses import dataclass
from warnings import warn

import at
import numpy
from numpy.typing import ArrayLike
import cothread
from scipy.constants import speed_of_light
from pytac.exceptions import FieldException


@dataclass
class LatticeData:

    twiss: ArrayLike
    tunes: ArrayLike
    chrom: ArrayLike
    emittance: ArrayLike
    radint: ArrayLike


def calculate_optics(
    at_lattice: at.Lattice, refpts: ArrayLike, calc_emittance: bool = True
) -> LatticeData:
    """Perform physics calculations on lattice.

    Args:
        at_lattice: AT lattice definition
        refpts: points at which to calculate physics data
        calc_emittance: whether to calculate emittances

    Returns:
        calculated lattice data
    """
    logging.debug("Starting optics calculations.")

    orbit0, _ = at_lattice.find_orbit6()
    logging.debug("Completed orbit calculation.")

    # Here one could use the faster linopt2 or linopt4 functions,
    # but linopt6 appears to be more correct.
    # If you try linopt2 or linopt4 be aware that the calculated
    # data from this call may not be physically accurate.
    # See the docstrings for those functions in pyat.
    _, beamdata, twiss = at_lattice.linopt6(
        refpts=refpts, get_chrom=True, orbit=orbit0, keep_lattice=True
    )
    logging.debug("Completed linear optics calculation.")

    if calc_emittance:
        emitdata = at_lattice.ohmi_envelope(orbit=orbit0, keep_lattice=True)
        logging.debug("Completed emittance calculation")

    radint = at_lattice.get_radiation_integrals(twiss=twiss)
    logging.debug("All calculation complete.")
    return LatticeData(twiss, beamdata.tune, beamdata.chromaticity, emitdata, radint)


class ATSimulator(object):
    """A centralised class which makes use of AT to simulate the physics data
    for the copy of the AT lattice which it holds. It works as follows, when a
    change is made to the lattice in Pytac it is added to the queue attribute
    of this class. When the queue has changes on it  a recalculation is
    triggered, all the changes are applied to the lattice and then the physics
    data calculated. This ensures that the physics data is up to date.

    **Attributes**

    Attributes:
        up_to_date (cothread.Event): A flag that indicates if the physics data
                                      is up to date with all the changes made
                                      to the AT lattice.

    .. Private Attributes:
           _at_lat (at.lattice_object.Lattice): The centralised instance of an
                                                 AT lattice from which the
                                                 physics data is calculated.
           _rp (numpy.array): A boolean array to be used as refpts for the
                               physics calculations.
            _emit_calc (bool): Whether or not to perform the beam envelope
                                based emittance calculations.
           _lattice_data (LatticeData): calculated physics data
                              function linopt (see at.lattice.linear.py).
           _queue (cothread.EventQueue): A queue of changes to be applied to
                                          the centralised lattice on the next
                                          recalculation cycle.
           _paused (cothread.Event): A flag used to temporarily pause the
                                      physics calculations.
           _calculation_thread (cothread.Thread): A thread to check the queue
                                                    for new changes to the AT
                                                    lattice and recalculate the
                                                    physics data upon a change.
    """

    def __init__(self, at_lattice, callback=None, emit_calc=True):
        """
        .. Note:: To avoid errors, the physics data must be initially
           calculated here, during creation, otherwise it could be accidentally
           referenced before the _lattice_data attribute exists due to
           delay between class creation and the end of the first calculation in
           the thread.

        Args:
            at_lattice (at.lattice_object.Lattice): An instance of an AT
                                                     lattice object.
            callback (callable): Optional, if passed it is called on completion
                                  of each round of physics calculations.
            emit_calc (bool): Whether or not to perform the beam envelope based
                               emittance calculations.

        **Methods:**
        """
        if (not callable(callback)) and (callback is not None):
            raise TypeError(
                "If passed, 'callback' should be callable, {0} is "
                "not.".format(callback)
            )
        self._at_lat = at_lattice
        self._rp = numpy.ones(len(at_lattice) + 1, dtype=bool)
        self._emit_calc = emit_calc
        self._at_lat.radiation_on()

        # Initial phys data calculation.
        self._lattice_data = calculate_optics(self._at_lat, self._rp, self._emit_calc)

        # Threading stuff initialisation.
        self._queue = cothread.EventQueue()
        # Explicitly manage the cothread Events, so turn off auto_reset.
        # These are False when reset, True when signalled.
        self._paused = cothread.Event(auto_reset=False)
        self.up_to_date = cothread.Event(auto_reset=False)
        self.up_to_date.Signal()
        self._calculation_thread = cothread.Spawn(self._recalculate_phys_data, callback)

    def queue_set(self, func, field, value):
        """Add a change to the queue, to be applied when the queue is emptied.

        Args:
            func (callable): The function to be called to apply the change.
            field (str): The field to be changed.
            value (float): The value to be set.
        """
        self._queue.Signal((func, field, value))

    def _gather_one_sample(self):
        """If the queue is empty Wait() yields until an item is added. When the
        queue is not empty the oldest change will be removed and applied to the
        AT lattice.
        """
        apply_change_method, field, value = self._queue.Wait()
        apply_change_method(field, value)

    def _recalculate_phys_data(self, callback):
        """Target function for the Cothread thread. Recalculates the physics
        data dependent on the status of the '_paused' flag and the length of
        the queue. The calculations only take place if '_paused' is False and
        there is one or more changes on the queue.

        .. Note:: If an error or exception is raised in the running thread then
           it does not continue running so subsequent calculations are not
           performed. To fix this we convert all errors raised inside the
           thread to warnings.

        Args:
            callback (callable): to be called after each round of calculations,
                                  indicating that they have concluded.

        Warns:
            at.AtWarning: any error or exception that was raised in the thread,
                           but as a warning.
        """
        while True:
            logging.debug("Starting recalculation loop")
            self._gather_one_sample()
            while self._queue:
                self._gather_one_sample()
            if bool(self._paused) is False:
                try:
                    self._lattice_data = calculate_optics(
                        self._at_lat, self._rp, self._emit_calc
                    )
                except Exception as e:
                    warn(at.AtWarning(e))
                # Signal up to date before the callback is executed in case
                # the callback requires data that requires the calculation
                # to be up to date.
                self.up_to_date.Signal()
                if callback is not None:
                    logging.debug("Executing callback function.")
                    callback()
                    logging.debug("Callback completed.")

    def toggle_calculations(self):
        """Pause or unpause the physics calculations by setting or clearing the
        _paused flag. N.B. this does not pause the emptying of the queue.
        """
        if self._paused:
            self._paused.Reset()
        else:
            self._paused.Signal()

    def pause_calculations(self):
        self._paused.Signal()

    def unpause_calculations(self):
        self._paused.Reset()

    def trigger_calculation(self):
        self.up_to_date.Reset()
        self.unpause_calculations()
        # Add a null item to the queue. A recalculation will happen
        # when it has been applied.
        self.queue_set(lambda *x: None, None, None)

    def wait_for_calculations(self, timeout=10):
        """Wait until the physics calculations have taken account of all
        changes to the AT lattice, i.e. the physics data is fully up to date.

        Args:
            timeout (float, optional): The number of seconds to wait for.

        Returns:
            bool: False if the timeout elapsed before the calculations
            concluded, else True.
        """
        try:
            self.up_to_date.Wait(timeout)
            return True
        except cothread.Timedout:
            return False

    # Get lattice related data:
    def get_at_element(self, index):
        """Return the AT element corresponding to the given index.

        Args:
            index (int): The index of the AT element to return.

        Returns:
            at.elements.Element: The element specified by the given index.
        """
        return self._at_lat[index - 1]

    def get_at_lattice(self):
        """Return a copy of the AT lattice object.

        Returns:
            at.lattice_object.Lattice: A copy of the AT lattice object.
        """
        return self._at_lat.copy()

    def get_s(self):
        """Return the s position of every element in the AT lattice

        Returns:
            list: The s position of each element.
        """
        return list(self._lattice_data.twiss["s_pos"][:-1])

    def get_total_bend_angle(self):
        """Return the total bending angle of all the dipoles in the AT lattice.

        Returns:
            float: The total bending angle for the AT lattice.
        """
        theta_sum = 0.0
        for elem in self._at_lat:
            if isinstance(elem, at.lattice.elements.Dipole):
                theta_sum += elem.BendingAngle
        return numpy.degrees(theta_sum)

    def get_total_absolute_bend_angle(self):
        """Return the total absolute bending angle of all the dipoles in the
        AT lattice.

        Returns:
            float: The total absolute bending angle for the AT lattice.
        """
        theta_sum = 0.0
        for elem in self._at_lat:
            if isinstance(elem, at.lattice.elements.Dipole):
                theta_sum += abs(elem.BendingAngle)
        return numpy.degrees(theta_sum)

    def get_energy(self):
        """Return the energy of the AT lattice. Taken from the AT attribute.

        Returns:
            float: The energy of the AT lattice.
        """
        return self._at_lat.energy

    # Get global linear optics data:
    def get_tune(self, field=None):
        """Return the tune for the AT lattice for the specified plane.

        .. Note:: A special consideration is made so only the fractional digits
           of the tune are returned.

        Args:
            field (str): The desired field (x or y) of tune, if None return
                          both tune dimensions.

        Returns:
            float: The x or y tune for the AT lattice.

        Raises:
            FieldException: if the specified field is not valid for tune.
        """
        tunes = self._lattice_data.tunes
        if field is None:
            return numpy.array(tunes) % 1
        elif field == "x":
            return tunes[0] % 1
        elif field == "y":
            return tunes[1] % 1
        else:
            raise FieldException("Field {0} is not a valid tune plane.".format(field))

    def get_chromaticity(self, field=None):
        """Return the chromaticity for the AT lattice for the specified plane.

        Args:
            field (str): The desired field (x or y) of chromaticity, if None
                          return both chromaticity dimensions.

        Returns:
            float: The x or y chromaticity for the AT lattice.

        Raises:
            FieldException: if the specified field is not valid for
                             chromaticity.
        """
        chrom = self._lattice_data.chrom
        if field is None:
            return chrom
        elif field == "x":
            return chrom[0]
        elif field == "y":
            return chrom[1]
        else:
            raise FieldException(
                "Field {0} is not a valid chromaticity plane.".format(field)
            )

    # Get local linear optics data:
    def get_orbit(self, field=None):
        """Return the closed orbit at each element in the AT lattice for the
        specified plane.

        Args:
            field (str): The desired field (x, px, y, or py) of closed orbit,
                          if None return whole orbit vector.

        Returns:
            numpy.array: The x, x phase, y or y phase for the AT lattice as an
            array of floats the length of the AT lattice.

        Raises:
            FieldException: if the specified field is not valid for orbit.
        """
        closed_orbit = self._lattice_data.twiss["closed_orbit"]
        if field is None:
            return closed_orbit[:-1]
        elif field == "x":
            return closed_orbit[:-1, 0]
        elif field == "px":
            return closed_orbit[:-1, 1]
        elif field == "y":
            return closed_orbit[:-1, 2]
        elif field == "py":
            return closed_orbit[:-1, 3]
        else:
            raise FieldException(
                "Field {0} is not a valid closed orbit plane.".format(field)
            )

    def get_dispersion(self, field=None):
        """Return the dispersion at every element in the AT lattice for the
        specified plane.

        Args:
            field (str): The desired field (x, px, y, or py) of dispersion, if
                          None return whole dispersion vector.

        Returns:
            numpy.array: The eta x, eta prime x, eta y or eta prime y for the
            AT lattice as an array of floats the length of the AT lattice.

        Raises:
            FieldException: if the specified field is not valid for dispersion.
        """
        dispersion = self._lattice_data.twiss["dispersion"]
        if field is None:
            return dispersion[:-1]
        elif field == "x":
            return dispersion[:-1, 0]
        elif field == "px":
            return dispersion[:-1, 1]
        elif field == "y":
            return dispersion[:-1, 2]
        elif field == "py":
            return dispersion[:-1, 3]
        else:
            raise FieldException(
                "Field {0} is not a valid dispersion plane.".format(field)
            )

    def get_alpha(self):
        """Return the alpha vector at every element in the AT lattice.

        Returns:
            numpy.array: The alpha vector for each element.
        """
        return self._lattice_data.twiss["alpha"][:-1]

    def get_beta(self):
        """Return the beta vector at every element in the AT lattice.

        Returns:
            numpy.array: The beta vector for each element.
        """
        return self._lattice_data.twiss["beta"][:-1]

    def get_mu(self):
        """Return mu at every element in the AT lattice.

        Returns:
            numpy.array: The mu array for each element.
        """
        return self._lattice_data.twiss["mu"][:-1]

    def get_m66(self):
        """Return the 6x6 transfer matrix for every element in the AT lattice.

        Returns:
            numpy.array: The 6x6 transfer matrix for each element.
        """
        return self._lattice_data.twiss["M"][:-1]

    # Get lattice emittance from beam envelope:
    def get_emittance(self, field=None):
        """Return the emittance for the AT lattice for the specified plane.

        .. Note:: The emittance at the entrance of the AT lattice as it is
           constant throughout the lattice, and so which element's emittance
           is returned is arbitrary.

        Args:
            field (str): The desired field (x or y) of emittance, if None
                          return both emittance dimensions.

        Returns:
            float: The x or y emittance for the AT lattice.

        Raises:
            FieldException: if the specified field is not valid for emittance.
        """
        if field is None:
            return self._lattice_data.emittance[0]["emitXY"]
        elif field == "x":
            return self._lattice_data.emittance[0]["emitXY"][0]
        elif field == "y":
            return self._lattice_data.emittance[0]["emitXY"][1]
        else:
            raise FieldException(
                "Field {0} is not a valid emittance plane.".format(field)
            )

    # Get lattice data from radiation integrals:
    def get_radiation_integrals(self):
        """Return the 5 Synchrotron Integrals for the AT lattice.

        Returns:
            numpy.array: The 5 radiation integrals.
        """
        return numpy.asarray(self._lattice_data.radint)

    def get_momentum_compaction(self):
        """Return the linear momentum compaction factor for the AT lattice.

        Returns:
            float: The linear momentum compaction factor of the AT lattice.
        """
        I1, _, _, _, _ = self._lattice_data.radint
        return I1 / self._lattice_data.twiss["s_pos"][-1]

    def get_energy_spread(self):
        """Return the energy spread for the AT lattice.

        Returns:
            float: The energy spread for the AT lattice.
        """
        _, I2, I3, I4, _ = self._lattice_data.radint
        gamma = self.get_energy() / (at.physics.e_mass)
        return gamma * numpy.sqrt((at.physics.Cq * I3) / ((2 * I2) + I4))

    def get_energy_loss(self):
        """Return the energy loss per turn of the AT lattice.

        Returns:
            float: The energy loss of the AT lattice.
        """
        _, I2, _, _, _ = self._lattice_data.radint
        return (at.physics.Cgamma * I2 * self.get_energy() ** 4) / (2 * numpy.pi)

    def get_damping_partition_numbers(self):
        """Return the damping partition numbers for the 3 normal modes.

        Returns:
            numpy.array: The damping partition numbers of the AT lattice.
        """
        _, I2, _, I4, _ = self._lattice_data.radint
        Jx = 1 - (I4 / I2)
        Je = 2 + (I4 / I2)
        Jy = 4 - (Jx + Je)  # Check they sum to 4, don't just assume Jy is 1.
        return numpy.asarray([Jx, Jy, Je])

    def get_damping_times(self):
        """Return the damping times for the 3 normal modes.
        [tx, ty, tz] = (2*E0*T0)/(U0*[Jx, Jy, Jz]) [1]
        [1] A.Wolski; CERN  Accelerator School, Advanced Accelerator Physics
        Course, Low Emittance Machines, Part 1: Beam Dynamics with Synchrotron
        Radiation; August 2013; eqn. 68

        Returns:
            numpy.array: The damping times of the AT lattice.
        """
        E0 = self.get_energy()
        U0 = self.get_energy_loss()
        T0 = self._at_lat.circumference / speed_of_light
        return (2 * T0 * E0) / (U0 * self.get_damping_partition_numbers())

    def get_linear_dispersion_action(self):
        """Return the Linear Dispersion Action ("curly H") for the AT lattice.

        Returns:
            float: Curly H for the AT lattice
        """
        _, I2, _, _, I5 = self._lattice_data.radint
        return I5 / I2

    def get_horizontal_emittance(self):
        """Return the horizontal emittance for the AT lattice calculated from
        the radiation integrals, as opposed to the beam envelope formalism
        used by AT's ohmi_envelope function.

        Returns:
            float: The horizontal ('x') emittance for the AT lattice.
        """
        _, I2, _, I4, I5 = self._lattice_data.radint
        gamma = self.get_energy() / (at.physics.e_mass)
        return (I5 * at.physics.Cq * gamma ** 2) / (I2 - I4)
