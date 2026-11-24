Generic field values
====================

The fields of LabIMotion templates (see :doc:`LabIMotionTemplates`) are filled in three places, all with
the same rules:

* a generic element's own fields: ``elem.properties[layer][field]`` (:doc:`GenericElementsDetails`),
* the segments of any element: ``element.segments[segment][layer][field]`` (:doc:`Segments`),
* the metadata of a dataset: ``dataset[layer][field]`` (:doc:`Analyses`).

Layers and fields are addressed by their labels in the template version the element, segment or dataset
was made with. Each value has the shape the ELN web form (chem-generic-ui 2.3.2, LabIMotion 2.3.4) stores.

.. code-block:: python

    import datetime

    elem = collection.new_generic_by_label('Micro Biology')
    layer = elem.properties['Cultivation']
    layer['Strain'] = 'E. coli K12'                                # text
    layer['Replicates'] = 3                                        # number
    layer['Growth medium'] = 'TB'                                  # select: key or label
    layer['Selection'] = ['Amp', 'Kan']                            # select-multi: keys or labels
    layer['Temperature'] = {'value': 37, 'unit': 'C'}              # system-defined
    layer['Start'] = datetime.datetime(2025, 3, 1, 9, 30)          # datetime
    layer['Finished'] = True                                       # checkbox
    layer['Measurements'] = [{'Probe': 'P1', 'Mass': 1.25}, {'Probe': 'P2'}]   # table rows
    elem.save()

    elem.field('Cultivation', 'Growth medium').options()           # [{'key': 'LB', 'label': 'LB'}, ...]
    elem.field('Cultivation', 'Temperature').units()               # ['C', 'F', 'K']
    elem.field('Cultivation', 'Replicates').numeric                # {'decimals': 0, 'min': 1, 'max': 12}

``elem.field(layer, field)`` and ``element.segments.field(segment, layer, field)`` return the template
field (:class:`~chemotion_api.utils.segment_fields.SegmentField`) with its type, options, units,
``numeric`` and ontology term.

Values by field type
--------------------

A field that was never filled may read as None. "Checked" values raise ``ValueError`` on ``save()`` when
they do not fit; the message names the field.
Only changed values are checked: a value read from the server can always be saved again, even if it no
longer fits the template.

.. list-table::
   :header-rows: 1
   :widths: 18 42 40

   * - Field type
     - Value (read and written)
     - Checked / converted on write
   * - text, textarea
     - ``str``
     - stored as given
   * - number
     - a number (``int`` or ``float`` when written by the client); ``''`` for none
     - must be a number (``'2,5'`` and ``'2.5'`` are read as 2.5); at most ``numeric['decimals']``
       places (a field without ``numeric``: whole numbers only) and within ``min``/``max``; stored as a
       number
   * - integer (deprecated)
     - as stored
     - must be a whole number; stored as given (``'3'`` stays a string)
   * - checkbox
     - ``True`` or ``False``
     - only ``bool`` is accepted
   * - select
     - the option key; ``''`` for none
     - option key or label, stored as the key. With the system user list (``'-su03-'``): a user id,
       stored as a string
   * - select-multi
     - list of option keys, ``[]`` for none
     - a list (or one item) of keys or labels; stored as keys without duplicates
   * - system-defined
     - ``{'value': ..., 'unit': ...}``
     - the value must be a number or ``''``/None; the unit must be one of the field's unit type. A bare
       number gets the field's default unit
   * - datetime
     - ``'DD/MM/YYYY HH:mm:ss'``; None or ``''`` if empty
     - a :class:`datetime.datetime` (or date) is formatted so; strings are stored as given; None removes
       the value
   * - datetime-range
     - ``{'timeStart': str, 'timeStop': str, 'duration': {'value', 'unit'}}``
     - a dict with any of the three parts; only those change. Times as for datetime. ``duration`` takes
       ``{'value', 'unit'}`` or a bare number (current unit); the unit must be a duration unit (``d``,
       ``h``, ``min``, ``s``, ``y``). The duration is not computed from start and stop
   * - ontology-select
     - the label of the chosen term (``str``), ``''`` or None
     - must be a string; not checked against the ontology
   * - formula-field
     - the stored result
     - stored as given; the client never computes formulas
   * - text-formula
     - None (the form shows the joined text without storing it)
     - a value written is stored as given; nothing is computed
   * - dummy
     - None
     - nothing to write
   * - input-group
     - list of the parts' values in order, e.g. ``['OD', 0.5, '', {'value': 600, 'unit': 'nm'}]``
     - a list of at most as many values as parts; ``number`` parts must be numbers; ``system-defined``
       parts as for system-defined fields; the others as given. The label part holds the label text:
       leave it as read
   * - table
     - list of :class:`~chemotion_api.utils.TableRow` (``{column heading: cell}``)
     - see `Tables`_
   * - drag_element
     - ``{'value': {...}}`` (``value`` is ``''`` when empty)
     - write ``{'value': <the el_* dict>}``; stored as given
   * - drag_sample, drag_molecule
     - the dropped item's ``el_*`` dict, ``''`` when empty
     - stored as given
   * - upload
     - ``{'files': [{'uid', 'filename', 'aid', ...}]}``
     - stored as given; files cannot be uploaded (see `Limits`_)

