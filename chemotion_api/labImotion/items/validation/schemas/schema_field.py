from chemotion_api.labImotion.items.options import FieldType
from chemotion_api.labImotion.items.validation.registry import SchemaRegistry

generic_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "chemotion://generic/field/draft-01",
    "title": "Schema for generic field",
    "type": "object",
    "properties": {
        # v4 emits `cols: 1` (and "1"), which the previous exclusiveMinimum/pattern pair rejected —
        # a single-column field is perfectly legal.
        "cols": {
            "oneOf": [
                {
                    "type": "number",
                    "minimum": 1
                },
                {
                    "type": "string",
                    "pattern": "^[1-9]\\d*(\\.\\d+)?$"
                }
            ]
        },
        "type": {
            "type": "string",
            "enum": FieldType.list()
        },
        "field": {
            "type": "string"
        },
        "label": {
            "type": "string"
        },
        "default": {
            "type": "string"
        },
        "position": {
            "type": "number",
            "minimum": 0
        },
        "required": {
            "type": "boolean"
        },
        "readonly": {
            "type": "boolean"
        },
        "canAdjust": {
            "type": "boolean"
        },
        "description": {
            "type": "string"
        },
        # Input-group sub-fields and table columns. Open like the designer's own field-base schema
        # (`sub_fields: {type: array, items: {type: object}}`): columns carry type-specific keys
        # (numeric, formula, decimal, refs; drag_element columns in LabIMotion 2.4) and select-multi
        # / datetime-range keep their values here.
        "sub_fields": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string"
                    },
                    "type": {
                        "type": "string"
                    },
                    "value": {
                        "type": ["string", "number", "boolean", "object", "array", "null"]
                    },
                    "value_system": {
                        "type": "string"
                    },
                    "option_layers": {
                        "type": "string"
                    },
                    "col_name": {
                        "type": "string"
                    },
                    "numeric": {
                        "$ref": "#/$defs/numeric"
                    },
                    "formula": {
                        "type": "string"
                    },
                    "decimal": {
                        "type": ["integer", "string"]
                    },
                    "refs": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["id", "abbr"]
                        }
                    },
                    # ELN v4 / LabIMotion 2.3 additions.
                    "_checksum": {
                        "type": ["string", "null"]
                    },
                    "is_new": {
                        "type": ["boolean", "null"]
                    }
                },
                "additionalProperties": True
            }
        },
        "text_sub_fields": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string"
                    },
                    "field": {
                        "type": "string"
                    },
                    "layer": {
                        "type": "string"
                    },
                    "separator": {
                        "type": "string"
                    },
                    # ELN v4 / LabIMotion 2.3 additions.
                    "_checksum": {
                        "type": ["string", "null"]
                    },
                    "is_new": {
                        "type": ["boolean", "null"]
                    }
                },
                "additionalProperties": False,
                "required": [
                    "id",
                    "field",
                    "layer",
                    "separator"
                ]
            }
        },
        "cond_fields": {
            "type": "array",
            "items": {
                "$ref": "chemotion://generic/cond_field/draft-01"
            }
        },
        "cond_operator": {
            "type": "number"
        },
        "decimal": {
            "type": ["string", "integer"]
        },
        "formula": {
            "type": "string"
        },
        "option_layers": {
            "type": "string"
        },
        "value_system": {
            "type": "string"
        },
        # ELN v4 / LabIMotion 2.3 additions.
        "placeholder": {
            "type": ["string", "null"]
        },
        "ontology": {
            "type": ["object", "array", "string", "null"]
        },
        "hasOwnRow": {
            "type": ["boolean", "string", "null"]
        },
        "value": {
            "type": ["string", "number", "boolean", "object", "array", "null"]
        },
        # Written by chem-generic-ui 2.3.2 (the designer of LabIMotion 2.3.4).
        "numeric": {
            "$ref": "#/$defs/numeric"
        },
        "value_system_base": {
            "type": "string"
        },
        "ontology_term": {
            "type": ["object", "string", "null"]
        },
        "sub_values": {
            "type": "array"
        },
        "wf_options": {
            "type": "array"
        },
        "is_voc": {
            "type": "boolean"
        }
    },
    "$defs": {
        "numeric": {
            "type": "object",
            "properties": {
                "decimals": {
                    "type": "integer",
                    "minimum": 0
                },
                "min": {
                    "type": ["number", "string"]
                },
                "max": {
                    "type": ["number", "string"]
                }
            }
        }
    },
    # Open, like the designer's own `urn:labimotion:schemas:field-base`: LabIMotion stores a field as
    # opaque JSON and the designer adds keys this schema does not know (Lab-Vocab `opid`, `source`, …).
    # A closed schema made every template with such a field unloadable — and with it every element
    # of the template — although the server accepts it. Known keys are still type-checked above.
    "additionalProperties": True,
    # sub_fields / text_sub_fields dropped from required: v4 emits them only for the field types
    # that actually have sub-fields (2609 of 2792 fields in the reference instance carry them).
    # Everything below is present on every field observed, so it stays required.
    "required": [
        "type",
        "field",
        "label",
        "default",
        "position"
    ]

}

SchemaRegistry.instance().register(generic_schema)
