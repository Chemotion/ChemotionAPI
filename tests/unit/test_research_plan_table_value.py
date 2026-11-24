"""#25: a research-plan table keeps every key of its value (the web editor's AG Grid
`columnStates`, and any key the client does not know), not only `columns` and `rows`."""
import copy

from chemotion_api.elements.research_plan import ResearchPlan, Table

_STATES = [{'colId': 'a', 'width': 350, 'hide': False, 'sort': 'asc', 'pinned': 'left'}]


def _field():
    # The ELN (3.1.4 as 4.0.2) keeps `startCollapsed` inside the value.
    return {'id': 't1', 'type': 'table',
            'value': {'columns': [{'headerName': 'A', 'field': 'a', 'colId': 'a'}],
                      'rows': [{'a': '1'}],
                      'columnStates': _STATES,
                      'unknownKey': {'x': 1},
                      'startCollapsed': False}}


def test_a_table_keeps_column_states():
    t = Table('id-1', {'columns': [{'field': 'a'}], 'rows': [], 'columnStates': _STATES})
    assert t['value']['columnStates'] == _STATES


def test_an_unchanged_table_is_saved_as_the_server_sent_it():
    plan = ResearchPlan.__new__(ResearchPlan)
    field = _field()
    sent = plan._reparse_table(plan._parse_table(copy.deepcopy(field)))
    assert sent == field


def test_column_states_survive_changing_rows_and_columns():
    plan = ResearchPlan.__new__(ResearchPlan)
    table = plan._parse_table(_field())
    table.add_columns('B')
    table.add_row('2', '3')
    sent = plan._reparse_table(table)['value']
    assert sent['columnStates'] == _STATES and sent['unknownKey'] == {'x': 1}
    assert len(sent['rows']) == 2 and len(sent['columns']) == 2


def test_a_collapsed_table_stays_collapsed():
    plan = ResearchPlan.__new__(ResearchPlan)
    field = _field()
    field['value']['startCollapsed'] = True
    table = plan._parse_table(copy.deepcopy(field))
    assert table['startCollapsed'] is True
    assert plan._reparse_table(table) == field