``wf-next`` fields are not shown in ``properties``; use the workflow methods of
:class:`~chemotion_api.elements.generic_element.GenericElement`.

Tables
------

A table reads as a list of :class:`~chemotion_api.utils.TableRow`, a ``dict`` of ``{column heading:
cell}`` with the ELN's row id in ``row_id``. The table ends up with exactly the rows you give, in that
order: rows can be added, removed, reordered and edited.

.. code-block:: python

    rows = elem.properties['Cultivation']['Measurements']
    rows.append({'Probe': 'P3', 'Mass': 0.5, 'Temperature': 20})   # a new row; missing cells stay empty
    rows[0]['Medium'] = 'LB broth'
    del rows[1]                                                    # removed on save
    elem.properties['Cultivation']['Measurements'] = rows[::-1]   # reordered
    elem.save()

Rows read from the server keep their id and their unchanged cells; any other row (a plain ``dict``) is a
new row with a new id, starting from the cells the web form gives a new row. An unknown column heading
raises ``ValueError``.

Cells read and write like the field of the column type:

============================  ======================================================================
Column type                   Cell
============================  ======================================================================
text                          ``str`` (other values are converted with ``str()``)
number                        a number or ``''``, checked against the column's ``numeric``
select                        option key (key or label accepted)
select-multi                  list of option keys (keys or labels accepted)
system-defined                ``{'value', 'unit'}``; a bare number gets the column's default unit
formula-field                 the stored result; must be a number or ``''`` (not recomputed)
drag_molecule, drag_sample    the dropped item's ``el_*`` dict, ``''`` when empty
============================  ======================================================================

Cells written in the stored shape (``{'value': ...}``, ``{'value', 'value_system'}``) are accepted too.
Cells of column types the client does not know are read and written as stored.

.. note::
   Since pull request #41 (after 403.0.1-rc.1) table cells read like their field type. Before, cells
   other than text were the raw stored dicts (``{'value': ...}``, system-defined ``{'value',
   'value_system'}``), and removing rows left old rows behind.

Segments and datasets
---------------------

.. code-block:: python

    cell = sample.segments.get('Electrochemistry')['Cell']     # .get() adds the segment if missing
    cell['Electrode type'] = 'disk'
    cell['Temperature'] = 25                                    # default unit
    sample.save()

    ds = sample.analyses.by_name('NMR').dataset_by_name('V1')
    ds['Instrument']['Solvent'] = 'CDCl3'                       # dataset metadata, the same rules
    sample.save()                                               # or sample.save_analyses()

Select options of a saved record are taken from its template release, because the ELN does not keep
them in the record. A dataset's metadata form is the dataset klass the server chose for the analysis
kind; it is empty if the dataset has none, and the client cannot attach one.

Segment fields in reaction variations follow their own rules (see :doc:`ReactionDetails`).

Limits
------

The client does not:

* upload files into upload fields (element attachments and analyses work as usual);
* fill drag fields from client objects (``Sample``, ``Molecule``, elements): write the ``el_*`` dict the
  web form stores, e.g. copied from another element;
* compute formula-field, text-formula and table formula values, or the duration of a datetime range;
* check required fields or evaluate restrictions (hidden fields can be written);
* move an element to a newer template version;
* support LabIMotion 2.4 features (cover images, klass sharing, AI filling, Link Element table columns).

Generic elements have no comments, private notes, version history or literature references in the ELN:
:meth:`~chemotion_api.elements.abstract_element.AbstractElement.comments`,
:meth:`~chemotion_api.elements.abstract_element.AbstractElement.private_note`,
:meth:`~chemotion_api.elements.abstract_element.AbstractElement.versions`,
:meth:`~chemotion_api.elements.abstract_element.AbstractElement.references` and the matching add/set
calls raise ``ValueError`` for them. User labels are not supported for generic elements by the client:
:attr:`~chemotion_api.elements.abstract_element.AbstractElement.user_labels_resolved` is empty, and
``properties`` holds only layers (a key ``'user_labels'`` is an unknown layer and raises ``ValueError``
on save).

API classes
-----------

.. autoclass:: chemotion_api.utils.TableRow

.. autofunction:: chemotion_api.utils.clean_generic_field
