"""Module containing all three of the AT simulator data sources."""
import at
import numpy
import pytac
from warnings import warn
from functools import partial
from threading import Thread, Event
from pytac.data_source import DataSource
from pytac.exceptions import FieldException, HandleException


class ATElementDataSource(DataSource):
    """A simulator data source to enable AT elements to be addressed using the
    standard Pytac syntax.

    **Attributes**

    Attributes:
        units (str): pytac.ENG or pytac.PHYS, pytac.PHYS by default.

    .. Private Attributes:
           _element (at.elements.Element): A pointer to the AT element
                                            equivalent of the Pytac element,
                                            which this data source instance
                                            is attached to.
           _ad (ATAcceleratorData): A pointer to the centralised accelerator
                                     data object.

           _fields (list): A list of all the fields that are present on this
                            element. N.B. not all possible fields i.e. _fields
                            != _field_funcs.keys()
           _field_funcs (dict): A dictionary which maps element fields to the
                                 correct data handling function. Some of these
                                 functions, via partial(), are passed a cell
                                 argument so only relevant data is returned.

    **Methods:**
    """
    def __init__(self, at_element, accelerator_data, fields=[]):
        self.units = pytac.PHYS
        self._element = at_element
        self._ad = accelerator_data
        self._fields = fields
        self._field_funcs = {'x_kick': partial(self._KickAngle, 0),
                             'y_kick': partial(self._KickAngle, 1),
                             'a1': partial(self._PolynomA, 1),
                             'b0': partial(self._PolynomB, 0),
                             'b1': partial(self._PolynomB, 1),
                             'b2': partial(self._PolynomB, 2),
                             'x': partial(self._Orbit, 0),
                             'y': partial(self._Orbit, 2),
                             'f': self._Frequency}

    def get_fields(self):
        """Get all the fields that are defined for the data source on this
        element.

        Returns:
            list: A list of all the fields that are present on this element.
        """
        return self._fields

    def get_value(self, field, handle=None):
        """Get the value for a field.

        N.B. The 'value' argument passed to the data handling functions is used
        as a get/set flag. In this case it is passed as 'None' to signify that
        data is to be returned not set.

        Args:
            field (str): The requested field.
            handle (any): Handle is not needed and is only here to conform with
                           the structure of the DataSource base class.

        Returns:
            float: The value of specified field on this data source.

        Raises:
            FieldException: if the specied field does not exist.
        """
        if field in self._fields:
            return self._field_funcs[field](value=None)
        else:
            raise FieldException("No field {0} on AT element {1}."
                                 .format(field, self._element))

    def set_value(self, field, set_value):
        """Set the value for a field.

        N.B. The 'value' argument passed to the data handling functions is used
        as a get/set flag. In this case the value to be set is passed this
        signifies that the given data should be set.

        Args:
            field (str): The requested field.
            set_value (float): The value to be set.

        Raises:
            FieldException: if the specied field does not exist.
        """
        if field in self._fields:
            self._field_funcs[field](value=set_value)
        else:
            raise FieldException("No field {0} on AT element {1}."
                                 .format(field, self._element))

    def _KickAngle(self, cell, value):
        """A data handling function used to get or set a specific cell of the
        KickAngle attribute of the AT element. Whenever a change is made the
        new changes threadding flag is set on the central accelerator data
        object, so as to trigger a recalculation of the physics data ensuring
        it is up to date.

        If the Corrector is attached to a Sextupole then the KickAngle needs to
        be assigned/returned to/from cell 0 of the applicable Polynom attribute
        and so a conversion must take place. For independant Correctors the
        KickAngle can be assigned/returned directly to/from the element's
        KickAngle attribute without any conversion.

        Args:
            cell (int): Which cell of KickAngle to get/set.
            value (float): The angle to be set, if it is not None.

        Returns:
            float: The kick angle of the specified cell.
        """
        if isinstance(self._element, at.elements.Sextupole):
            if value is None:
                if cell is 0:
                    return (- self._element.PolynomB[0] * self._element.Length)
                elif cell is 1:
                    return (self._element.PolynomA[0] * self._element.Length)
            else:
                if cell is 0:
                    self._element.PolynomB[0] = (- value / self._element.Length)
                elif cell is 1:
                    self._element.PolynomA[0] = (value / self._element.Length)
                self._ad.new_changes.set()
        else:
            if value is None:
                return self._element.KickAngle[cell]
            else:
                self._element.KickAngle[cell] = value
                self._ad.new_changes.set()

    def _PolynomA(self, cell, value):
        """A data handling function used to get or set a specific cell of the
        PolynomA attribute of the AT element. Whenever a change is made the new
        changes threadding flag is set on the central accelerator data object,
        so as to trigger a recalculation of the physics data ensuring it is up
        to date.

        Args:
            cell (int): Which cell of PolynomA to get/set.
            value (float): The value to be set, if it is not None.

        Returns:
            float: The value of the specified cell of PolynomA.
        """
        if value is None:
            return self._element.PolynomA[cell]
        else:
            self._element.PolynomA[cell] = value
            self._ad.new_changes.set()

    def _PolynomB(self, cell, value):
        """A data handling function used to get or set a specific cell of the
        PolynomB attribute of the AT element. Whenever a change is made the new
        changes threadding flag is set on the central accelerator data object,
        so as to trigger a recalculation of the physics data ensuring it is up
        to date.

        N.B. In the case of Quadrupoles K must also be set to the same value.

        Args:
            cell (int): Which cell of PolynomB to get/set.
            value (float): The value to be set, if it is not None.

        Returns:
            float: The value of the specified cell of PolynomB.
        """
        if value is None:
            return self._element.PolynomB[cell]
        else:
            if isinstance(self._element, at.elements.Quadrupole):
                self._element.K = value
            self._element.PolynomB[cell] = value
            self._ad.new_changes.set()

    def _Orbit(self, cell, value):
        """A data handling function used to get or set a specific cell of the
        orbit data for the AT element. This is the only function on this data
        source to get data from the central accelerator data object, as orbit
        is calculated over the whole lattice.

        Args:
            cell (int): Which cell of closed_orbit to get/set.
            value (float): You cannot set to BPMs of if it is not None an error
                            is raised.

        Returns:
            float: The value of the specified cell of closed_orbit.

        Raises:
            HandleException: if a set operation is attempted (value != None).
        """
        index = self._element.Index-1
        if value is None:
            return float(self._ad.get_orbit(cell)[index])
        else:
            field = 'x' if cell is 0 else 'y'
            raise HandleException("Field {0} cannot be set on element data "
                                  "source {1}.".format(field, self))

    def _Frequency(self, value):
        """A data handling function used to get or set the Frequency attribute
        of the AT element. Whenever a change is made the new changes threadding
        flag is set on the central accelerator data object, so as to trigger a
        recalculation of the physics data ensuring it is up to date.

        Args:
            value (float): The value to be set, if it is not None.

        Returns:
            float: The value of the element's Frequency attribute.
        """
        if value is None:
            return self._element.Frequency
        else:
            self._element.Frequency = value
            self._ad.new_changes.set()


