"""Module containing the pytac data sources for the AT simulator."""

import logging
from functools import partial

import at
import pytac
from pytac.exceptions import ControlSystemException, FieldException, HandleException


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
           _index (int): The element's index in the ring, starting from 1.
           _atsim (ATSimulator): A pointer to the centralised instance of an
                                  ATSimulator object.
           _fields (list): A list of all the fields that are present on this
                            element. N.B. not all possible fields i.e. _fields
                            != _get_field_funcs.keys()
           _get_field_funcs (dict): A dictionary which maps element fields to
                                     the correct get function. Some of these
                                     functions, via partial(), are passed a
                                     cell argument so only relevant data is
                                     returned.
           _set_field_funcs (dict): A dictionary which maps element fields to
                                     the correct set function. Some of these
                                     functions, via partial(), are passed a
                                     cell argument so only relevant data is
                                     returned.
    """

    def __init__(self, at_element, index, atsim, fields=None):
        """
        .. Note:: This data source, currently, cannot understand the simulated
           equivalent of shared devices on the live machine, or multiple
           devices that address the same field/attribute for that matter.

        Args:
            at_element (at.elements.Element): The AT element corresponding to
                                               the Pytac element which this
                                               data source is attached to.
            index (int): The element's index in the ring, starting from 1.
            atsim (ATSimulator): An instance of an ATSimulator object.
            fields (list, typing.Optional): The fields found on this element.

        Raises:
            ValueError: if an unsupported field is passed, i.e. a field not in
                         _field_funcs.keys().

        **Methods:**
        """
        self.units = pytac.PHYS
        self._at_element = at_element
        self._index = index
        self._atsim = atsim
        self._get_field_funcs = {
            "x_kick": partial(self._get_KickAngle, 0),
            "y_kick": partial(self._get_KickAngle, 1),
            "x": partial(self._get_ClosedOrbit, "x"),
            "y": partial(self._get_ClosedOrbit, "y"),
            "a1": partial(self._get_PolynomA, 1),
            "b1": partial(self._get_PolynomB, 1),
            "b2": partial(self._get_PolynomB, 2),
            "b0": self._get_BendingAngle,
            "f": self._get_Frequency,
        }
        self._set_field_funcs = {
            "x_kick": partial(self._set_KickAngle, 0),
            "y_kick": partial(self._set_KickAngle, 1),
            "a1": partial(self._set_PolynomA, 1),
            "b1": partial(self._set_PolynomB, 1),
            "b2": partial(self._set_PolynomB, 2),
            "b0": self._set_BendingAngle,
            "f": self._set_Frequency,
        }
        fields = set() if fields is None else set(fields)
        # We assume that every set field has a corresponding get field.
        supported_fields = set(self._get_field_funcs.keys())
        if not all(f in supported_fields for f in fields):
            raise FieldException(f"Unsupported field(s) {fields - supported_fields}.")
        else:
            self._fields = list(fields)

    def get_fields(self):
        """Get all the fields that are defined for the data source on this
        element.

        Returns:
            list: A list of all the fields that are present on this element.
        """
        return self._fields

    def add_field(self, field):
        """Add a field to this data source. This is normally done
        automatically when adding a device, however since the simulated data
        sources do not use devices this method is needed.

        Args:
            field (str): The name of a supported field that is not already on
                          this data_source.

        Raises:
            pytac.FieldException: if the specified field is already present or if it
                             is not supported.
        """
        if field in self._fields:
            raise FieldException(
                f"Field {field} already present on element data source {self}."
            )
        elif field not in self._get_field_funcs.keys():
            raise FieldException(f"Unsupported field {field}.")
        else:
            self._fields.append(field)

    def get_value(self, field, handle=None, throw=True):
        """Get the value for a field.

        Args:
            field (str): The requested field.
            handle (str, typing.Optional): Handle is not needed and is only here to
                                     conform with the structure of the
                                     DataSource base class.
            throw (bool, typing.Optional): If the check for completion of outstanding
                                     calculations times out, then:
                                     if True, raise a ControlSystemException;
                                     if False, log a warning and return the
                                     potentially out of date data anyway.

        Returns:
            float: The value of the specified field on this data source.

        Raises:
            pytac.FieldException: if the specified field does not exist.
            pytac.ControlSystemException: if the calculation completion check fails,
                                     and throw is True.
        """
        # Wait for any outstanding calculations to conclude, to ensure they are
        # complete before a value is returned; if the wait times out then raise
        # an error message or log a warning according to the value of throw.
        if not self._atsim.wait_for_calculations():
            error_msg = "Check for completion of outstanding calculations timed out."
            if throw:
                raise ControlSystemException(error_msg)
            else:
                logging.warning("Potentially out of date data returned. " + error_msg)
        # Again we assume that every set field has a corresponding get field.
        if field in self._fields:
            return self._get_field_funcs[field]()
        else:
            raise FieldException(f"No field {field} on AT element {self._at_element}.")

    def set_value(self, field, value, throw=None):
        """Set the value for a field. The field and value go onto the queue of
        changes on the ATSimulator to be passed to make_change when the queue
        is emptied.

        Args:
            field (str): The requested field.
            value (float): The value to be set.
            throw (bool, typing.Optional): Throw is not needed and is only here to
                                     conform with the structure of the
                                     DataSource base class.

        Raises:
            pytac.HandleException: if the specified field cannot be set to.
            pytac.FieldException: if the specified field does not exist.
        """
        if field in self._fields:
            if field in self._set_field_funcs.keys():
                self._atsim.queue_set(self._make_change, field, value)
            else:
                raise HandleException(
                    f"Field {field} cannot be set on element data source {self}."
                )
        else:
            raise FieldException(f"No field {field} on AT element {self._at_element}.")

    def _make_change(self, field, value):
        """Calls the appropriate field setting function to actually modify the
        AT element, called in ATSimulator when the queue is being emptied.

        Args:
            field (str): The requested field.
            value (float): The value to be set.
        """
        self._set_field_funcs[field](value)

    def _get_KickAngle(self, cell):
        """A data handling function used to get the value of a specific cell
        of the KickAngle attribute of the AT element.

        .. Note:: If the Corrector is attached to a Sextupole then KickAngle
           needs to be returned from cell 0 of the applicable Polynom(A/B)
           attribute and so a conversion must take place. For independent
           Correctors KickAngle can be returned directly from the element's
           KickAngle attribute without any conversion. This is because
           independent Correctors have a KickAngle attribute in our AT lattice,
           but those attached to Sextupoles do not.

        Args:
            cell (int): Which cell of KickAngle to get.

        Returns:
            float: The kick angle of the specified cell.
        """
        if isinstance(self._at_element, at.elements.Sextupole):
            length = self._at_element.Length
            if cell == 0:
                return -(self._at_element.PolynomB[0] * length)
            elif cell == 1:
                return self._at_element.PolynomA[0] * length
        else:
            return self._at_element.KickAngle[cell]

    def _set_KickAngle(self, cell, value):
        """A data handling function used to set the value of a specific cell
        of the KickAngle attribute of the AT element.

        .. Note:: If the Corrector is attached to a Sextupole then KickAngle
           needs to be assigned to cell 0 of the applicable Polynom(A/B)
           attribute and so a conversion must take place. For independent
           Correctors KickAngle can be assigned directly to the element's
           KickAngle attribute without any conversion. This is because
           independent Correctors have a KickAngle attribute in our AT lattice,
           but those attached to Sextupoles do not.

        Args:
            cell (int): Which cell of KickAngle to set.
            value (float): The angle to be set.
        """
        if isinstance(self._at_element, at.elements.Sextupole):
            length = self._at_element.Length
            if cell == 0:
                self._at_element.PolynomB[0] = -(value / length)
            elif cell == 1:
                self._at_element.PolynomA[0] = value / length
        else:
            self._at_element.KickAngle[cell] = value

    def _get_PolynomA(self, cell):
        """A data handling function used to get the value of a specific cell
        of the PolynomA attribute of the AT element.

        Args:
            cell (int): Which cell of PolynomA to get.

        Returns:
            float: The value of the specified cell of PolynomA.
        """
        return self._at_element.PolynomA[cell]

    def _set_PolynomA(self, cell, value):
        """A data handling function used to set the value of a specific cell
        of the PolynomA attribute of the AT element.

        Args:
            cell (int): Which cell of PolynomA to set.
            value (float): The value to be set.
        """
        self._at_element.PolynomA[cell] = value

    def _get_PolynomB(self, cell):
        """A data handling function used to get the value of a specific cell
        of the PolynomB attribute of the AT element.

        Args:
            cell (int): Which cell of PolynomB to get.

        Returns:
            float: The value of the specified cell of PolynomB.
        """
        return self._at_element.PolynomB[cell]

    def _set_PolynomB(self, cell, value):
        """A data handling function used to set the value of a specific cell
        of the PolynomB attribute of the AT element.

        Args:
            cell (int): Which cell of PolynomB to set.
            value (float): The value to be set.
        """
        self._at_element.PolynomB[cell] = value

    def _get_ClosedOrbit(self, field):
        """A data handling function used to get the value of a specific cell
        of the orbit data for the AT element. This is the only function on
        this data source to get data from the central ATSimulator object, it
        must do this because in AT the closed orbit is calculated over the
        whole lattice.

        Args:
            field (str): Which cell of closed_orbit to get.

        Returns:
            float: The value of the specified cell of closed_orbit.
        """
        return float(self._atsim.get_orbit(field)[self._index - 1])

    def _get_BendingAngle(self):
        """A data handling function used to get the value of the BendingAngle
        attribute of the AT element.

        Returns:
            float: The value of the element's BendingAngle attribute.
        """
        return self._at_element.BendingAngle

    def _set_BendingAngle(self, value):
        """A data handling function used to set the value of the BendingAngle
        attribute of the AT element.

        Args:
            value (float): The value to be set.
        """
        self._at_element.BendingAngle = value

    def _get_Frequency(self):
        """A data handling function used to get the value of the Frequency
        attribute of the AT element.

        Returns:
            float: The value of the element's Frequency attribute.
        """
        return self._at_element.Frequency

    def _set_Frequency(self, value):
        """A data handling function used to set the value of the Frequency
        attribute of the AT element.

        Args:
            value (float): The value to be set.
        """
        self._at_element.Frequency = value


class ATLatticeDataSource(pytac.data_source.DataSource):
    """A simulator data source to allow the physics data of the AT lattice to
    be addressed using the standard Pytac syntax.

    **Attributes**

    Attributes:
        units (str): pytac.ENG or pytac.PHYS, pytac.PHYS by default.

    .. Private Attributes:
           _atsim (ATSimulator): A pointer to the centralised instance of an
                                  ATSimulator object.
           _field_funcs (dict): A dictionary which maps Pytac lattice fields to
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
        self._field_funcs = {
            "chromaticity_x": self._atsim.get_chromaticity,
            "chromaticity_y": self._atsim.get_chromaticity,
            "chromaticity": self._atsim.get_chromaticity,
            "eta_prime_x": self._atsim.get_dispersion,
            "eta_prime_y": self._atsim.get_dispersion,
            "dispersion": self._atsim.get_dispersion,
            "emittance_x": self._atsim.get_emittance,
            "emittance_y": self._atsim.get_emittance,
            "emittance": self._atsim.get_emittance,
            "closed_orbit": self._atsim.get_orbit,
            "eta_x": self._atsim.get_dispersion,
            "eta_y": self._atsim.get_dispersion,
            "energy": self._atsim.get_energy,
            "phase_x": self._atsim.get_orbit,
            "phase_y": self._atsim.get_orbit,
            "s_position": self._atsim.get_s,
            "tune_x": self._atsim.get_tune,
            "tune_y": self._atsim.get_tune,
            "alpha": self._atsim.get_alpha,
            "beta": self._atsim.get_beta,
            "tune": self._atsim.get_tune,
            "m66": self._atsim.get_m66,
            "x": self._atsim.get_orbit,
            "y": self._atsim.get_orbit,
            "mu": self._atsim.get_mu,
        }

    def get_fields(self):
        """Get all the fields that are defined for this data source on the
        Pytac lattice.

        Returns:
            list: A list of all the fields that are present on this element.
        """
        return list(self._field_funcs.keys())

    def get_value(self, field, handle=None, throw=True):
        """Get the value for a field on the Pytac lattice.

        Args:
            field (str): The requested field.
            handle (str, typing.Optional): Handle is not needed and is only here to
                                     conform with the structure of the
                                     DataSource base class.
            throw (bool, typing.Optional): If the check for completion of outstanding
                                     calculations times out, then:
                                     if True, raise a ControlSystemException;
                                     if False, log a warning and return the
                                     potentially out of date data anyway.

        Returns:
            float: The value of the specified field on this data source.

        Raises:
            pytac.FieldException: if the specified field does not exist.
            pytac.ControlSystemException: if the calculation completion check fails,
                                     and throw is True.
        """
        # Wait for any outstanding calculations to conclude, to ensure they are
        # complete before a value is returned; if the wait times out then raise
        # an error message or log a warning according to the value of throw.
        if not self._atsim.wait_for_calculations():
            error_msg = "Check for completion of outstanding calculations timed out."
            if throw:
                raise ControlSystemException(error_msg)
            else:
                logging.warning("Potentially out of date data returned. " + error_msg)
        if field in list(self._field_funcs.keys()):
            # The orbit x_phase and y_phase, and the eta prime_x and prime_y
            # fields are represented by 'px' or 'py' in the ATSimulator data
            # handling functions.
            if (field.startswith("phase")) or (field.find("prime") != -1):
                return self._field_funcs[field]("p" + field[-1])
            elif field.endswith("x"):
                return self._field_funcs[field]("x")
            elif field.endswith("y"):
                return self._field_funcs[field]("y")
            else:
                return self._field_funcs[field]()
        else:
            raise FieldException(
                f"Lattice data source {self} does not have field {field}"
            )

    def set_value(self, field, value, throw=None):
        """Set the value for a field.

        .. Note:: Currently, a HandleException is always raised.

        Args:
            field (str): The requested field.
            value (float): The value to be set.
            throw (bool, typing.Optional): Throw is not needed and is only here to
                                     conform with the structure of the
                                     DataSource base class.

        Raises:
            pytac.HandleException: as setting values to Pytac lattice fields is not
                              currently supported.
        """
        raise HandleException(
            f"Field {field} cannot be set on lattice data source {self}."
        )
