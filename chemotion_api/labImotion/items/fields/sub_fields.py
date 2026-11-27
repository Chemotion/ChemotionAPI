import uuid
import re
from enum import Enum

from chemotion_api.labImotion.items.fields.abstract_fields import SystemDefined, _report_unknown_unit as _report_unknown_value
from chemotion_api.labImotion.items.options import SubFieldType, FieldUnit, get_unit
from chemotion_api.labImotion.structure import StructureRegistry
from chemotion_api.labImotion.utils import ChemotionSerializable


#: A number as the designer's number input accepts it (HTML ``type="number"``): sign, decimals, exponent.
#: ASCII digits only: ``\d`` would also take digits such as '١٢' or '１２', which no number input sends.
NUMBER_PATTERN = re.compile(r'[+-]?([0-9]+\.?[0-9]*|\.[0-9]+)([eE][+-]?[0-9]+)?')


class SubBaseField(ChemotionSerializable):
    _default_required_fields = ["id", "field_type", "value"]
    required_fields = []
    mapping = {"field_type": "type"}
    default = ""
    field_type = None

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        self._sr = sr
        self._layer_key = layer_key
        self._id = json_data.get("id", uuid.uuid4().__str__())
        value = json_data.get("value", self.default)
        try:
            self.value = value
        except ValueError as e:
            # A loaded value the setter refuses (e.g. '1.2.3', which older clients accepted) is kept
            # verbatim, as BaseField._parse_json does: raising would make the whole field unreadable.
            self._value = value
            _report_unknown_value(f"{type(self).__name__}.value rejected the server's value {value!r} ({e})")

    def to_dict(self):
        json_dict = {}
        for key in self._default_required_fields + self.required_fields:
            val = getattr(self, key)
            if isinstance(val, Enum):
                val = val.value
            key = self.mapping.get(key, key)
            json_dict[key] = val
        return json_dict

    @property
    def value(self) -> str:
        return self._value

    @value.setter
    def value(self, value: str):
        if not isinstance(value, str):
            raise TypeError(f"value {type(value)} not supported")
        self._value = value

    @property
    def id(self) -> str:
        return self._id

    @id.setter
    def id(self, value: str):
        # This validated and stored the *builtin* `id` rather than the argument, so every
        # assignment raised TypeError (a builtin_function_or_method is never a str).
        if not isinstance(value, str):
            raise TypeError(f"value {type(value)} not supported")
        self._id = value


class NumberField(SubBaseField):
    field_type = SubFieldType.NUMBER
    default = "0"

    @property
    def value(self) -> str:
        return self._value

    @value.setter
    def value(self, value: str | float | int):
        if isinstance(value, bool):
            raise TypeError(f"value {type(value)} not supported")
        if isinstance(value, float) or isinstance(value, int):
            value = str(value)
        if not isinstance(value, str):
            raise TypeError(f"value {type(value)} not supported")
        # '' is what the designer stores for a new or cleared number sub-field
        if value != '' and NUMBER_PATTERN.fullmatch(value) is None:
            raise ValueError(f"value must be a number: {value}")
        self._value = value


class LabelField(SubBaseField):
    field_type = SubFieldType.LABEL


class TextField(SubBaseField):
    field_type = SubFieldType.TEXT


class SystemDefinedField(SubBaseField, SystemDefined):
    field_type = SubFieldType.SYSTEM_DEFINED
    required_fields = ['option_layers', 'value_system']

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        super().__init__(sr, layer_key, json_data)
        SystemDefined.__init__(self, json_data)