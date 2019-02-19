"""Module containing the pytac data sources for the AT simulator."""
from functools import partial

import at
import pytac
from pytac.exceptions import FieldException, HandleException


class ATElementDataSource(pytac.data_source.DataSource):
    """A simulator data source to enable AT elements to be addressed using the
    standard Pytac syntax.

    **Attributes**

    Attributes:
        units (str): pytac.ENG or pytac.PHYS, pytac.PHYS by default.

    .. Private Attributes:
           _at_element (at.elements.Element): A pointer to the AT element
                                               equivalent of the Pytac element,
                                               which this data source instance
                                               is attached to.
           _atsim (ATSimulator): A pointer to the centralised instance of an
                                  ATSimulator object.
           _fields (list): A list of all the fields that are present on this
                            element. N.B. not all possible fields i.e. _fields
                            != _field_funcs.keys()
           _field_funcs (dict): A dictionary which maps element fields to the
                                 correct data handling function. Some of these
                                 functions, via partial(), are passed a cell
                                 argument so only relevant data is returned.
    """
    def __init__(self, at_element, atsim, fields=[]):
        """
        .. Note:: This data source, currently, cannot understand the simulated
           equivelent of shared devices on the live machine, or multiple
           devices that address the same field/attribute for that matter.

        Args:
            at_element (at.elements.Element): The AT element corresponding to
                                               the Pytac element which this
                                               data source is attached to.
            atsim (ATSimulator): An instance of an ATSimulator object.
            fields (list, optional): The fields found on this element.

        **Methods:**
        """
        self.units = pytac.PHYS
        self._at_element = at_element
        self._atsim = atsim
        self._fields = fields
        self._field_funcs = {'x_kick': partial(self._KickAngle, 0),
                             'y_kick': partial(self._KickAngle, 1),
                             'a1': partial(self._PolynomA, 1),
                             'b1': partial(self._PolynomB, 1),
                             'b2': partial(self._PolynomB, 2),
                             'x': partial(self._Orbit, 0),
                             'y': partial(self._Orbit, 2),
                             'b0': self._BendingAngle,
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

        .. Note:: The 'value' argument passed to the data handling functions is
           used as a get/set flag. In this case, it is passed as 'None' to
           signify that data is to be returned not set.

        Args:
            field (str): The requested field.
            handle (str, optional): Handle is not needed and is only here to
                                     conform with the structure of the
                                     DataSource base class.

        Returns:
            float: The value of the specified field on this data source.

        Raises:
            FieldException: if the specified field does not exist.
        """
        if field in self._fields:
            return self._field_funcs[field](value=None)
        else:
            raise FieldException("No field {0} on AT element {1}."
                                 .format(field, self._at_element))

    def set_value(self, field, set_value):
        """Set the value for a field.

        .. Note:: The 'value' argument passed to the data handling functions is
           used as a get/set flag. In this case, the value to be set is passed
           this signifies that the given data should be set.

        Args:
            field (str): The requested field.
            set_value (float): The value to be set.

        Raises:
            FieldException: if the specified field does not exist.
        """
        if field in self._fields:
            self._field_funcs[field](value=set_value)
        else:
            raise FieldException("No field {0} on AT element {1}."
                                 .format(field, self._at_element))

    def _KickAngle(self, cell, value):
        """A data handling function used to get or set a specific cell of the
        KickAngle attribute of the AT element. Whenever a change is made the
        'up_to_date' threading event is cleared on the central ATSimulator
        object, so as to trigger a recalculation of the physics data ensuring
        it is up to date.

        .. Note:: If the Corrector is attached to a Sextupole then KickAngle
           needs to be assigned/returned to/from cell 0 of the applicable
           Polynom(A/B) attribute and so a conversion must take place. For
           independent Correctors KickAngle can be assigned/returned directly
           to/from the element's KickAngle attribute without any conversion.
           This is because independent Correctors have a KickAngle attribute in
           AT, but those attached to Sextupoles do not.

        Args:
            cell (int): Which cell of KickAngle to get/set.
            value (float): The angle to be set, if it is not None.

        Returns:
            float: The kick angle of the specified cell.
        """
        if isinstance(self._at_element, at.elements.Sextupole):
            length = self._at_element.Length
            if value is None:
                if cell is 0:
                    return -(self._at_element.PolynomB[0] * length)
                elif cell is 1:
                    return (self._at_element.PolynomA[0] * length)
            else:
                if cell is 0:
                    self._at_element.PolynomB[0] = -(value / length)
                elif cell is 1:
                    self._at_element.PolynomA[0] = (value / length)
                self._atsim.up_to_date.clear()
        else:
            if value is None:
                return self._at_element.KickAngle[cell]
            else:
                self._at_element.KickAngle[cell] = value
                self._atsim.up_to_date.clear()

    def _PolynomA(self, cell, value):
        """A data handling function used to get or set a specific cell of the
        PolynomA attribute of the AT element. Whenever a change is made the
        'up_to_date' threading event is cleared on the central ATSimulator
        object, so as to trigger a recalculation of the physics data ensuring
        it is up to date.

        Args:
            cell (int): Which cell of PolynomA to get/set.
            value (float): The value to be set, if it is not None.

        Returns:
            float: The value of the specified cell of PolynomA.
        """
        if value is None:
            return self._at_element.PolynomA[cell]
        else:
            self._at_element.PolynomA[cell] = value
            self._atsim.up_to_date.clear()

    def _PolynomB(self, cell, value):
        """A data handling function used to get or set a specific cell of the
        PolynomB attribute of the AT element. Whenever a change is made the
        'up_to_date' threading event is cleared on the central ATSimulator
        object, so as to trigger a recalculation of the physics data ensuring
        it is up to date.

        Args:
            cell (int): Which cell of PolynomB to get/set.
            value (float): The value to be set, if it is not None.

        Returns:
            float: The value of the specified cell of PolynomB.
        """
        if value is None:
            return self._at_element.PolynomB[cell]
        else:
            self._at_element.PolynomB[cell] = value
            self._atsim.up_to_date.clear()

    def _Orbit(self, cell, value):
        """A data handling function used to get or set a specific cell of the
        orbit data for the AT element. This is the only function on this data
        source to get data from the central ATSimulator object, it must do this
        because the orbit is calculated over the whole lattice.

        Args:
            cell (int): Which cell of closed_orbit to get/set.
            value (float): You cannot set to BPMs of if it is not None an error
                            is raised.

        Returns:
            float: The value of the specified cell of closed_orbit.

        Raises:
            HandleException: if a set operation is attempted (value != None).
        """
        index = self._at_element.Index - 1
        if value is None:
            return float(self._atsim.get_orbit(cell)[index])
        else:
            field = 'x' if cell is 0 else 'y'
            raise HandleException("Field {0} cannot be set on element data "
                                  "source {1}.".format(field, self))

    def _BendingAngle(self, value):
        """A data handling function used to get or set the BendingAngle
        attribute of the AT element. Whenever a change is made the 'up_to_date'
        threading event is cleared on the central ATSimulator object, so as to
        trigger a recalculation of the physics data ensuring it is up to date.

        Args:
            value (float): The value to be set, if it is not None.

        Returns:
            float: The value of the element's BendingAngle attribute.
        """
        if value is None:
            return self._at_element.BendingAngle
        else:
            self._at_element.BendingAngle = value
            self._atsim.up_to_date.clear()

    def _Frequency(self, value):
        """A data handling function used to get or set the Frequency attribute
        of the AT element. Whenever a change is made the 'up_to_date'
        threading event is cleared on the central ATSimulator object, so as to
        trigger a recalculation of the physics data ensuring it is up to date.

        Args:
            value (float): The value to be set, if it is not None.

        Returns:
            float: The value of the element's Frequency attribute.
        """
        if value is None:
            return self._at_element.Frequency
        else:
            self._at_element.Frequency = value
            self._atsim.up_to_date.clear()


class ATLatticeDataSource(pytac.data_source.DataSource):
    """A simulator data source to allow the physics data of the AT lattice to
    be addressed using the standard Pytac syntax.

    **Attributes**

    Attributes:
        units (str): pytac.ENG or pytac.PHYS, pytac.PHYS by default.

    .. Private Attributes:
           _atsim (ATSimulator): A pointer to the centralised instance of an
                                  ATSimulator object.
           _field_funcs (dict): A dictionary which maps pytac lattice fields to
                                 the correct data function on the centralised
                                 ATSimulator object. Some of these functions,
                                 via partial(), are passed a cell argument so
                                 only relevant data is returned.
    """
    def __init__(self, atsim):
        """
        .. Note:: Though not currently supported, there are plans to add
           get_element_values and set_element_values methods to this data
           source in future.

        Args:
            atsim (ATSimulator): An instance of an ATSimulator object.

        **Methods:**
        """
        self.units = pytac.PHYS
        self._atsim = atsim
        self._field_funcs = {'chromaticity_x': partial(self._atsim.get_chrom, 0),
                             'chromaticity_y': partial(self._atsim.get_chrom, 1),
                             'emittance_x': partial(self._atsim.get_emit, 0),
                             'emittance_y': partial(self._atsim.get_emit, 1),
                             'phase_x': partial(self._atsim.get_orbit, 1),
                             'phase_y': partial(self._atsim.get_orbit, 3),
                             'tune_x': partial(self._atsim.get_tune, 0),
                             'tune_y': partial(self._atsim.get_tune, 1),
                             'x': partial(self._atsim.get_orbit, 0),
                             'y': partial(self._atsim.get_orbit, 2),
                             'dispersion': self._atsim.get_disp,
                             'energy': self._atsim.get_energy,
                             's_position': self._atsim.get_s,
                             'alpha': self._atsim.get_alpha,
                             'beta': self._atsim.get_beta,
                             'm44': self._atsim.get_m44,
                             'mu': self._atsim.get_mu}

    def get_fields(self):
        """Get all the fields that are defined for this data source on the
        pytac lattice.

        Returns:
            list: A list of all the fields that are present on this element.
        """
        return self._field_funcs.keys()

    def get_value(self, field, handle=None):
        """Get the value for a field on the pytac lattice.

        Args:
            field (str): The requested field.
            handle (str, optional): Handle is not needed and is only here to
                                     conform with the structure of the
                                     DataSource base class.

        Returns:
            float: The value of the specified field on this data source.

        Raises:
            FieldException: if the specified field does not exist.
        """
        if field in self._field_funcs.keys():
            return self._field_funcs[field]()
        else:
            raise FieldException("Lattice data source {0} does not have field "
                                 "{1}".format(self, field))

    def set_value(self, field, value):
        """Set the value for a field.

        .. Note:: Currently, a HandleException is always raised.

        Args:
            field (str): The requested field.
            value (float): The value to be set.

        Raises:
            HandleException: as setting values to pytac lattice fields is not
                              currently supported.
        """
        raise HandleException("Field {0} cannot be set on lattice data source "
                              "{0}.".format(field, self))