class ATLatticeDataSource(DataSource):
    """A simulator data source to allow the physics data of the AT lattice to
    be be addressed using the standard Pytac syntax.

    **Attributes**

    Attributes:
        units (str): pytac.ENG or pytac.PHYS, pytac.PHYS by default.

    .. Private Attributes:
           _ad (ATAcceleratorData): A pointer to the centralised accelerator
                                     data object.
           _field_funcs (dict): A dictionary which maps lattice fields to the
                                 correct data function on the centralised
                                 accelerator data object. Some of these
                                 functions, via partial(), are passed a cell
                                 argument so only relevant data is returned.

    **Methods:**
    """
    def __init__(self, accelerator_data):
        self.units = pytac.PHYS
        self._ad = accelerator_data
        self._field_funcs = {'chromaticity_x': partial(self._ad.get_chrom, 0),
                             'chromaticity_y': partial(self._ad.get_chrom, 1),
                             'emittance_x': partial(self._ad.get_emit, 0),
                             'emittance_y': partial(self._ad.get_emit, 1),
                             'phase_x': partial(self._ad.get_orbit, 1),
                             'phase_y': partial(self._ad.get_orbit, 3),
                             'tune_x': partial(self._ad.get_tune, 0),
                             'tune_y': partial(self._ad.get_tune, 1),
                             'x': partial(self._ad.get_orbit, 0),
                             'y': partial(self._ad.get_orbit, 2),
                             'dispersion': self._ad.get_disp,
                             'energy': self._ad.get_energy,
                             's_position': self._ad.get_s,
                             'alpha': self._ad.get_alpha,
                             'beta': self._ad.get_beta,
                             'm44': self._ad.get_m44,
                             'mu': self._ad.get_mu}

    def get_fields(self):
        """Get all the fields that are defined for this data source on the
        lattice.

        Returns:
            list: A list of all the fields that are present on this element.
        """
        return self._field_funcs.keys()

    def get_value(self, field, handle=None):
        """Get the value for a field on the lattice.

        Args:
            field (str): The requested field.
            handle (any): Handle is not needed and is only here to conform with
                           the structure of the DataSource base class.

        Returns:
            float: The value of specified field on this data source.

        Raises:
            FieldException: if the specied field does not exist.
        """
        if field in self._field_funcs.keys():
            return self._field_funcs[field]()
        else:
            raise FieldException("Lattice data source {0} does not have field "
                                 "{1}".format(self, field))

    def set_value(self, field, value):
        """Set the value for a field.

        N.B. Currently a HandleException is always raised.

        Args:
            field (str): The requested field.
            value (float): The value to be set.

        Raises:
            HandleException: as setting values to lattice fields is not
                              currently supported.
        """
        raise HandleException("Field {0} cannot be set on lattice data source "
                              "{0}.".format(field, self))


