import re
import warnings
from enum import Enum

from chemotion_api.labImotion.items.condition_handler import ConditionHandler
from chemotion_api.labImotion.items.fields import BaseField, field_factory, FieldType, create_field
from chemotion_api.labImotion.items.fields.abstract_fields import Select
from chemotion_api.labImotion.items.options import LayerColor
from chemotion_api.labImotion.items.validation import validate_generic_layer
from chemotion_api.labImotion.structure import StructureRegistry
from chemotion_api.labImotion.utils import ChemotionSerializable, all_instances_of, generate_key


class Layer(ChemotionSerializable, ConditionHandler):
    """A layer (section) of a template.

    :meth:`to_dict` writes the modelled attributes over the layer as it was loaded, so keys this client
    does not model (``label_fields``, ``wf_info``, ``ai`` and the like) are saved unchanged.
    """
    #: Attributes written by :meth:`to_dict` (besides the restrictions) when they were loaded or set.
    _attributes = ('key', 'label', 'color', 'style', 'cols', 'position', 'wf', 'wf_position', 'timeRecord', 'fields')

    @classmethod
    def generate_new_layer(cls, sr: StructureRegistry, key: str, label: str):
        return cls(sr, {
            "key": key,
            "label": label,
            "color": "none",
            "style": "panel_generic_heading",
            "cols": 1,
            "position": 10,
            "wf": False,
            "timeRecord": "",
            "wf_position": 0,
            "fields": []
        })

    def __init__(self, sr: StructureRegistry, json_data: dict):
        ConditionHandler.__init__(self, sr)
        self._json_data = json_data
        self.validate()
        self._wf = False
        self._key = ''
        self._style = 'panel_generic_heading'
        self._label = ''
        self._cols = 1
        self._color = ''
        self._position = 1
        self._wf_position = 1
        self._timeRecord = ''
        self._fields = []
        self._sr = sr

        # The key first: the fields take their layer key from it.
        for key, value in sorted(json_data.items(), key=lambda item: item[0] != 'key'):
            if hasattr(self, key):
                setattr(self, key, value)
        #: Attributes set after loading that the loaded layer did not have.
        self._set_attributes: set[str] = set()

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        if name in self._attributes and hasattr(self, '_set_attributes'):
            self._set_attributes.add(name)

    def add_field(self, field_type: FieldType, label: str, field: str = "", idx: int = -1,
                  options: list[str] | None = None, ontology: dict | str | None = None) -> BaseField:
        """
        Adds a new field to the layer, set up as the template designer sets up a new field of that type.

        >>> layer.add_field(FieldType.TEXT, 'Strain')
        >>> layer.add_field(FieldType.SELECT, 'Medium', options=['LB', 'TB'])
        >>> layer.add_field(FieldType.TEXT, 'NMR method', ontology='CHMO:0000593')
        >>> layer.add_field(FieldType.NUMBER, 'Replicates').set_numeric(decimals=0, min=1)

        For a number use ``FieldType.NUMBER``. ``FieldType.INTEGER`` also creates a ``number`` field (with
        0 decimal places) and warns: the designer (chem-generic-ui 2.3.2) offers only "Number" and turns
        every ``integer`` field into ``number`` with ``numeric.decimals = 0`` whenever it saves a template,
        so an ``integer`` field would not survive the next save in the web interface anyway. Templates
        that already contain ``integer`` fields load and save unchanged.

        :param field_type: the type of the field
        :param label: the label shown in Chemotion
        :param field: the key of the field. If empty, it is generated from the label
        :param idx: the position in the layer. Negative values append the field
        :param options: only for SELECT and SELECT_MULTI fields: creates a new select option list (option layer)
            with these entries and links the field to it
        :param ontology: an ontology term (dict or term ID) linked to the field, see :attr:`BaseField.ontology`
        :return: the new field

        :raises ValueError: if the key is already used in this layer
        """
        all_keys = [l.field for l in self.fields if l.field is not None]
        if field == '':
            field = generate_key(label, all_keys, max_len=40, fallback='field')
        elif field in all_keys:
            raise ValueError(f'A field with the key "{field}" already exists in layer "{self.key}"')
        if options is not None and field_type not in (FieldType.SELECT, FieldType.SELECT_MULTI):
            raise ValueError('options are only supported for SELECT and SELECT_MULTI fields')
        if field_type == FieldType.INTEGER:
            warnings.warn('The integer field type is deprecated in LabIMotion; a number field with 0 decimal '
                          'places is created instead. Use FieldType.NUMBER.', DeprecationWarning, stacklevel=2)
            field_type = FieldType.NUMBER

        new_field = create_field(self._sr, self.key, field_type, label, idx, field)
        new_field.ontology = ontology
        if isinstance(new_field, Select) and options is not None:
            properties = self._sr.get_properties()
            if properties is None:
                raise ValueError('options can only be added to a template with properties')
            new_field.option_layers = properties.add_select_option(field, options)
        if idx < 0 :
            self.fields.append(new_field)
        else:
            self.fields.insert(idx, new_field)
        self.update_fields_position()
        return new_field

    def update_fields_position(self):
        i = 1
        for f in self.fields:
            f.position = i
            i += 1


    def validate(self, json_data: dict = None):
        if json_data is None:
            json_data = self._json_data
        validate_generic_layer(json_data)

    def to_dict(self) -> dict:
        """The layer as the server stores it.

        :return: the layer as a ``dict``
        """
        keys = [key for key in self._attributes if key in self._json_data or key in self._set_attributes]
        for key in keys:
            value = getattr(self, key)
            if isinstance(value, Enum):
                value = value.value
            if all_instances_of(value, ChemotionSerializable):
                self._json_data[key] = [x.to_dict() for x in value]
            else:
                self._json_data[key] = value
        self._write_conditions(self._json_data)
        return self._json_data

    @property
    def fields(self) -> list[BaseField]:
        return self._fields

    @fields.setter
    def fields(self, value: list[dict | BaseField]):
        self._fields = []
        for field in value:
            if isinstance(field, BaseField):
                self._fields.append(field)
            elif isinstance(field, dict):
                self._fields.append(field_factory(self._sr, self.key, field))

    @property
    def timeRecord(self) -> str:
        """The time recorded for the layer in an element ("Record time", ``DD/MM/YYYY HH:mm:ss``); ``''`` in
        a new template."""
        return self._timeRecord

    @timeRecord.setter
    def timeRecord(self, time_rec: str):
        if not isinstance(time_rec, str):
            raise TypeError('timeRecord must be a string')
        self._timeRecord = time_rec

    @property
    def wf(self) -> bool:
        return self._wf

    @wf.setter
    def wf(self, wf: bool):
        if isinstance(wf, bool):
            self._wf = wf
        else:
            raise TypeError('wf must be a boolean')

    @property
    def key(self) -> str:
        return self._key

    @key.setter
    def key(self, key: str):
        if isinstance(key, str):
            self._key = key
        else:
            raise TypeError('key must be a string')

    @property
    def style(self) -> str:
        return self._style

    @style.setter
    def style(self, style: str):
        if re.match(r'^panel_generic_heading$|^panel_generic_heading_([bui])(?!.*\1)([bui])?(?!.*\1|.*\2)([bui])?$',
                    style) is not None:
            self._style = style
        else:
            raise TypeError('style must be a string')

    @property
    def label(self) -> str:
        return self._label

    @label.setter
    def label(self, label: str):
        if isinstance(label, str):
            self._label = label
        else:
            raise TypeError('label must be a string')

    @property
    def color(self) -> str:
        return self._color

    @color.setter
    def color(self, color: str | LayerColor):
        if isinstance(color, str):
            color = LayerColor(color)
        if isinstance(color, LayerColor):
            self._color = color
        else:
            raise TypeError(f'color must be a string and in [{", ".join(LayerColor.list())}]')

    @property
    def cols(self) -> int:
        return self._cols

    @cols.setter
    def cols(self, cols: int):
        if isinstance(cols, int) and cols > 0:
            self._cols = cols
        else:
            raise TypeError('cols must be a integer and cols > 0')

    @property
    def wf_position(self) -> int:
        return self._wf_position

    @wf_position.setter
    def wf_position(self, wf_position: int):
        if isinstance(wf_position, int) and wf_position >= 0:
            self._wf_position = wf_position
        else:
            raise TypeError('wf_position must be a integer and cols >= 0')

    @property
    def position(self) -> int:
        return self._position

    @position.setter
    def position(self, position: int):
        if isinstance(position, int) and position >= 0:
            self._position = position
        else:
            raise TypeError('position must be a integer and position >= 0')
