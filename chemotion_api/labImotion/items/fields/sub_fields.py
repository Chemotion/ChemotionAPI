import uuid
import re
from enum import Enum

from chemotion_api.labImotion.items.fields.abstract_fields import SystemDefined, _report_unknown_unit
from chemotion_api.labImotion.items.options import SubFieldType, FieldUnit, get_unit
from chemotion_api.labImotion.structure import StructureRegistry
from chemotion_api.labImotion.utils import ChemotionSerializable


#: A number as the designer's number inputs accept it (HTML ``type="number"``): sign, decimals, exponent.
NUMBER_PATTERN = re.compile(r'^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$')


class SubBaseField(ChemotionSerializable):
    """A sub-field of an input-group, or a column of a table.

    :meth:`to_dict` writes the modelled attributes over the sub-field as it was loaded, so keys this client
    does not model are saved unchanged.
    """
    _default_required_fields = ["id", "field_type", "value"]
    required_fields = []
    mapping = {"field_type": "type"}
    default = ""
    field_type = None

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        self._sr = sr
        self._layer_key = layer_key
        self._json_data = json_data
        self._id = json_data.get("id", uuid.uuid4().__str__())
        self._value = self.default
        value = json_data.get("value", self.default)
        try:
            self.value = value
        except (TypeError, ValueError) as e:
            # Lenient while parsing, as BaseField._parse_json: keep what the server sent.
            self._value = value
            _report_unknown_unit(f"{type(self).__name__}.value rejected the server's value {value!r} ({e})")

    def to_dict(self):
        """The sub-field as the server stores it.

        :return: the sub-field as a ``dict``
        """
        json_dict = dict(self._json_data)
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
    """A number in an input-group. The value is kept as a string, as the designer stores it; negative
    numbers and exponents ('-1.5e3') are allowed like in the designer's number input."""
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
        if value != '' and NUMBER_PATTERN.match(value) is None:
            raise ValueError(f"value must be a number: {value}")
        self._value = value


class OpaqueSubField(SubBaseField):
    """A sub-field or column of a type this client does not model. It is kept as loaded."""

    def __init__(self, sr: StructureRegistry, layer_key: str, json_data: dict):
        self.field_type = json_data.get('type')
        super().__init__(sr, layer_key, json_data)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value

    def to_dict(self):
        """The sub-field as loaded, with its ``id`` and ``value``.

        :return: the sub-field as a ``dict``
        """
        data = dict(self._json_data) | {'id': self._id}
        if 'value' in data or self._value != self.default:
            data['value'] = self._value
        return data


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