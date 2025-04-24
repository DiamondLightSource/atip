"""Module containing an interface with the AT simulator."""

import asyncio
import concurrent
import logging
from dataclasses import dataclass
from warnings import warn

import at
import numpy
from numpy.typing import ArrayLike
from pytac.exceptions import DataSourceException, FieldException
from scipy.constants import speed_of_light


@dataclass
class LatticeData:
    twiss: ArrayLike
    tunes: ArrayLike
    chrom: ArrayLike
    emittance: ArrayLike
    radint: ArrayLike


def calculate_optics(
    at_lattice: at.lattice_object.Lattice,
    refpts: ArrayLike,
    disable_emittance: bool = False,
) -> LatticeData:
    """Perform the physics calculations on the lattice.

    .. Note:: We choose to use the more physically accurate find_orbit6 and
       linopt6 functions over their faster but less representative 4d or 2d
       equivalents (find_orbit4, linopt2, & linopt4), see the docstrings for
       those functions in PyAT for more information.

    Args:
        at_lattice (at.lattice_object.Lattice): AT lattice definition.
        refpts (numpy.typing.NDArray): A boolean array specifying the points at which
                               to calculate physics data.
        disable_emittance (bool): whether to calculate emittance.

    Returns:
        LatticeData: The calculated lattice data.
    """
    try:
        logging.debug("Starting physics calculations.")

        orbit0, _ = at_lattice.find_orbit6()
        logging.debug("Completed orbit calculation.")

        _, beamdata, twiss = at_lattice.linopt6(
            refpts=refpts, get_chrom=True, orbit=orbit0, keep_lattice=True
        )
        logging.debug("Completed linear optics calculation.")

        if not disable_emittance:
            emitdata = at_lattice.ohmi_envelope(orbit=orbit0, keep_lattice=True)
            logging.debug("Completed emittance calculation")
        else:
            emitdata = ()
        radint = at_lattice.get_radiation_integrals(twiss=twiss)
        logging.debug("All calculation complete.")
        return LatticeData(
            twiss, beamdata.tune, beamdata.chromaticity, emitdata, radint
        )
    except Exception as e:
        warn(at.AtWarning(e), stacklevel=1)
        return None


