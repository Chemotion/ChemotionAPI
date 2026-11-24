import logging

from chemotion_api.labImotion.items.options import FieldUnit, get_unit
from chemotion_api.labImotion.structure import StructureRegistry

logger = logging.getLogger(__name__)

#: Values already reported as unrecognised, so a klass with many such fields warns once each
#: rather than once per field.
_reported_unknown_units: set[str] = set()


def _report_unknown_unit(message: str) -> None:
    """Warn once per distinct message that a server payload used something we do not model.

    This client mirrors LabIMotion's unit table, field types and select-option sets by hand, so it
    trails the server and the klasses older generic-ui versions left behind. The value is always
    kept as-is: degrading beats making the element unreadable.
    """
    if message not in _reported_unknown_units:
        _reported_unknown_units.add(message)
        logger.warning("%s — value kept as-is; this client's copy trails the server.", message)


#: The option set the designer offers as "System user list": the select lists the ELN's users and its
#: value is a user id (chem-generic-ui ``f4``).
SYSTEM_USER_LIST = '-su03-'


class Select:
    """A select field, pointing at one of its klass's ``select_options`` sets by key, or at
    :data:`SYSTEM_USER_LIST`.

    As with units, assignment from user code is validated strictly, but parsing a server payload
    is lenient: klasses authored by older generic-ui versions routinely reference an option set
    that is no longer present in the klass (sometimes with ``select_options`` empty altogether),
    and refusing those makes the whole klass — and every element using it — unreadable.
    """

    def __init__(self, sr: StructureRegistry, json_data):
        self._option_layers = None
        if not hasattr(self, '_sr'):
            self._sr = sr
        self._set_option_layers(json_data.get("option_layers"), strict=False)

    @property
    def option_layers(self) -> str:
        """The key of the option set in the template's ``select_options``, ``'-su03-'`` for the ELN's
        users, or ``''`` if the template has no option set yet. A new field gets the first option set.

        :raises ValueError: when set to a key the template does not have (add it with
            :meth:`~chemotion_api.labImotion.items.genericproperties.GenericProperties.add_select_option`)
        """
        return self._option_layers

    @option_layers.setter
    def option_layers(self, value: str | None):
        self._set_option_layers(value, strict=True)

    def _set_option_layers(self, value: str | None, strict: bool):
        options = self._sr.get_select_options_list()
        if value is None:
            # Without any option list the field stays unlinked until option_layers is set
            value = options[0] if options else ''
        if not isinstance(value, str):
            raise TypeError(f"option_layers {type(value)} not supported")
        if value not in ('', SYSTEM_USER_LIST) and value not in options:
            if strict:
                raise ValueError(f"option_layers '{value}' not in {options}. Add it with "
                                 f"properties.add_select_option(key, values)")
            # Deliberately silent: BaseField._parse_json re-assigns through the strict setter and
            # reports there, so warning here too would double every message.
        self._option_layers = value

