"""Module containing an interface with the AT simulator."""
from threading import Thread, Event
from warnings import warn

import at
import numpy


class ATSimulator(object):
    """A centralised class which makes use of AT to simulate the physics data
    for the copy of the AT lattice which it holds. This class ensures that this
    data is up to date through the use of threading, a thread constantly runs
    in the background and recalculates the physics data every time a change is
    made via the use of flags (threading events).

    **Attributes**

    Attributes:
        up_to_date (threading.Event): A flag that indicates if the physics data
                                       is up to date with all the changes made
                                       to the AT lattice.

    .. Private Attributes:
           _at_lattice (at.lattice_object.Lattice): The centralised instance of
                                                     an AT lattice from which
                                                     the physics data is
                                                     calculated.
           _rp (numpy.array): A boolean array to be used as refpoints for the
                               physics calculations.
           _emittance (tuple): Emittance, the output of the AT physics function
                                ohmi_envelope (see at.lattice.radiation.py).
           _lindata (tuple): Linear optics data, the output of the AT physics
                              function linopt (see at.lattice.linear.py).
           _paused (threading.Event): A flag used to temporarily pause the
                                       physics calculations.
           _running (threading.Event): A flag used to indicate if the thread is
                                        running or not, it is also used to turn
                                        the thread off.
           _calculation_thread (threading.Thread): A thread to constantly check
                                                    for new changes to the AT
                                                    lattice and recalculate the
                                                    physics data upon a change.
    """
    def __init__(self, at_lattice, callback=None):
        """
        .. Note:: To avoid errors, the physics data must be initially
           calculated here, during creation, otherwise it could be accidentally
           referenced before the attributes _emittance and _lindata exist due
           to delay between class creation and the end of the first calculation
           in the thread.

        Args:
            at_lattice (at.lattice_object.Lattice): An instance of an AT
                                                     lattice object.
            callback (callable): To be called after completion of each round of
                                  physics calculations.

        **Methods:**
        """
        if (not callable(callback)) and (callback is not None):
            raise TypeError("If passed, 'callback' should be callable, {0} is "
                            "not.".format(callback))
        self._at_lattice = at_lattice
        self._rp = numpy.ones(len(at_lattice), dtype=bool)
        # Initial phys data calculation.
        self._at_lattice.radiation_on()
        self._emittance = self._at_lattice.ohmi_envelope(self._rp)
        self._at_lattice.radiation_off()
        self._lindata = self._at_lattice.linopt(refpts=self._rp,
                                                get_chrom=True, coupled=False)
        # Threading stuff initialisation.
        self.up_to_date = Event()
        self.up_to_date.set()
        self._paused = Event()
        self._running = Event()
        self._calculation_thread = Thread(target=self._recalculate_phys_data,
                                          name='atip_calculation_thread',
                                          args=[callback])

    def start_thread(self):
        """Start the thread created in __init__ in the background. This
        function is separated from __init__ so that multiple Accelerator Data
        objects can be created without the need to waste processing power on
        threads when they are not required.

        Raises:
            RuntimeError: if the thread has already been started.
        """
        if self._running.is_set() is False:
            self._calculation_thread.setDaemon(True)
            self._running.set()
            self._calculation_thread.start()
        else:
            raise RuntimeError("Cannot start thread as it is already running.")

    def _recalculate_phys_data(self, callback):
        """Target function for the background thread. Recalculates the physics
        data dependant on the status of the '_paused' and 'up_to_date' flags.
        The thread is constantly running but the calculations only take place
        if both flags are False.

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
            if self._running.is_set() is False:
                return
            elif (self.up_to_date.is_set() or self._paused.is_set()) is False:
                try:
                    self._at_lattice.radiation_on()
                    self._emittance = self._at_lattice.ohmi_envelope(self._rp)
                    self._at_lattice.radiation_off()
                    self._lindata = self._at_lattice.linopt(refpts=self._rp,
                                                            get_chrom=True,
                                                            coupled=False)
                except Exception as e:
                    warn(at.AtWarning(e))
                if callback is not None:
                    callback()
                self.up_to_date.set()

    def stop_thread(self):
        """Stop the recalculation thread if it is running. This enables threads
        to be switched off when they are not being used so they do not
        unnecessarily use processing power. We join the thread to block until
        it has finished.

        Raises:
            RuntimeError: if the thread is not yet running.
        """
        if self._running.is_set() is True:
            self._running.clear()
            self._calculation_thread.join()
        else:
            raise RuntimeError("Cannot stop thread as it is not running.")

    def toggle_calculations(self):
        """Pause or unpause the physics calculations by setting or clearing the
        _paused flag.
        """
        if self._paused.is_set() is False:
            self._paused.set()
        else:
            self._paused.clear()

    def wait_for_calculations(self, timeout=10):
        """Wait until the physics calculations have taken account of all
        changes to the AT lattice, i.e. the physics data is fully up to date.

        Args:
            timeout (float, optional): The number of seconds to wait for.

        Returns:
            bool: False if the timeout elapsed before the calculations
            concluded, else True.
        """
        return self.up_to_date.wait(timeout)

    def get_at_element(self, index):
        """Return the AT element coresponding to the given index.

        Args:
            index (int): The index of the AT element to return.

        Returns:
            at.elements.Element: The element specified by the given index.
        """
        return self._at_lattice[index - 1]

    def get_at_lattice(self):
        """Return a copy of the AT lattice object.

        Returns:
            at.lattice_object.Lattice: A copy of the AT lattice object.
        """
        return self._at_lattice.copy()

    def get_chrom(self, cell):
        """Return the specified cell of the chromaticity for the AT lattice.

        Args:
            cell (int): The desired cell of chromaticity.

        Returns:
            float: The x or y chromaticity for the AT lattice.
        """
        return self._lindata[2][cell]

    def get_emit(self, cell):
        """Return the specified cell of the emittance for the AT lattice.

        .. Note:: The emittance of the first element is returned as it is
           constant throughout the AT lattice, and so which element's emittance
           is returned is arbitrary.

        Args:
            cell (int): The desired cell of emittance.

        Returns:
            float: The x or y emittance for the AT lattice.
        """
        return self._emittance[2]['emitXY'][:, cell][0]

    def get_orbit(self, cell):
        """Return the specified cell of the closed orbit for the AT lattice.

        Args:
            cell (int): The desired cell of closed orbit.

        Returns:
            numpy.array: The x, x phase, y or y phase for the AT lattice as an
            array of floats the length of the AT lattice.
        """
        return self._lindata[3]['closed_orbit'][:, cell]

    def get_tune(self, cell):
        """Return the specified cell of the tune for the AT lattice.

        .. Note:: A special consideration is made so only the fractional digits
           of the tune are returned.

        Args:
            cell (int): The desired cell of tune.

        Returns:
            float: The x or y tune for the AT lattice.
        """
        return (self._lindata[1][cell] % 1)

    def get_disp(self):
        """Return the dispersion at every element in the AT lattice.

        Returns:
            numpy.array: The dispersion vector for each element.
        """
        return self._lindata[3]['dispersion']

    def get_s(self):
        """Return the s position of every element in the AT lattice

        Returns:
            list: The s position of each element.
        """
        return list(self._lindata[3]['s_pos'])

    def get_energy(self):
        """Return the energy of the AT lattice. Taken from the AT attribute.

        Returns:
            float: The energy of the AT lattice.
        """
        return self._at_lattice.energy

    def get_alpha(self):
        """Return the alpha vector at every element in the AT lattice.

        Returns:
            numpy.array: The alpha vector for each element.
        """
        return self._lindata[3]['alpha']

    def get_beta(self):
        """Return the beta vector at every element in the AT lattice.

        Returns:
            numpy.array: The beta vector for each element.
        """
        return self._lindata[3]['beta']

    def get_m44(self):
        """Return the 4x4 transfer matrix for every element in the AT lattice.

        Returns:
            numpy.array: The 4x4 transfer matrix for each element.
        """
        return self._lindata[3]['m44']

    def get_mu(self):
        """Return mu at every element in the AT lattice.

        Returns:
            numpy.array: The mu array for each element.
        """
        return self._lindata[3]['mu']