class ATSimulator:
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
           _rp (numpy.typing.NDArray): A boolean array to be used as refpts for the
                               physics calculations.
            _disable_emittance (bool): Whether or not to perform the beam
                                        envelope based emittance calculations.
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

    _loop: asyncio.BaseEventLoop
    _queue: asyncio.Queue
    _paused: asyncio.Event
    _quit_thread: asyncio.Event
    _up_to_date: asyncio.Event
    _compute_task: asyncio.Task

    @classmethod
    async def create(cls, at_lattice, callback=None, disable_emittance=False):
        """
        .. Note:: To avoid errors, the physics data must be initially
           calculated here, during creation, otherwise it could be accidentally
           referenced before the _lattice_data attribute exists due to
           delay between class creation and the end of the first calculation in
           the thread.

        Args:
            at_lattice (at.lattice_object.Lattice): An instance of an AT
                                                     lattice object.
            callback (typing.Callable): Optional, if passed it is called on completion
                                  of each round of physics calculations.
            disable_emittance (bool): Whether or not to perform the beam
                                       envelope based emittance calculations.

        **Methods:**
        """
        self = cls()
        if (not callable(callback)) and (callback is not None):
            raise TypeError(
                f"If passed, 'callback' should be callable, {callback} is not."
            )
        self._at_lat = at_lattice
        self._rp = numpy.ones(len(at_lattice) + 1, dtype=bool)
        self._disable_emittance = disable_emittance
        self._at_lat.radiation_on()

        # Initial phys data calculation.
        self._lattice_data = calculate_optics(
            self._at_lat, self._rp, self._disable_emittance
        )

        self._loop = asyncio.get_event_loop()  # TODO: check a loop is running
        self._queue = asyncio.Queue()
        self._paused = asyncio.Event()
        self._quit_thread = asyncio.Event()
        self._up_to_date = asyncio.Event()
        self._up_to_date.set()
        self._new_setpoint = asyncio.Event()
        self._lock = asyncio.Lock()

        self._compute_task = asyncio.create_task(
            self._recalculate_phys_data(callback)
        )  # This task should last the lifetime of the program
        return self

    async def queue_set(self, func, field, value):
        """Add a change to the queue, to be applied when the queue is emptied.

        Args:
            func (typing.Callable): The function to be called to apply the change.
            field (str): The field to be changed.
            value (float): The value to be set.
        """
        await self._queue.put((func, field, value))
        # If this flag gets cleared while we are recalculating, then it can cause
        # everything to lock, so we setup a lock between this function and the
        # recalculate function
        logging.debug(f"Added task to async queue. qsize={self._queue.qsize()}")

    async def _gather_one_sample(self):
        """If the queue is empty Wait() yields until an item is added. When the
        queue is not empty the oldest change will be removed and applied to the
        AT lattice.
        """
        logging.debug("Waiting for new item in queue")
        apply_change_method, field, value = await self._queue.get()
        apply_change_method(field, value)
        logging.debug("Processed item from queue")

    async def quit_calculation_thread(self, timeout=10):
        """Quit the calculation thread after the current loop is complete."""
        await self._quit_thread.set()
        await self.trigger_calculation()
        await asyncio.wait_for(self._calculation_thread.Wait, timeout)
        # TODO: Catch timeout exception
        # For some reason we have to wait a bit before we can clear the queue.
        await asyncio.sleep(0.1)
        tasks = asyncio.all_tasks()
        for task in tasks:
            await task.cancel()

    async def _recalculate_phys_data(self, callback):
        """Target function for the Cothread thread. Recalculates the physics
        data dependent on the status of the '_paused' flag and the length of
        the queue. The calculations only take place if '_paused' is False and
        there are one or more changes on the queue.

        .. Note:: If an error or exception is raised in the running thread then
           it does not continue running so subsequent calculations are not
           performed. To fix this we convert all errors raised inside the
           thread to warnings.

        Args:
            callback (typing.Callable): to be called after each round of calculations,
                                  indicating that they have concluded.

        Warns:
            at.AtWarning: any error or exception that was raised in the thread,
                           but as a warning.
        """
        logging.debug("Starting recalculation loop")
        # Using Cothread Event is only ~4% slower than a normal Boolean but much safer.
        while not self._quit_thread.is_set():
            # We lock for the remainder of the function, to make sure that the
            # _up_to_date flag isnt reset before we run the callback which may
            # look at this
            await self._gather_one_sample()
            while not self._queue.empty():
                await self._gather_one_sample()
            logging.debug("Recaulculating simulation with new setpoints.")
            if not self._paused.is_set():
                # we run the cpu intensive calculate_optics() function in a seperate
                # process which allows us to continue servicing CA requests while doing
                # the physics
                with concurrent.futures.ProcessPoolExecutor() as pool:
                    data = await self._loop.run_in_executor(
                        pool,
                        calculate_optics,
                        self._at_lat,
                        self._rp,
                        self._disable_emittance,
                    )
                    if data is not None:
                        # Sometimes the data is non if an exception is raised during
                        # calculate_optics().
                        # TODO: If data is none we dont update the lattice and so dont
                        # need to update the output pvs.
                        self._lattice_data = data
                # Signal the up to date flag since the physics data is now up to
                # date. We do this before the callback is executed in case the
                # callback checks the flag.
                self._up_to_date.set()
                logging.debug("Simulation up to date.")
                if callback is not None:
                    logging.debug(f"Executing callback function: {callback.__name__}")
                    await callback()
                    logging.debug("Callback completed.")
                self._up_to_date.clear()

    def toggle_calculations(self):
        """Pause or unpause the physics calculations by setting or clearing the
        _paused flag.

        .. Note:: This does not pause the emptying of the queue.
        """
        if self._paused:
            self._paused.clear()
        else:
            self._paused.set()

    def pause_calculations(self):
        """Pause the physics calculations by setting the _paused flag.

        .. Note:: This does not pause the emptying of the queue.
        """
        if not self._paused:
            self._paused.set()

    async def unpause_calculations(self):
        """Unpause the physics calculations by clearing the _paused flag."""
        if self._paused.is_set():
            await self._paused.clear()
            if not self._up_to_date:
                await self.trigger_calculation()

    async def trigger_calculation(self):
        """Unpause the physics calculations and add a null item to the queue to
        trigger a recalculation.

        .. Note:: This method does not wait for the recalculation to complete,
           that is up to the user.
        """
        await self.unpause_calculations()
        self.queue_set(lambda *x: None, None, None)

    async def wait_for_calculations(self, timeout=10):
        """Wait until the physics calculations have taken account of all
        changes to the AT lattice, i.e. the physics data is fully up to date.

        Args:
            timeout (float, typing.Optional): The number of seconds to wait for.

        Returns:
            bool: False if the timeout elapsed before the calculations
            concluded, else True.
        """
        try:
            await asyncio.wait_for(self._up_to_date.wait(), timeout)
            return True
        except asyncio.exceptions.TimeoutError:
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
            pytac.FieldException: if the specified field is not valid for tune.
        """
        tunes = self._lattice_data.tunes
        if field is None:
            return numpy.array(tunes) % 1
        elif field == "x":
            return tunes[0] % 1
        elif field == "y":
            return tunes[1] % 1
        else:
            raise FieldException(f"Field {field} is not a valid tune plane.")

    def get_chromaticity(self, field=None):
        """Return the chromaticity for the AT lattice for the specified plane.

        Args:
            field (str): The desired field (x or y) of chromaticity, if None
                          return both chromaticity dimensions.

        Returns:
            float: The x or y chromaticity for the AT lattice.

        Raises:
            pytac.FieldException: if the specified field is not valid for
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
            raise FieldException(f"Field {field} is not a valid chromaticity plane.")

    # Get local linear optics data:
    def get_orbit(self, field=None):
        """Return the closed orbit at each element in the AT lattice for the
        specified plane.

        Args:
            field (str): The desired field (x, px, y, or py) of closed orbit,
                          if None return whole orbit vector.

        Returns:
            numpy.typing.NDArray: The x, x phase, y or y phase for the AT lattice as an
            array of floats the length of the AT lattice.

        Raises:
            pytac.FieldException: if the specified field is not valid for orbit.
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
            raise FieldException(f"Field {field} is not a valid closed orbit plane.")

    def get_dispersion(self, field=None):
        """Return the dispersion at every element in the AT lattice for the
        specified plane.

        Args:
            field (str): The desired field (x, px, y, or py) of dispersion, if
                          None return whole dispersion vector.

        Returns:
            numpy.typing.NDArray: The eta x, eta prime x, eta y or eta prime y for the
            AT lattice as an array of floats the length of the AT lattice.

        Raises:
            pytac.FieldException: if the specified field is not valid for dispersion.
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
            raise FieldException(f"Field {field} is not a valid dispersion plane.")

    def get_alpha(self):
        """Return the alpha vector at every element in the AT lattice.

        Returns:
            numpy.typing.NDArray: The alpha vector for each element.
        """
        return self._lattice_data.twiss["alpha"][:-1]

    def get_beta(self):
        """Return the beta vector at every element in the AT lattice.

        Returns:
            numpy.typing.NDArray: The beta vector for each element.
        """
        return self._lattice_data.twiss["beta"][:-1]

    def get_mu(self):
        """Return mu at every element in the AT lattice.

        Returns:
            numpy.typing.NDArray: The mu array for each element.
        """
        return self._lattice_data.twiss["mu"][:-1]

    def get_m66(self):
        """Return the 6x6 transfer matrix for every element in the AT lattice.

        Returns:
            numpy.typing.NDArray: The 6x6 transfer matrix for each element.
        """
        return self._lattice_data.twiss["M"][:-1]

    # Get lattice emittance from beam envelope:
    def get_emittance(self, field=None):
        """Return the emittance for the AT lattice for the specified plane.

        .. Note:: The emittance at the entrance of the AT lattice is returned
           as it is constant throughout the lattice, and so which element's
           emittance is returned is arbitrary.

        Args:
            field (str): The desired field (x or y) of emittance, if None
                          return both emittance dimensions.

        Returns:
            float: The x or y emittance for the AT lattice.

        Raises:
            pytac.FieldException: if the specified field is not valid for emittance.
        """
        if not self._disable_emittance:
            if field is None:
                return self._lattice_data.emittance[0]["emitXY"]
            elif field == "x":
                return self._lattice_data.emittance[0]["emitXY"][0]
            elif field == "y":
                return self._lattice_data.emittance[0]["emitXY"][1]
            else:
                raise FieldException(f"Field {field} is not a valid emittance plane.")
        else:
            raise DataSourceException(
                "Emittance calculations not enabled on this simulator object."
            )

    # Get lattice data from radiation integrals:
    def get_radiation_integrals(self):
        """Return the 5 Synchrotron Integrals for the AT lattice.

        Returns:
            numpy.typing.NDArray: The 5 radiation integrals.
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
        gamma = self.get_energy() / (at.constants.e_mass)
        return gamma * numpy.sqrt((at.constants.Cq * I3) / ((2 * I2) + I4))

    def get_energy_loss(self):
        """Return the energy loss per turn of the AT lattice.

        Returns:
            float: The energy loss of the AT lattice.
        """
        _, I2, _, _, _ = self._lattice_data.radint
        return (at.constants.Cgamma * I2 * self.get_energy() ** 4) / (2 * numpy.pi)

    def get_damping_partition_numbers(self):
        """Return the damping partition numbers for the 3 normal modes.

        Returns:
            numpy.typing.NDArray: The damping partition numbers of the AT lattice.
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
            numpy.typing.NDArray: The damping times of the AT lattice.
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
        gamma = self.get_energy() / (at.constants.e_mass)
        return (I5 * at.constants.Cq * gamma**2) / (I2 - I4)
