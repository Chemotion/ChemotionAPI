import copy
import uuid
from enum import Enum

from chemotion_api.labImotion.items.options import ElementType
from chemotion_api.labImotion.items.layer import Layer
from chemotion_api.labImotion.items.validation import validate_selection_options, validate_generic_properties, \
    validate_generic_dataset_properties, validate_generic_segment_properties
from chemotion_api.labImotion.structure import StructureRegistry
from chemotion_api.labImotion.utils import ChemotionSerializable, generate_key
from chemotion_api.utils import FixedDict


class GenericProperties(ChemotionSerializable):
    """The template of a LabIMotion klass (``properties_template``, or the read-only
    ``properties_release``): its :attr:`layers`, :attr:`select_options` and identity. ``klass.properties``
    of an element, segment or dataset klass is the editable one; changes reach the server with
    ``klass.save()``.

    Keys the client does not model (e.g. ``flowObject``, the workflow graph) are saved as they were
    loaded.
    """
    def __init__(self, json_data: dict, element_type: ElementType, sr: StructureRegistry):
        self._json_data = json_data
        self._element_type = element_type
        self._pkg = FixedDict(copy.deepcopy(json_data.get('pkg', {})))
        self._select_options = {}
        self._identifier = None
        self._flow_object = []
        self._version = None
        self._uuid = ''
        self._klass = ElementType.ELEMENT
        self._layers = []
        self._sr = sr

        for key, value in json_data.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def to_dict(self) -> dict:
        """The template as the server stores it: the loaded dict with the modelled attributes written
        over it.

        :return: the template as a ``dict``
        """
        for key, _ in self._json_data.items():
            if hasattr(self, key) and key != 'pkg':
                value = getattr(self, key)
                if isinstance(value, Enum):
                    value = value.value
                if key == 'layers':
                    self._json_data[key] = {x.key: x.to_dict() for x in value}
                else:
                    self._json_data[key] = value
        return self._json_data

    def validate(self, json_data: dict = None):
        """Checks the template (as loaded, or ``json_data``) against the schema of its klass kind.

        :raises jsonschema.ValidationError: if it does not fit
        """
        if json_data is None:
            json_data = self._json_data
        if self._element_type == ElementType.DATASET:
            validate_generic_dataset_properties(json_data)
        elif self._element_type == ElementType.SEGMENT:
            validate_generic_segment_properties(json_data)
        else:
            validate_generic_properties(json_data)

    def get_layer_by_label(self, label: str) -> Layer:
        """The first layer with this label.

        :raises StopIteration: if there is none
        """
        return next(l for l in self.layers if l.label == label)

    def get_layer_by_key(self, key: str) -> Layer:
        """The layer with this key.

        :raises StopIteration: if there is none
        """
        return next(l for l in self.layers if l.key == key)

    @property
    def layers(self) -> list[Layer]:
        """The layers, sorted by :attr:`~chemotion_api.labImotion.items.layer.Layer.position`. Add layers
        with :meth:`add_new_layer`; setting it to a list of layers replaces them all (a dict of layer dicts
        by key is accepted too)."""
        return self._layers

    @layers.setter
    def layers(self, values: dict | list[Layer]):
        if isinstance(values, dict):
            self._layers = []
            for key, value in values.items():
                self._layers.append(Layer(self._sr, value))
        else:
            if not isinstance(values, list):
                raise TypeError(f"layers {type(values)} not supported")
            for value in values:
                if not isinstance(value, Layer):
                    raise TypeError(f"layers -> list[{type(value)}] not supported")
            self._layers = list(values)

        self._layers.sort(key=lambda x: x.position)

    @property
    def version(self) -> str | None:
        """The version stored in the template (set by the server on release). It can be set once only."""
        return self._version

    @version.setter
    def version(self, value: str | None):
        if value is None:
            return
        if not isinstance(value, str):
            raise TypeError(f"version {type(value)} not supported")
        if self._version is not None:
            raise ValueError(f"version {self._version} already set")
        self._version = value

    @property
    def identifier(self) -> str:
        """The identifier of the template (set by the server). It can be set once only; None generates a
        UUID."""
        return self._identifier

    @identifier.setter
    def identifier(self, value: str | None):
        if value is None:
            self._identifier = uuid.uuid4().__str__()
            return
        if not isinstance(value, str):
            raise TypeError(f"identifier {type(value)} not supported")
        if self._identifier is not None:
            raise ValueError(f"identifier {self._identifier} already set")
        self._identifier = value

    @property
    def uuid(self) -> str:
        """The UUID of this template version (the server gives every save a new one). It can be set once
        only."""
        return self._uuid

    @uuid.setter
    def uuid(self, value: str):
        if not isinstance(value, str):
            raise TypeError(f"uuid {type(value)} not supported")
        if self._uuid != '':
            raise ValueError(f"uuid {self._uuid} already set")
        self._uuid = value

    @property
    def package_info(self):
        """The ``pkg`` stamp of the template (which ELN / LabIMotion / chem-generic-ui wrote it), read
        only."""
        return self._pkg

    @property
    def klass(self) -> ElementType:
        """The klass kind stored in the template (:class:`~chemotion_api.labImotion.items.options.ElementType`)."""
        return self._klass

    @klass.setter
    def klass(self, value: ElementType | str):
        if isinstance(value, str):
            value = ElementType(value)
        if not isinstance(value, ElementType):
            raise TypeError(f"klass {type(value)} not supported")
        self._klass = value

    @property
    def select_options(self) -> dict[str, dict[str, list[dict[str, str]]]]:
        """The option sets of the template: ``{key: {'options': [{'key': ..., 'label': ...}]}}``. Setting it
        checks the whole dict against the schema; :meth:`add_select_option` adds one set whose keys equal its
        labels. A set with keys that differ from the labels is added by assigning the dict."""
        return self._select_options

    @select_options.setter
    def select_options(self, value: dict[str, dict[str, list[dict[str, str]]]]):
        if not isinstance(value, dict):
            raise TypeError(f"select_options {type(value)} not supported")
        validate_selection_options(value)
        self._select_options = value

    def add_select_option(self, key: str, vals: list[str]) -> str:
        """
        Adds a select option list (option layer) that SELECT fields can use via ``field.option_layers``.

        :param key: the name of the option list. It is turned into a valid key (3-12 letters or '_') and
            made unique
        :param vals: the options
        :return: the key of the new option list
        """
        if not isinstance(vals, list) or not all(isinstance(v, str) for v in vals):
            raise TypeError('vals must be a list of strings')
        key = generate_key(key, list(self.select_options), max_len=12, fallback='opt')
        self.select_options = self.select_options | {key: {'options': [{'key': val, 'label': val} for val in vals]}}
        return key

    def add_new_layer(self, label: str, key: str = '', idx: int = -1) -> Layer:
        """
        Adds a new layer to the template.

        :param label: the label shown in Chemotion
        :param key: the key of the layer (3-22 letters or '_'). If empty, it is generated from the label
        :param idx: the position of the layer. Negative values append the layer
        :return: the new layer

        :raises ValueError: if the key is already used
        """
        all_keys = [l.key for l in self.layers]
        if key == '':
            key = generate_key(label, all_keys, fallback='layer')
        elif key in all_keys:
            raise ValueError(f'A layer with the key "{key}" already exists')
        new_layer = Layer.generate_new_layer(self._sr, key, label)
        if idx < 0 :
            self.layers.append(new_layer)
        else:
            self.layers.insert(idx, new_layer)
        self.update_layer_position()

        return new_layer

    def update_layer_position(self):
        """Renumbers the layers that are not workflow layers 10, 20, 30, ... in list order."""
        i = 10
        for layer in self.layers:
            if not layer.wf:
                layer.position = i
                i += 10