class ATAcceleratorData(object):
    """A centralised class which holds the data for the simulator, and provides
    the lattice's physics data to simulator data sources. This class ensures
    that this data is up to date through the use of threading, a thread
    constantly runs in the background and recalculates the physics data every
    time a change is made via the use of flags (threading events).

    **Attributes**

    Attributes:
        new_changes (threading.Event): A flag to indicate that changes to the
                                        AT ring have been made.

    .. Private Attributes:
           _lattice (at.lattice_object.Lattice): The centralised instance of
                                                  the AT ring which the physics
                                                  data is calculated.
           _rp (numpy.array): A boolean array to be used as refpoints for the
                               physics calculations.
           _paused (threading.Event): A flag used to temporarily pause the
                                       physics calculations.
           _emittance (tuple): Emittance, the output of the AT physics function
                                ohmi_envelope, see at.lattice.radiation.
           _lindata (tuple): Linear optics data, the output of the AT physics
                              function linopt, see at.lattice.linear.

    **Methods:**
    """
    def __init__(self, ring):
        """If an error or execption is raised in the running thread then it
        does not continue running so subsequent calculations are not performed.
        Converting errors to warnings fixes this.

        The phys data must be initially calculated here so that it can't be
        accidentally referenced before the attributes _emittance and _lindata
        can be referenced, this causes errors as they wouldn't exist yet.
        """
        self._lattice = at.Lattice(ring, keep_all=True)
        self._rp = numpy.array(range(len(ring) + 1))
        self._lattice.radiation_on()
        self._emittance = self._lattice.ohmi_envelope(self._rp)
        self._lattice.radiation_off()
        self._lindata = self._lattice.linopt(0, self._rp, True, coupled=False)
        self.new_changes = Event()
        self._paused = Event()
        self._running = Event()
        self._calculation_thread = Thread(target=self.recalculate_phys_data)

    def start_thread(self):
        if self._running.is_set() is False:
            self._calculation_thread.setDaemon(True)
            self._running.set()
            self._calculation_thread.start()
        else:
            raise RuntimeError("Cannot start thread as it is already running.")

    def recalculate_phys_data(self):
        """Target function for the background thread. Recalculates the physics
        data dependant on the status of the _paused and new_changes flags. The
        thread is constantly running but the calculations only take place if
        the changes flag is True and the paused flag is False.
        """
        while self._running.is_set() is True:
            if (self.new_changes.is_set() is True) and (self._paused.is_set()
                                                        is False):
                try:
                    self._lattice.radiation_on()
                    self._emittance = self._lattice.ohmi_envelope(self._rp)
                    self._lattice.radiation_off()
                    self._lindata = self._lattice.linopt(0, self._rp, True,
                                                         coupled=False)
                except Exception as e:
                    warn(at.AtWarning(e))
                self.new_changes.clear()

    def stop_thread(self):
        self._running.clear()
        self._calculation_thread.join()

    def toggle_calculations(self):
        """Pause or unpause the pysics calculations by setting or clearing the
        _paused flag.
        """
        if self._paused.is_set() is False:
            self._paused.set()
        else:
            self._paused.clear()

    def get_element(self, index):
        """Return the AT element coresponding to the given index.

        Args:
            index (int): The index of the AT element to return.

        Returns:
            at.elements.Element: The element specified by the given index.
        """
        return self._lattice[index-1]

    def get_ring(self):
        """Return the AT ring.

        Returns:
            list: A copy of the AT ring.
        """
        return self._lattice._lattice

    def get_lattice_object(self):
        """Return a copy of the AT lattice object.

        Returns:
            at.lattice_object.Lattice: A copy of the AT lattice object.
        """
        return self._lattice.copy()

    def get_chrom(self, cell):
        """Return the specified cell of the chromaticity for the lattice.

        Returns:
            float: The x or y chromaticity for the lattice.
        """
        return self._lindata[2][cell]

    def get_emit(self, cell):
        """Return the specified cell of the emittance for the lattice.

        N.B. The emittance of the last element is returned as it should be
        constant throughout the lattice and so cell is returned is arbitrary.

        Returns:
            float: The x or y emittance for the lattice.
        """
        return self._emittance[2]['emitXY'][:, cell][0]

    def get_orbit(self, cell):
        """Return the specified cell of the closed orbit for the lattice.

        Returns:
            numpy.array: The x, x phase, y or y phase for the lattice as an
                          array of floats the length of the lattice.
        """
        return self._lindata[3]['closed_orbit'][:, cell]

    def get_tune(self, cell):
        """Return the specified cell of the tune for the lattice.

        Returns:
            float: The x or y tune for the lattice.
        """
        return (self._lindata[1][cell] % 1)

    def get_disp(self):
        """Return the dispersion at every element in the lattice.

        Returns:
            numpy.array: The dispersion vector for each element.
        """
        return self._lindata[3]['dispersion']

    def get_s(self):
        """Return the s position of every element in the lattice

        Returns:
            list: The s position of each element.
        """
        return list(self._lindata[3]['s_pos'])

    def get_energy(self):
        """Return the energy of the lattice. Taken from the AT attribute.

        Returns:
            float: The energy of the lattice.
        """
        return self._lattice.energy

    def get_alpha(self):
        """Return the alpha vector at every element in the lattice.

        Returns:
            numpy.array: The alpha vector for each element.
        """
        return self._lindata[3]['alpha']

    def get_beta(self):
        """Return the beta vector at every element in the lattice.

        Returns:
            numpy.array: The beta vector for each element.
        """
        return self._lindata[3]['beta']

    def get_m44(self):
        """Return the 4x4 transfer matrix at every element in the lattice.

        Returns:
            numpy.array: The 4x4 transfer matrix for each element.
        """
        return self._lindata[3]['m44']

    def get_mu(self):
        """Return mu at every element in the lattice.

        Returns:
            numpy.array: The mu array for each element.
        """
        return self._lindata[3]['mu']
