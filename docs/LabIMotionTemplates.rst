LabIMotion templates
====================

A LabIMotion template (a *klass*) defines a generic element type, a generic segment or the metadata form
of a dataset. It consists of layers (sections), each with fields, and of option sets for select fields.
This page shows how to build and change templates with the client; :doc:`GenericFieldValues` shows how to
fill the elements, segments and datasets made from them.

Templates are managed with the :class:`chemotion_api.labImotion.GenericManager`. Changing templates needs
the LabIMotion admin rights of the ELN (see :meth:`chemotion_api.user.Admin.set_user_rights`). The
reference is LabIMotion 2.3.4 with chem-generic-ui 2.3.2, as shipped in ELN 4.0.2.

.. code-block:: python

    from chemotion_api.labImotion.items.fields import FieldType
    from chemotion_api.labImotion.items.options import (SaveActionType, SubFieldType, SubTableFieldType,
                                                        FieldUnit, LayerColor, ConditionOperator, ElementType)

    gm = instance.generic_manager()
    klass = gm.get_element('wrk')                       # or gm.get_element(label='Workflow', version='2.0')
    segment = gm.get_segment(label='Electrochemistry')
    dataset = gm.get_dataset(ols_term_id='CHMO:0000593')

Templates are loaded from the server on every call. ``klass.properties`` is the editable template
(:class:`~chemotion_api.labImotion.items.genericproperties.GenericProperties`), ``klass.release`` the
released one (read only). Changes reach the server with ``klass.save()``.

Templates from the web designer
-------------------------------

A template made or changed in the web designer can be loaded, changed and saved with the client without
losing anything. Fields, sub-fields, table columns and layers write the attributes the client models over
the JSON they were loaded from, so keys the client does not model (drag restrictions, upload settings,
``wf-next`` options, ``sys-reaction``, Lab-Vocab keys, the workflow graph ``flowObject``, layer groups and
keys a later LabIMotion adds) are saved unchanged. Clearing a modelled attribute (setting it to ``None``)
removes its key.

Templates that use the designer's ``number`` fields, ``ontology-select`` fields or the newer table column
types load as well; the field and layer schemas accept keys they do not know.

