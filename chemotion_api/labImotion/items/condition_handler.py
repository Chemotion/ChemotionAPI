from __future__ import annotations
import uuid

from chemotion_api.labImotion.items.options import ConditionOperator, FieldType
from chemotion_api.labImotion.structure import StructureRegistry

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chemotion_api.labImotion.items.fields import BaseField

#: The field types the designer offers as the source of a restriction (chem-generic-ui ``u42``).
CONDITION_SOURCE_TYPES = (FieldType.CHECKBOX, FieldType.TEXT, FieldType.SELECT, FieldType.ONTOLOGY_SELECT)


class ConditionHandler:
    """Restrictions ("Restriction Setting" in the template designer) of a field or a layer: it is
    shown only if the values of other fields match (``cond_fields``), combined by
    ``cond_operator``."""

    def __init__(self, sr: StructureRegistry):
        if not hasattr(self, '_sr'):
            self._sr = sr
        self._cond_fields = None
        self._cond_operator = None

    def add_condition(self, field: BaseField, value: str | bool, label: str = '') -> dict:
        """
        Adds a restriction: this field or layer is shown only if ``field`` has ``value``. The condition is
        stored the way the template designer stores it.

        >>> layer.add_condition(medium_field, 'LB broth')   # option label or key
        >>> notes.add_condition(done_checkbox, True, label='Finished')

        :param field: the source field, of type checkbox, text, select or ontology-select
        :param value: checkbox: a bool (or 'true'/'false'); select: the key or the label of an option (the
            key is stored); text and ontology-select: the text to match
        :param label: the "Display as" text of the condition (the designer stores ``''`` if none is given)
        :return: the new condition

        :raises ValueError: if the field type cannot be a source or the value does not fit it
        """
        if not isinstance(label, str):
            raise TypeError(f"label {type(label)} not supported")
        if field.field_type == FieldType.SELECT:
            options = self._sr.get_select_options().get(field.option_layers, {})
            if value not in options:
                value = next((key for key, option_label in options.items() if option_label == value), None)
            if value is None:
                raise ValueError(f"Value must be one of the options {', '.join(map(str, options.values()))} "
                                 f"(label or key)")
        elif field.field_type in (FieldType.TEXT, FieldType.ONTOLOGY_SELECT):
            if not isinstance(value, str):
                raise ValueError(f'Condition value for {field.field_type.value} fields must be a string')
            value = value.strip()
        elif field.field_type == FieldType.CHECKBOX:
            # The designer stores a boolean (``a3()``: anything but '', 'false' and '0' is true)
            if isinstance(value, str) and value.lower() in ('true', 'false'):
                value = value.lower() == 'true'
            if not isinstance(value, bool):
                raise ValueError('Condition value for checkboxes must be True or False')
        else:
            raise ValueError(f"Only fields of type {', '.join(t.value for t in CONDITION_SOURCE_TYPES)} can be used")

        condition = {
            "id": f"{uuid.uuid4()}-fc",
            "field": field.field,
            "layer": field.layer_key,
            "value": value,
            "label": label.strip()
        }
        self.cond_fields = (self.cond_fields or []) + [condition]
        return condition

    def _write_conditions(self, data: dict) -> None:
        """Write the restrictions into the serialized field or layer ``data``. Cleared restrictions remove
        both keys, as the designer does; a loaded empty list stays as it was."""
        if self.cond_fields is None:
            if data.get('cond_fields'):
                data.pop('cond_fields')
                data.pop('cond_operator', None)
            return
        data['cond_fields'] = self.cond_fields
        data['cond_operator'] = self.cond_operator.value

    @property
    def cond_fields(self) -> list | None:
        """The restrictions (dicts ``{id, field, layer, value, label}``), or None. Setting None or an empty
        list removes all restrictions, as the designer does."""
        return self._cond_fields

    @cond_fields.setter
    def cond_fields(self, value: list | None):
        if value is None or value == []:
            self._cond_operator = None
            self._cond_fields = None
            return
        if not isinstance(value, list):
            raise TypeError(f"cond_fields {type(value)} not supported")
        self._cond_fields = value

    @property
    def cond_operator(self) -> ConditionOperator | None:
        """How the restrictions are combined (default: :attr:`ConditionOperator.MATCH_ONE`)."""
        if self.cond_fields is not None and self._cond_operator is None:
            return ConditionOperator.MATCH_ONE
        return self._cond_operator

    @cond_operator.setter
    def cond_operator(self, value: ConditionOperator | int | None):
        if value is None:
            if self.cond_fields is None:
                self._cond_operator = None
                return
            else:
                value = ConditionOperator.MATCH_ONE
        if isinstance(value, int):
            value = ConditionOperator(value)
        if not isinstance(value, ConditionOperator):
            raise TypeError(f"cond_operator {type(value)} not supported")
        self._cond_operator = value
