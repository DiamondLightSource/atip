"""Module containing an interface with the AT simulator."""
from warnings import warn

import at
import numpy
import cothread
from scipy.constants import speed_of_light
from pytac.exceptions import FieldException


class ATSimulator(object):
    """A centralised class which makes use of AT to simulate the physics data
    for the copy of the AT lattice which it holds. It works as follows, when a
    change is made to the lattice in Pytac it is added to the queue attribute
    of this class. When the queue has changes on it  a recalculation is
    triggered, all the changes are applied to the lattice and then the physics
    data calculated. This ensures that the physics data is up to date.

    **Attributes**

    Attributes:
        queue (cothread.EventQueue): A queue of changes to be made to the
                                      lattice on the next recalculation cycle.
        up_to_date (cothread.Event): A flag that indicates if the physics data
                                      is up to date with all the changes made
                                      to the AT lattice.

    .. Private Attributes:
           _at_lat (at.lattice_object.Lattice): The centralised instance of an
                                                 AT lattice from which the
                                                 physics data is calculated.
           _rp (numpy.array): A boolean array to be used as refpts for the
                               physics calculations.
           _emitdata (tuple): Emittance, the output of the AT physics function
                               ohmi_envelope (see at.lattice.radiation.py).
           _lindata (tuple): Linear optics data, the output of the AT physics
                              function linopt (see at.lattice.linear.py).
           _paused (cothread.Event): A flag used to temporarily pause the
                                      physics calculations.
           _calculation_thread (cothread.Thread): A thread to check the queue
                                                    for new changes to the AT
                                                    lattice and recalculate the
                                                    physics data upon a change.
    """
    def __init__(self, at_lattice, callback=None):
        """
        .. Note:: To avoid errors, the physics data must be initially
           calculated here, during creation, otherwise it could be accidentally
           referenced before the attributes _emitdata and _lindata exist due to
           delay between class creation and the end of the first calculation in
           the thread.

        Args:
            at_lattice (at.lattice_object.Lattice): An instance of an AT
                                                     lattice object.
            callback (callable): Optional, if passed it is called on completion
                                  of each round of physics calculations.

        **Methods:**
        """
        if (not callable(callback)) and (callback is not None):
            raise TypeError("If passed, 'callback' should be callable, {0} is "
                            "not.".format(callback))
        self._at_lat = at_lattice
        self._rp = numpy.ones(len(at_lattice)+1, dtype=bool)
        # Initial phys data calculation.
        self._at_lat.radiation_on()
        self._emitdata = self._at_lat.ohmi_envelope(self._rp)
        self._at_lat.radiation_off()
        self._lindata = self._at_lat.linopt(refpts=self._rp, get_chrom=True,
                                            coupled=False)
        # Threading stuff initialisation.
        self.queue = cothread.EventQueue()
        self.up_to_date = cothread.Event()
        self.up_to_date.Signal()
        self._paused = cothread.Event()
        self._calculation_thread = cothread.Spawn(self._recalculate_phys_data,
                                                  callback)

    def _gather_one_sample(self):
        """If the queue is empty Wait() yields until an item is added. When the
        queue is not empty the oldest change will be removed and applied to the
        AT lattice.
        """
        apply_change_method, field, value = self.queue.Wait()
        apply_change_method(field, value)

    def _recalculate_phys_data(self, callback):
        """Target function for the Cothread thread. Recalculates the physics
        data dependant on the status of the '_paused' flag and the length of
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
            self._gather_one_sample()
            for _ in range(len(self.queue)):
                self._gather_one_sample()
            if bool(self._paused) is False:
                try:
                    self._at_lat.radiation_on()
                    self._emitdata = self._at_lat.ohmi_envelope(self._rp)
                    self._at_lat.radiation_off()
                    self._lindata = self._at_lat.linopt(0.0, self._rp, True,
                                                        coupled=False)
                except Exception as e:
                    warn(at.AtWarning(e))
                if callback is not None:
                    callback()
                self.up_to_date.Signal()

    def toggle_calculations(self):
        """Pause or unpause the physics calculations by setting or clearing the
        _paused flag. N.B. this does not pause the emptying of the queue.
        """
        if bool(self._paused) is False:
            self._paused.Signal()
        else:
            self._paused.Reset()

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

    def get_chrom(self, field):
        """Return the chromaticity for the AT lattice for the specified plane.

        Args:
            field (str): The desired field (x or y) of chromaticity.

        Returns:
            float: The x or y chromaticity for the AT lattice.

        Raises:
            FieldException: if the specified field is not valid for
                             chromaticity.
        """
        if field == 'x':
            return self._lindata[2][0]
        elif field == 'y':
            return self._lindata[2][1]
        else:
            raise FieldException("Field {0} is not a valid chromaticity "
                                 "plane.".format(field))

    def get_emit(self, field):
        """Return the emittance for the AT lattice for the specified plane.

        .. Note:: The emittance of the first element is returned as it is
           constant throughout the AT lattice, and so which element's emittance
           is returned is arbitrary.

        Args:
            field (str): The desired field (x or y) of emittance.

        Returns:
            float: The x or y emittance for the AT lattice.

        Raises:
            FieldException: if the specified field is not valid for emittance.
        """
        if field == 'x':
            return self._emitdata[0]['emitXY'][0]
        elif field == 'y':
            return self._emitdata[0]['emitXY'][1]
        else:
            raise FieldException("Field {0} is not a valid emittance plane."
                                 .format(field))

    def get_orbit(self, field):
        """Return the closed orbit for the AT lattice for the specified plane.

        Args:
            field (str): The desired field (x, px, y, or py) of closed orbit.

        Returns:
            numpy.array: The x, x phase, y or y phase for the AT lattice as an
            array of floats the length of the AT lattice.

        Raises:
            FieldException: if the specified field is not valid for orbit.
        """
        if field == 'x':
            return self._lindata[3]['closed_orbit'][:-1, 0]
        elif field == 'px':
            return self._lindata[3]['closed_orbit'][:-1, 1]
        elif field == 'y':
            return self._lindata[3]['closed_orbit'][:-1, 2]
        elif field == 'py':
            return self._lindata[3]['closed_orbit'][:-1, 3]
        else:
            raise FieldException("Field {0} is not a valid closed orbit plane."
                                 .format(field))

    def get_tune(self, field):
        """Return the tune for the AT lattice for the specified plane.

        .. Note:: A special consideration is made so only the fractional digits
           of the tune are returned.

        Args:
            field (str): The desired field (x or y) of tune.

        Returns:
            float: The x or y tune for the AT lattice.

        Raises:
            FieldException: if the specified field is not valid for tune.
        """
        if field == 'x':
            return (self._lindata[1][0] % 1)
        elif field == 'y':
            return (self._lindata[1][1] % 1)
        else:
            raise FieldException("Field {0} is not a valid tune plane."
                                 .format(field))

    def get_disp(self):
        """Return the dispersion at every element in the AT lattice.

        Returns:
            numpy.array: The dispersion vector for each element.
        """
        return self._lindata[3]['dispersion'][:-1]

    def get_s(self):
        """Return the s position of every element in the AT lattice

        Returns:
            list: The s position of each element.
        """
        return list(self._lindata[3]['s_pos'][:-1])

    def get_energy(self):
        """Return the energy of the AT lattice. Taken from the AT attribute.

        Returns:
            float: The energy of the AT lattice.
        """
        return self._at_lat.energy

    def get_alpha(self):
        """Return the alpha vector at every element in the AT lattice.

        Returns:
            numpy.array: The alpha vector for each element.
        """
        return self._lindata[3]['alpha'][:-1]

    def get_beta(self):
        """Return the beta vector at every element in the AT lattice.

        Returns:
            numpy.array: The beta vector for each element.
        """
        return self._lindata[3]['beta'][:-1]

    def get_m44(self):
        """Return the 4x4 transfer matrix for every element in the AT lattice.

        Returns:
            numpy.array: The 4x4 transfer matrix for each element.
        """
        return self._lindata[3]['m44'][:-1]

    def get_mu(self):
        """Return mu at every element in the AT lattice.

        Returns:
            numpy.array: The mu array for each element.
        """
        return self._lindata[3]['mu'][:-1]

    def get_energy_spread(self):
        """Return the energy spread for the AT lattice.

        Returns:
            float: The energy spread for the AT lattice.
        """
        return numpy.sqrt(self._emitdata[0]['r66'][4, 4])

    def get_mcf(self):
        """Return the linear momentum compaction factor for the AT lattice.

        Returns:
            float: The linear momentum compaction factor of the AT lattice.
        """
        self._at_lat.radiation_off()
        return self._at_lat.get_mcf()

    def get_energy_loss(self):
        """Return the energy loss per turn of the AT lattice. Taken from the AT
        lattice property.

        Returns:
            float: The energy loss of the AT lattice.
        """
        return self._at_lat.energy_loss

    def get_damping_times(self):
        """Return the damping times for the 3 normal modes.

        Returns:
            numpy.array: The damping times of the AT lattice.
        """
        T0 = self.get_s()[-1] / speed_of_light
        return T0 / self._emitdata[1]['damping_rates']

    def get_damping_partition_numbers(self):
        """Return the damping partition numbers for the 3 normal modes.

        Returns:
            numpy.array: The damping partition numbers of the AT lattice.
        """
        dt = self.get_damping_times()
        return 4.0 / (dt * sum(dt**-1))

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

    def get_rad_int(self):
        self._at_lat.radiation_off()
        return self._at_lat.get_radiation_integrals(twiss=self._lindata[3])

    def get_lda(self):
        I1, I2, I3, I4, I5 = self.get_rad_int()
        return I5/I2

    def get_dpn(self):
        I1, I2, I3, I4, I5 = self.get_rad_int()
        Jx = 1-(I4/I2)
        Je = 2+(I4/I2)
        Jy = 4-(Jx+Je)  # Check they sum to 4, don't just assume Jy is 1.
        return Jx, Jy, Je

    def get_dt(self):
        """t = (2*E0*T0)/(U0*J) [1]
        [1] A.Wolski; CERN  Accelerator School, Advanced Accelerator Physics
            Course, Low Emittance Machines, Part 1: Beam Dynamics with
            Synchrotron Radiation; August 2013; eqn. 68
        """
        I1, I2, I3, I4, I5 = self.get_rad_int()
        U0 = (at.physics.Cgamma/2/numpy.pi)*I2*self._at_lat.energy**4
        T0 = self._at_lat.circumference/speed_of_light
        return (2*T0*self._at_lat.energy)/(U0*numpy.asarray(self.get_dpn()))

    def get_espread(self):
        I1, I2, I3, I4, I5 = self.get_rad_int()
        gamma = self._at_lat.energy/(at.physics.e_mass)
        return gamma*numpy.sqrt((at.physics.Cq*I3)/(2*I2+I4))

    def get_mntm_comp(self):
        I1, I2, I3, I4, I5 = self.get_rad_int()
        return I1/self._at_lat.circumference

    def get_horizontal_emittance(self):
        I1, I2, I3, I4, I5 = self.get_rad_int()
        gamma = self._at_lat.energy/(at.physics.e_mass)
        return (I5*at.physics.Cq*gamma**2)/(I2-I4)

    def get_vertical_emittance(self):
        """In comparison to ohmi_envelope both are off by a little bit and
        a factor of 10, in different directions!
            ey1 = 10*(I6*Cq*gamma^2)/(Jy*I2)
            where:
                I6 = integral(curV/|rho^3| ds)
                Jy == 1
            ey2 = 0.2*(curVavg*I3*Cq*gamma^2)/(Jy*I2)
            where:
                curVavg*I3 = integral(curV/|rho^3| ds)
                           = <curV>*integral(1/|rho^3| ds)
        """
        I6 = 0.0
        curVavg = 0.0
        for elem in self._at_lat:
            if isinstance(elem, at.elements.Bend) and elem.BendingAngle != 0.0:
                alpha_y = self._lindata[3]['alpha'][elem.Index-1, 1]
                beta_y = self._lindata[3]['beta'][elem.Index-1, 1]
                eta_y = self._lindata[3]['dispersion'][elem.Index-1, 2]
                eta_yp = self._lindata[3]['dispersion'][elem.Index-1, 3]
                gamma_y = (1 + alpha_y**2)/beta_y
                curV = (gamma_y*eta_y**2 + 2*alpha_y*eta_y*eta_yp
                        + beta_y*eta_yp**2)
                curVavg += curV*elem.Length
                # curV*len*rho^3 = (curV*theta^3)/len^2
                I6 += curV*abs(elem.BendingAngle**3)/elem.Length**2
        _, I2, I3, _, _ = self.get_rad_int()
        gamma = self._at_lat.energy/(at.physics.e_mass)
        return [(I6*at.physics.Cq*gamma**2)/I2,
                (curVavg*I3*at.physics.Cq*gamma**2)/I2]

    def get_dispersion_action(self):
        curHavg = 0.0
        curVavg = 0.0
        I5 = 0.0
        I6 = 0.0
        for elem in self._at_lat:
            if isinstance(elem, at.elements.Dipole) and elem.BendingAngle != 0:
                idx = elem.Index - 1
                alpha_x = self._lindata[3]['alpha'][idx, 0]
                alpha_y = self._lindata[3]['alpha'][idx, 1]
                beta_x = self._lindata[3]['beta'][idx, 0]
                beta_y = self._lindata[3]['beta'][idx, 1]
                eta_x = self._lindata[3]['dispersion'][idx, 0]
                eta_xp = self._lindata[3]['dispersion'][idx, 1]
                eta_y = self._lindata[3]['dispersion'][idx, 2]
                eta_yp = self._lindata[3]['dispersion'][idx, 3]
                # gamma*eta^2 + 2*alpha*eta*eta_prime + beta*eta_prime^2
                curH = (eta_x**2 + alpha_x**2*eta_x**2 +
                        2*beta_x*alpha_x*eta_x*eta_xp + beta_x**2*eta_xp**2)
                curHavg += curH
                # (curH*len)/abs(rho^3)
                I5 += abs(curH*elem.BendingAngle**3)/elem.Length**2
                curV = (eta_y**2 + alpha_y**2*eta_y**2 +
                        2*beta_y*alpha_y*eta_y*eta_yp + beta_y**2*eta_yp**2)
                curVavg += curV
                I6 += abs(curV*elem.BendingAngle**3)/elem.Length**2
        return curHavg, curVavg, I5, I6

    def get_emit_from_curly(self):
        _, I2, I3, I4, _ = self.get_rad_int()
        curlyH, curlyV, I5, I6 = self.get_dispersion_action()
        gamma = self._at_lat.energy/(at.physics.e_mass)
        out = [(curlyH*I3*at.physics.Cq*gamma**2)/(I2-I4),
               (I5*at.physics.Cq*gamma**2)/(I2-I4),
               (curlyV*I3*at.physics.Cq*gamma**2)/I2,
               (I6*at.physics.Cq*gamma**2)/I2]
        return out