.. note::
   This holds since the release after 403.0.1-rc.1 (pull request #40). Before, saving dropped every
   attribute the client did not model (``placeholder``, ``description``, ``hasOwnRow``, ``readonly``, the
   joined fields of a text-formula, a layer's ``timeRecord`` and more), and templates with ``number``
   fields were skipped when loading.

Layers
------

.. code-block:: python

    layer = klass.properties.add_new_layer('Cultivation')          # key 'cultivation', added at the end
    first = klass.properties.add_new_layer('Overview', key='overview', idx=0)
    layer.label = 'Cultivation conditions'
    layer.cols = 2                                                 # fields in two columns
    layer.color = LayerColor.BLUE                                  # stored as 'primary'
    layer.style = 'panel_generic_heading_bu'                       # bold and underlined heading

    klass.properties.get_layer_by_key('cultivation')
    klass.properties.get_layer_by_label('Overview')

* :attr:`~chemotion_api.labImotion.items.layer.Layer.key` is generated from the label (3-22 letters or
  ``_``, made unique) unless given. Keys must be unique; elements store their values under them.
* :attr:`~chemotion_api.labImotion.items.layer.Layer.position`: ``add_new_layer`` renumbers the layers that
  are not workflow layers 10, 20, 30, ...; ``idx`` chooses the place.
* :attr:`~chemotion_api.labImotion.items.layer.Layer.color` is a
  :class:`~chemotion_api.labImotion.items.options.LayerColor` (``NONE``, ``BLUE``, ``BLUE_LIGHT``,
  ``GREEN``, ``GREY``, ``RED``, ``ORANGE``) or its value.
* :attr:`~chemotion_api.labImotion.items.layer.Layer.style` is ``panel_generic_heading`` with an optional
  suffix of ``b`` (bold), ``u`` (underlined) and ``i`` (italic).
* :attr:`~chemotion_api.labImotion.items.layer.Layer.wf` marks a workflow layer and
  :attr:`~chemotion_api.labImotion.items.layer.Layer.wf_position` its place in the workflow. The workflow
  graph (``flowObject``, drawn in the designer) cannot be edited with the client; it is kept on save.
* :attr:`~chemotion_api.labImotion.items.layer.Layer.timeRecord` is the "Record time" text
  (``DD/MM/YYYY HH:mm:ss``); a new layer has ``''``.
* ``klass.properties.layers = [...]`` replaces all layers.

Fields
------

:meth:`~chemotion_api.labImotion.items.layer.Layer.add_field` adds a field, set up as the designer sets up
a new field of that type, and returns it:

.. code-block:: python

    strain = layer.add_field(FieldType.TEXT, 'Strain')            # key 'strain'
    notes = layer.add_field(FieldType.TEXTAREA, 'Notes', field='notes_free', idx=0)
    layer.add_field(FieldType.TEXT, 'NMR method', ontology='CHMO:0000593')

The key (``field=``) is generated from the label (lowercase letters and ``_``: ``'Temperature (°C)'`` ->
``temperature_c``) unless given; a key that is already used in the layer raises ``ValueError``. Fields are
numbered 1, 2, ... in list order (``idx`` chooses the place).

Attributes of every field (:class:`~chemotion_api.labImotion.items.fields.base.BaseField`):

=========================  ===============================================================================
Attribute                  Meaning
=========================  ===============================================================================
``label``                  "Display Name"; elements address the field by it
``field``                  the key; set once only
``required``               "Required" (stored; the client does not check it when saving an element)
``default``                the ``default`` string
``cols``                   the ``cols`` setting (None leaves it out)
``ontology``               "Term": a term dict, a term ID (``'CHMO:0000593'``, looked up in the TIB
                           Terminology Service) or None; see
                           :meth:`~chemotion_api.labImotion.GenericManager.search_ontology_terms`
``description``            "Hover Info"
``hasOwnRow``              "Has its own line" (not for dummy and table fields)
``readonly``               shown read-only in the element form
``placeholder``            text, integer and number fields only
=========================  ===============================================================================

The UI attributes ``description``, ``hasOwnRow``, ``readonly`` and ``placeholder`` are ``None`` when unset,
and setting them to ``None`` removes them.

Field types
-----------

Every member of :class:`~chemotion_api.labImotion.items.options.FieldType` can be passed to ``add_field``.

text, textarea, checkbox, datetime, datetime-range, dummy
    No settings of their own besides the attributes above.

number
    ``numeric`` sets the rounding and range ("Max Decimal Places / Min Value / Max Value"). A new number
    field has ``{'decimals': 0, 'min': '', 'max': ''}``::

        layer.add_field(FieldType.NUMBER, 'Replicates').set_numeric(decimals=0, min=1, max=12)
        od = layer.add_field(FieldType.NUMBER, 'OD600', field='od')
        od.set_numeric(decimals=3)              # arguments left out keep their value
        od.placeholder = '0.000'

integer (deprecated)
    The designer offers only "Number" and turns every ``integer`` field into ``number`` (with 0 decimal
    places) when it saves a template. So ``add_field(FieldType.INTEGER, ...)`` creates a ``number`` field
    with 0 decimal places and emits a ``DeprecationWarning``. Loaded ``integer`` fields stay
    :class:`~chemotion_api.labImotion.items.fields.fields.IntegerField` and are saved as they are.

select and select-multi
    ``option_layers`` names an option set of ``klass.properties.select_options``. ``options=[...]`` creates
    a set for the field (keys equal to the labels). Shared sets are added with
    :meth:`~chemotion_api.labImotion.items.genericproperties.GenericProperties.add_select_option`; a set
    whose keys differ from its labels is added by assigning ``select_options``. ``'-su03-'`` is the
    designer's "System user list" (the ELN's users)::

        layer.add_field(FieldType.SELECT, 'Growth medium', options=['LB', 'TB'])
        key = klass.properties.add_select_option('Antibiotics', ['Amp', 'Kan'])   # -> 'antibiotics'
        layer.add_field(FieldType.SELECT_MULTI, 'Selection').option_layers = key
        klass.properties.select_options = klass.properties.select_options | {
            'media': {'options': [{'key': 'lb', 'label': 'LB broth'}, {'key': 'tb', 'label': 'Terrific broth'}]}}
        layer.add_field(FieldType.SELECT, 'Pre-culture medium').option_layers = 'media'
        layer.add_field(FieldType.SELECT, 'Operator').option_layers = '-su03-'

    ``add_select_option`` turns the name into a key of 3-12 letters or ``_``. An unknown
    ``option_layers`` raises ``ValueError``.

system-defined
    A number with a unit. ``option_layers`` is the unit type
    (:class:`~chemotion_api.labImotion.items.options.FieldUnit`), ``value_system`` the default unit, one
    of ``UNITS[unit type]`` in :mod:`chemotion_api.labImotion.items.options`. A new field has
    ``acceleration``; changing the type resets the default unit to its first unit::

        temp = layer.add_field(FieldType.SYSTEM_DEFINED, 'Temperature')
        temp.option_layers = FieldUnit.TEMPERATURE       # value_system is now 'C'
        temp.value_system = 'K'                          # one of 'C', 'F', 'K'

formula-field
    A result computed by the element form from number, integer and system-defined fields of the **same
    layer**, addressed by their keys. ``decimal`` is the number of decimal places (a new field has
    ``'2'``), ``canAdjust`` whether the user may overwrite the result (a new field has ``True``)::

        layer.add_field(FieldType.NUMBER, 'Mass A', field='mass_a')
        layer.add_field(FieldType.NUMBER, 'Mass B', field='mass_b')
        total = layer.add_field(FieldType.FORMULA_FIELD, 'Total mass')
        total.formula = '(mass_a + mass_b) * 2'          # other names raise ValueError
        total.decimal = 3

text-formula
    Joins the values of text fields (``text_sub_fields``)::

        first = layer.add_field(FieldType.TEXT, 'Genus')
        joined = layer.add_field(FieldType.TEXT_FORMULA, 'Full name')
        joined.add_text_sub_field(first, separator=' ')          # a field object
        joined.add_text_sub_field('strain', layer='cultivation')  # or a key (and the layer key)

    The target must be a text field of the template (a table column is given as
    ``'<table key>[@@]<column id>'``); the default separator is ``'.'``.

ontology-select
    A select whose options are the sub-terms of ``ontology_term``. It is stored as the designer's term
    picker stores it, ``{'value': <terminology service id>, 'label': ...}``; it can be set to such a dict,
    a term dict, or a term ID (looked up online)::

        technique = layer.add_field(FieldType.ONTOLOGY_SELECT, 'Technique')
        technique.ontology_term = gm.get_ontology_term('CHMO:0000228')

input-group
    Several inputs on one line. Parts (:class:`~chemotion_api.labImotion.items.options.SubFieldType`) are
    ``LABEL`` (a fixed text in ``value``), ``NUMBER`` (any number, also ``-1.5e3``), ``TEXT`` and
    ``SYSTEM_DEFINED`` (with ``option_layers`` and ``value_system``)::

        group = layer.add_field(FieldType.INPUT_GROUP, 'Optical density')
        group.add_subfield(SubFieldType.LABEL).value = 'OD'
        group.add_subfield(SubFieldType.NUMBER)
        group.add_subfield(SubFieldType.SYSTEM_DEFINED).option_layers = FieldUnit.LENGTH

table
    Columns are added with ``add_subfield(type, heading)``; every
    :class:`~chemotion_api.labImotion.items.options.SubTableFieldType` is possible. Each column gets the
    settings the designer's column-type switch gives it::

        table = layer.add_field(FieldType.TABLE, 'Measurements')
        table.add_subfield(SubTableFieldType.TEXT, 'Probe')
        mass = table.add_subfield(SubTableFieldType.NUMBER, 'Mass')
        mass.set_numeric(decimals=2, min=0)
        temp = table.add_subfield(SubTableFieldType.SYSTEM_DEFINED, 'Temperature')
        temp.option_layers = FieldUnit.TEMPERATURE
        table.add_subfield(SubTableFieldType.SELECT, 'Medium').option_layers = 'media'
        table.add_subfield(SubTableFieldType.SELECT_MULTI, 'Antibiotics').option_layers = key
        double = table.add_subfield(SubTableFieldType.FORMULA_FIELD, 'Double mass')
        double.add_ref(mass, 'm')                        # only number and system-defined columns
        double.formula = 'm*2'
        double.decimal = 2                               # a new formula column has 5
        mol = table.add_subfield(SubTableFieldType.DRAG_MOLECULE, 'Molecule')
        mol.set_sample_display(inchikey=True, smiles=True, iupac=False, molecular_weight=True)
        sample = table.add_subfield(SubTableFieldType.DRAG_SAMPLE, 'Sample')
        sample.set_sample_display(name=True, external_label=False, molecular_weight=True)

    ``set_sample_display`` chooses the extra columns shown for a dropped molecule or sample; a new drag
    column shows none (``value = ''``). Column types the client does not model (LabIMotion 2.4's
    ``drag_element`` column) are kept as they were loaded.

drag_element, drag_sample, drag_molecule, upload
    Created without settings of their own. Settings made in the designer are kept on save.

date, wf-next, sys-reaction, drag, drag_reaction
    ``add_field`` creates the bare field
    (:class:`~chemotion_api.labImotion.items.fields.fields.OpaqueField`) without type settings. Loaded
    fields of these types, and of types the client does not know, keep all their keys.

Restrictions (conditions)
-------------------------

A field or a layer can be shown only when other fields have certain values ("Restriction Setting" in the
designer). The source field must be a checkbox, text, select or ontology-select field:

.. code-block:: python

    done = layer.add_field(FieldType.CHECKBOX, 'Finished')
    medium = layer.add_field(FieldType.SELECT, 'Medium')
    medium.option_layers = 'media'
    result = klass.properties.add_new_layer('Result')
    result.add_condition(done, True)                          # checkbox: True or False
    notes.add_condition(medium, 'Terrific broth', label='TB')  # select: option key or label, stores the key
    notes.add_condition(strain, 'E. coli')                     # text and ontology-select: the text
    notes.cond_operator = ConditionOperator.MATCH_ALL          # default MATCH_ONE; also MATCH_NONE
    notes.cond_fields                                          # [{'id', 'field', 'layer', 'value', 'label'}]
    notes.cond_fields = None                                   # removes all restrictions

Restrictions are stored as the designer stores them; a checkbox condition holds a boolean. The client
does not evaluate them: values of hidden fields can still be read and written.

Releasing and versions
----------------------

.. code-block:: python

    klass.save()                         # SaveActionType.DRAFT: stores the template, no new version
    klass.save(SaveActionType.MINOR)     # releases it as the next minor version
    klass.save(SaveActionType.MAJOR)     # ... or the next major version
    klass = gm.get_element('wrk')        # reload: klass.version is the new version
    for rev in klass.revisions():
        print(rev.version, rev.released_at)

* New elements (and segments, datasets) are built from the latest release. Existing elements keep the
  template version they were made with (``elem.klass_version``) and address their fields by its labels;
  the client cannot move an element to a newer template version.
* ``save()`` of an element or segment klass also sends its general attributes: ``label``, ``desc`` and,
  for element klasses, ``icon_name`` and ``klass_prefix`` (``name`` can be set once only).
* ``klass.is_active = True`` / ``klass.activate()`` / ``klass.deactivate()`` are sent right away. Only
  active, released klasses can be used for new elements.
* ``klass.validate(klass.to_dict())`` checks the klass with your changes against the client's schema;
  ``save()`` does not validate.
* :meth:`~chemotion_api.labImotion.GenericManager.write_all_validation_schemas` writes the schemas to
  ``./schemas``.

New klasses
-----------

.. code-block:: python

    klass = gm.create_new_element('Micro Biology', 'bug', description='...', prefix='MB')
    # released as an empty version 0.1 and active; release=False / activate=False skip that

    gm.create_new_segment('Cultivation', 'Cultivation data', klass)   # returns all segment klasses
    seg = gm.get_segment(label='Cultivation')
    seg.properties.add_new_layer('Conditions').add_field(FieldType.TEXT, 'Medium')
    seg.save(SaveActionType.MINOR)
    seg.activate()

A new segment klass is neither released nor active; its element klass must be active. Segment klasses
can belong to built-in element types too (see ``seg.element_klass``).

Upload, download and the LabIMotion Hub
---------------------------------------

.. code-block:: python

    klass.download('wrk.json')                     # the designer's "Download"
    gm.upload_elements_json('wrk.json')            # on another ELN; returns all element klasses
    gm.upload_segment_json('segment.json')
    gm.hub_templates(ElementType.SEGMENT)          # templates of the central hub
    gm.import_hub_template(identifier, ElementType.SEGMENT)
    gm.submit_to_hub(klass.revisions()[0], ElementType.ELEMENT, 'me@example.org', 'NMR', 'Please review')
    klass.delete(confirm=klass.label)              # irreversible, admins only

Uploaded and imported klasses that are new to the ELN are created inactive.

Dataset klasses
---------------

The metadata form of a dataset comes from the dataset klass the server picks by the analysis kind
(``dataset.ols_term_id``). With the client you can load dataset klasses, edit their layers and fields as
above, release them (``save()``), activate or deactivate them, list and delete revisions, download them,
import them from the hub and delete them.

Not possible: creating a dataset klass (the ELN has no route for it; they come from its seeds, the hub,
or in LabIMotion 2.4 its AI), uploading one (``GenericDataset.upload`` sends nothing and returns ``[]``),
and changing its ``label``, ``desc`` or ``ols_term_id`` (changed locally, but not saved).

Not supported
-------------

* Editing the workflow graph (``flowObject``) and the designer's layer groups; both are kept on save.
* Type settings of drag, upload, ``wf-next`` and ``sys-reaction`` fields; they are kept on save.
* LabIMotion 2.4 features: cover images, klass sharing, toolbar and template feature settings, AI
  endpoints, template DOIs, ``ontology_root``, restoring deleted klasses, and the ``drag_element``
  table column (kept as loaded, but cannot be created).

API classes
-----------

.. autoclass:: chemotion_api.labImotion.GenericElementKlass
    :members: klass_prefix, icon_name, name

.. autoclass:: chemotion_api.labImotion.GenericSegment
    :members: element_klass

.. autoclass:: chemotion_api.labImotion.GenericDataset
    :members: ols_term_id

.. autoclass:: chemotion_api.labImotion.base_generic_obj.GenericObj
    :members: save, activate, deactivate, label, desc, version, is_active, properties, release, revisions,
        delete_revision, download, delete, upload

.. autoclass:: chemotion_api.labImotion.items.genericproperties.GenericProperties
    :members:

.. autoclass:: chemotion_api.labImotion.items.layer.Layer
    :members:

.. autoclass:: chemotion_api.labImotion.items.condition_handler.ConditionHandler
    :members:

.. autoclass:: chemotion_api.labImotion.items.fields.base.BaseField
    :members:

.. automodule:: chemotion_api.labImotion.items.fields.fields
    :members: Placeholder, DummyField, CheckboxField, DatetimeField, DatetimeRangeField, DragElementField,
        DragMoleculeField, DragSampleField, FormulaFieldField, InputGroupField, IntegerField, NumberField,
        OntologySelectField, SelectField, SelectMultiField, OpaqueField, SystemDefinedField, TableField,
        TextFormulaField, TextField, TextareaField, UploadField
    :show-inheritance:

.. automodule:: chemotion_api.labImotion.items.fields.abstract_fields
    :members: Select, SystemDefined, Numeric

.. automodule:: chemotion_api.labImotion.items.fields.sub_fields
    :members: SubBaseField, NumberField, LabelField, TextField, SystemDefinedField, OpaqueSubField
    :show-inheritance:

.. automodule:: chemotion_api.labImotion.items.fields.table_sub_fields
    :members: TableSubBaseField, TSText, TSNumber, TSSelect, TSSelectMulti, TSSystemDefined, TSFormulaField,
        TSDragMolecule, TSDragSample
    :show-inheritance:

.. automodule:: chemotion_api.labImotion.items.options
    :members: SaveActionType, ElementType, FieldType, SubFieldType, SubTableFieldType, FieldUnit, LayerColor,
        ConditionOperator
