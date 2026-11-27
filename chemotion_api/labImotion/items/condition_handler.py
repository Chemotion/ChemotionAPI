from __future__ import annotations
import uuid

from chemotion_api.labImotion.items.options import ConditionOperator, FieldType
from chemotion_api.labImotion.structure import StructureRegistry

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chemotion_api.labImotion.items.fields import SelectField, TextField, CheckboxField


class ConditionHandler:
    def __init__(self, sr: StructureRegistry):
        if not hasattr(self, '_sr'):
            self._sr = sr
        self._cond_fields = None
        self._cond_operator = None

    def add_condition(self, field: SelectField | TextField | CheckboxField, value: str | bool):
        if field.field_type == FieldType.SELECT:
            options = self._sr.get_select_options().get(field.option_layers)
            if options is None:
                raise ValueError(f'Select field "{field.field}" uses the option list "{field.option_layers}", '
                                 'which the template does not define')
            if value not in options:
                # Not a key: take the option whose label it is, and store its key
                value = next((key for key, label in options.items() if label == value), None)
            if value is None:
                raise ValueError(f"Value must be an option label or key: labels {', '.join(map(str, options.values()))}"
                                 f"; keys {', '.join(map(str, options.keys()))}")


        elif field.field_type == FieldType.TEXT:
            if not isinstance(value, str):
                raise ValueError('Condition value for text fields must be a string')
        elif field.field_type == FieldType.CHECKBOX:
            if isinstance(value, bool):
                value = 'true' if value else 'false'
            if value not in ['true', 'false']:
                raise ValueError('Condition value for checkboxes must be "true" or "false"')
        else:
            raise ValueError(f"Only Fields of type [{FieldType.CHECKBOX}, {FieldType.TEXT}, {FieldType.SELECT}]")

        if self.cond_fields is None:
            self.cond_fields = []
        self.cond_fields.append({
            "id": uuid.uuid4().__str__(),
            "field": field.field,
            "label": "TEST",
            "layer": field.layer_key,
            "value": value
        })

    @property
    def cond_fields(self) -> list | None:
        return self._cond_fields

    @cond_fields.setter
    def cond_fields(self, value: list | None):
        if value is None:
            self._cond_operator = None
            self._cond_fields = None
            return
        if not isinstance(value, list):
            raise TypeError(f"cond_fields {type(value)} not supported")
        self._cond_fields = value

    @property
    def cond_operator(self) -> ConditionOperator | None:
        if self.cond_fields is not None and self._cond_operator is None:
            return ConditionOperator.MATCH_ONE
        return self._cond_operator

    @cond_operator.setter
    def cond_operator(self, value: ConditionOperator | int | None):
        if value is None:
            # With conditions set, None means the default operator
            self._cond_operator = None if self.cond_fields is None else ConditionOperator.MATCH_ONE
            return
        if isinstance(value, int):
            value = ConditionOperator(value)
        if not isinstance(value, ConditionOperator):
            raise TypeError(f"cond_operator {type(value)} not supported")
        self._cond_operator = value