class SystemDefined:
    """A numeric field carrying a unit type (``option_layers``) and a chosen unit (``value_system``).

    Assignment from user code is validated strictly, so a typo'd unit is caught at the call site.
    Parsing a server payload is deliberately *lenient*: LabIMotion adds units in point releases and
    the table in :mod:`chemotion_api.labImotion.items.options` is a hand-maintained mirror of the
    gem's ``units.rb``, so a klass using a unit this client has not learned yet must degrade to a
    warning rather than make the whole element unreadable.
    """

    def __init__(self, json_data: dict):
        self._value_system = None
        self._option_layers = None
        self._set_option_layers(json_data.get("option_layers", FieldUnit.ACCELERATION), strict=False)
        value_system = json_data.get("value_system")
        if value_system is None:
            available = get_unit(self.option_layers)
            value_system = available[0] if available else None
        if value_system is not None:
            self._set_value_system(value_system, strict=False)

    @property
    def value_system(self) -> str:
        """The default unit, a unit key of :attr:`option_layers` (see
        :data:`chemotion_api.labImotion.items.options.UNITS`). A bare number written to an element gets this
        unit.

        :raises ValueError: when set to a unit that is not one of the unit type
        """
        if self._value_system is None:
            available_units = get_unit(self.option_layers)
            self._value_system = available_units[0] if available_units else None
        return self._value_system

    @value_system.setter
    def value_system(self, value: str):
        self._set_value_system(value, strict=True)

    def _set_value_system(self, value: str, strict: bool):
        available_units = get_unit(self.option_layers)
        if not isinstance(value, str):
            raise TypeError(f"value_system {type(value)} not supported")
        if value not in available_units:
            if strict:
                raise ValueError(f"value_system {value} must be in {available_units}")
            _report_unknown_unit(
                f"unit {value!r} is not a known unit of {self.option_layers!r}"
            )
        self._value_system = value

    @property
    def option_layers(self) -> FieldUnit | str:
        """The unit type (:class:`~chemotion_api.labImotion.items.options.FieldUnit`, or its string).
        A new field gets ``FieldUnit.ACCELERATION``. Setting it resets :attr:`value_system` to the first unit
        of the type if the current one does not belong to it.

        :raises ValueError: for an unknown unit type
        """
        if self._option_layers is None:
            return FieldUnit.ACCELERATION
        return self._option_layers

    @option_layers.setter
    def option_layers(self, value: FieldUnit | str):
        self._set_option_layers(value, strict=True)

    def _set_option_layers(self, value: FieldUnit | str, strict: bool):
        if isinstance(value, str):
            try:
                value = FieldUnit(value)
            except ValueError:
                if strict:
                    raise
                _report_unknown_unit(f"unit type {value!r} is not known to this client")
        if not isinstance(value, FieldUnit | str):
            raise TypeError(f"option_layers {type(value)} not supported")
        self._option_layers = value
        available_units = get_unit(self._option_layers)
        if available_units and self._value_system not in available_units:
            self._value_system = available_units[0]


class Numeric:
    """Rounding and range of a number field or column (``numeric = {decimals, min, max}``), as the
    designer's "Max Decimal Places / Min Value / Max Value" set them. ``min``/``max`` are numbers or ``''``
    for no limit."""

    def __init__(self, json_data: dict):
        self._numeric = json_data.get('numeric')

    @property
    def numeric(self) -> dict | None:
        """``{'decimals': int >= 0, 'min': number or '', 'max': number or ''}``, or None. Values written
        to a ``number`` field or column of an element are checked against it (a number field without
        ``numeric`` takes integers only; ``integer`` fields ignore it). Other keys of the dict are kept."""
        return self._numeric

    @numeric.setter
    def numeric(self, value: dict | None):
        if value is not None:
            if not isinstance(value, dict):
                raise TypeError(f"numeric {type(value)} not supported")
            value = self._check_numeric(value.get('decimals', 0), value.get('min', ''), value.get('max', '')) \
                | {k: v for k, v in value.items() if k not in ('decimals', 'min', 'max')}
        self._numeric = value

    def set_numeric(self, decimals: int | None = None, min: float | str | None = None,
                    max: float | str | None = None) -> dict:
        """
        Sets the rounding and the range of the number. Arguments left out keep their value.

        :param decimals: the number of decimal places (>= 0)
        :param min: the lowest allowed value, or '' for none
        :param max: the highest allowed value, or '' for none
        :return: the new ``numeric`` setting

        :raises ValueError: if ``decimals`` is negative or ``min`` > ``max``
        """
        current = self._numeric or {'decimals': 0, 'min': '', 'max': ''}
        self.numeric = current | {k: v for k, v in (('decimals', decimals), ('min', min), ('max', max))
                                  if v is not None}
        return self._numeric

    @staticmethod
    def _check_numeric(decimals, minimum, maximum) -> dict:
        if isinstance(decimals, bool) or not isinstance(decimals, int) or decimals < 0:
            raise ValueError(f"decimals must be an integer >= 0, not {decimals!r}")
        for name, limit in (('min', minimum), ('max', maximum)):
            if limit != '' and (isinstance(limit, bool) or not isinstance(limit, int | float)):
                raise ValueError(f"{name} must be a number or '', not {limit!r}")
        if minimum != '' and maximum != '' and minimum > maximum:
            raise ValueError(f"min {minimum} is greater than max {maximum}")
        return {'decimals': decimals, 'min': minimum, 'max': maximum}
