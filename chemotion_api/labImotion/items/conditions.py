from chemotion_api.utils import FixedDict


class Condition(FixedDict):
    """A restriction entry ``{id, field, label, layer, value}`` with fixed keys. Not used by the client
    itself: :meth:`~chemotion_api.labImotion.items.condition_handler.ConditionHandler.add_condition` builds
    plain dicts."""
    def __init__(self, id: str, field: str, label: str, layer: str, value:str):
        super().__init__({
            "id": id,
            "field": field,
            "label": label,
            "layer": layer,
            "value": value
        })
