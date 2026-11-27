from chemotion_api.labImotion.items.options import FieldType, SubFieldType, SubTableFieldType
from chemotion_api.labImotion.items.validation.registry import SchemaRegistry

#: Types of input-group sub-fields and table columns this client models.
_KNOWN_SUB_FIELD_TYPES = sorted(set(SubFieldType.list()) | set(SubTableFieldType.list()))

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
        # Any string, not FieldType.list(): a type this client has no class for is kept as an
        # OpaqueField and round-trips. An enum here rejected the whole klass instead, and every
        # element using it became unreadable (issue #58: 'number', 'ontology-select').
        "type": {
            "type": "string",
            "minLength": 1
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
                    }
                },
                # A sub-field of a known type may carry only the keys below, with these types; one of
                # a type this client does not know may carry any keys and values and is kept as it is
                # (TSOpaque), so its keys are not checked at all.
                "unevaluatedProperties": False,
                "if": {"properties": {"type": {"enum": _KNOWN_SUB_FIELD_TYPES}}},
                "then": {
                    "properties": {
                        "value": {
                            "type": "string"
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
                        # ELN v4 / LabIMotion 2.3 additions.
                        "_checksum": {
                            "type": ["string", "null"]
                        },
                        "is_new": {
                            "type": ["boolean", "null"]
                        },
                        # A formula column of a table (ELN 4.0 designer), issue #61: the formula, the
                        # columns its variables stand for, and the decimal places (an int; text read
                        # too). Read as leniently as the designer reads them: TSFormula keeps a value
                        # its setters refuse as stored.
                        "formula": {
                            "type": "string"
                        },
                        "refs": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {"id": {"type": "string"}, "abbr": {"type": "string"}},
                                "required": ["id", "abbr"]
                            }
                        },
                        "decimal": {
                            "type": ["integer", "string"]
                        },
                        # The number settings of a number column, as on a number field. The designer
                        # reads decimals with parseInt and empty bounds as unset; TSNumber keeps what
                        # its setter refuses as stored.
                        "numeric": {
                            "type": "object",
                            "properties": {
                                "decimals": {"type": ["integer", "string"]},
                                "min": {"type": ["number", "string", "null"]},
                                "max": {"type": ["number", "string", "null"]}
                            }
                        }
                    }
                },
                "else": {"additionalProperties": True},
                # `value` is no longer required — v4 omits it on freshly added sub-fields.
                "required": [
                    "id",
                    "type"
                ]
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
            "type": "string"
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
        # Written by the ELN's template designer (chem-generic-ui, ELN 4.0.2), issue #58: the base
        # unit it backfills on system-defined fields, the settings of a 'number' field and the
        # root term of an 'ontology-select' field. Shapes as in the designer's own field schema.
        "value_system_base": {
            "type": "string"
        },
        "numeric": {
            "type": "object",
            "properties": {
                "decimals": {"type": "integer", "minimum": 0},
                "min": {"type": ["number", "string"]},
                "max": {"type": ["number", "string"]}
            },
            "additionalProperties": False
        },
        "ontology_term": {
            "type": ["object", "string", "null"]
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
        }
    },
    # A field of a known type may carry only the keys above (a key the server starts sending
    # fails loudly, see tests/unit/test_klass_schema_fields.py). A field of a type this client
    # does not know may carry any keys: it is kept as an OpaqueField, which round-trips them.
    "unevaluatedProperties": False,
    "if": {"properties": {"type": {"enum": FieldType.list()}}},
    "else": {"additionalProperties": True},
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
