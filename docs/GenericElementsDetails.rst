Generic Elements
======================

Generic elements are element types defined by the administration of a Chemotion instance with LabIMotion.
They are loaded with :meth:`chemotion_api.Instance.get_generic_by_name` or
:meth:`chemotion_api.Instance.get_generic_by_label`, listed with
:meth:`chemotion_api.collection.Collection.get_generics_by_name` or
:meth:`chemotion_api.collection.Collection.get_generics_by_label`, and created with
:meth:`chemotion_api.collection.Collection.new_generic` or
:meth:`chemotion_api.collection.Collection.new_generic_by_label`.

Their templates can be loaded and edited with the :class:`chemotion_api.labImotion.GenericManager`
(:meth:`chemotion_api.Instance.generic_manager`). A template is a
:class:`chemotion_api.labImotion.GenericElementKlass` (formerly ``labImotion.GenericElement``); the element
exposes the label, name and version of its template as :attr:`~GenericElement.label`,
:attr:`~GenericElement.klass_name` and :attr:`~GenericElement.klass_version`.

The server sets the short label of a new element on its first save: the creator's initials, the template's
``klass_prefix`` and a counter of the user's elements of this type, e.g. ``API-WRK10``.

Layers and workflows
--------------------

Layers without fields appear in ``properties`` as empty dicts; :meth:`~GenericElement.layers_without_fields`
lists them. The generic segments of the element type are listed by ``elem.segments.available()``.

``properties`` holds the layers by their label: ``properties['Nr 1']['name_one']``. A layer that is used more
than once (e.g. in two workflows) gets a suffix taken from its layer key: the layer ``three.1`` is
``properties['Nr 3.1']``. The suffix belongs to the layer, so the names stay the same when the element is
saved and loaded again. Layers are ordered by position and workflow step.

The next steps of the workflows are listed by :meth:`~GenericElement.wf_next_options`; each option names its
workflow (``wf_idx``, ``wf_id``) and template layer (``layer_key``, ``layer_label``) and can be passed to
:meth:`~GenericElement.wf_next`, which returns the key of the new layer in ``properties``::

    option = next(o for o in elem.wf_next_options() if o['wf_idx'] == 1 and o['layer_label'] == 'Nr 4')
    key = elem.wf_next(**option)
    elem.properties[key]['name_four'] = 'done'

:meth:`~GenericElement.wf_workflows` lists the layers of each workflow with their ``properties`` key, and
:meth:`~GenericElement.wf_layer` returns a layer by workflow and label or key: ``elem.wf_layer(1, 'Nr 3')``.

Creating a template
-------------------

:meth:`~chemotion_api.labImotion.GenericManager.create_new_element` creates a template and returns it. By
default it releases an empty version 0.1 and activates the template; only released and active templates can
be used for new elements. Layers and fields are added to ``klass.properties``, and a new release makes them
available::

    from chemotion_api.labImotion.items.fields import FieldType
    from chemotion_api.labImotion.items.options import SaveActionType

    gm = instance.generic_manager()
    klass = gm.create_new_element('Micro Biology', 'bug', description='...', prefix='MB')
    general = klass.properties.add_new_layer('General')
    general.add_field(FieldType.TEXT, 'Strain')
    general.add_field(FieldType.SELECT, 'Growth medium', options=['LB', 'TB'])
    klass.properties.add_new_layer('Cultivation').add_field(FieldType.INTEGER, 'Temperature (°C)')
    klass.save(SaveActionType.MINOR)   # release; SaveActionType.DRAFT only stores the template

    elem = collection.new_generic_by_label('Micro Biology')
    elem.properties['General']['Strain'] = 'E. coli K12'
    elem.save()

Notes:

* Layer and field keys are generated from the labels (``'Temperature (°C)'`` -> ``temperature_c``) unless
  given with ``key=`` / ``field=``. Keys must be unique.
* A SELECT field uses a select option list of the template. ``options=[...]`` creates one for the field;
  shared lists are created with ``klass.properties.add_select_option(key, values)`` and linked by
  ``field.option_layers = key``. ``field.options()`` lists the options of the field's list as
  ``[{'key': ..., 'label': ...}]``; all lists of the template are in ``klass.properties.select_options``.
* A NUMBER field takes optional ``field.numeric = {'decimals': 0, 'min': 0, 'max': 100}`` (every key
  optional; ``min``/``max`` may also be strings), as the template designer stores it. INTEGER is a separate
  type.
* An ONTOLOGY_SELECT field offers the terms below ``field.ontology_term``: set a term ID (looked up online),
  a term dict from :meth:`~chemotion_api.labImotion.GenericManager.search_ontology_terms`, or ``None``. It is
  stored as ``{'value': <term id>, 'label': <label>}``, like the designer stores it.
* A SYSTEM_DEFINED field may carry ``field.value_system_base``, a unit key of ``option_layers``. The template
  designer fills it in when the template is edited in the web UI; the client keeps it and never adds it.
* A field type this client does not know is kept as it is (an ``OpaqueField``), so the template still loads
  and saves.
* ``create_new_element`` refuses the label of a built-in element type ('Sample', 'Research Plan', ...)
  with ``ValueError``: the ELN would accept it without an error.
* ``field.required`` and ``field.default`` are stored in the template.
* ``field.ontology`` links a field to an ontology term, like "Link to ontology terminology" in the template
  designer. Terms come from the TIB Terminology Service (NFDI4Chem collection), the same service the
  Chemotion UI uses: set a term ID (``'CHMO:0000593'``, short form or IRI; it is looked up online), a term
  dict from :meth:`~chemotion_api.labImotion.GenericManager.search_ontology_terms`, or ``None`` to remove the
  link. ``add_field(..., ontology=...)`` does the same. On elements, ``elem.field(layer, field).ontology``
  (and ``elem.segments.field(...).ontology``) returns the term of the template.
* Elements address their fields by the labels of the template version they were created with. After a
  label change, existing elements keep the old names; unknown names raise a ``ValueError`` on save.
* The ``description`` is stored as ``desc``; the short label prefix is ``klass.klass_prefix``.
* A TABLE field's columns are added with ``table.add_subfield(SubTableFieldType.X, col_name)``: DRAG_MOLECULE,
  DRAG_SAMPLE, SELECT, SYSTEM_DEFINED, TEXT and, as in the ELN 4.0 designer, NUMBER, SELECT_MULTI and
  FORMULA_FIELD. A formula column computes its cells from other columns of the row:
  ``calc.add_ref(mass, 'm').add_ref(count, 'n'); calc.formula = 'm/n'; calc.decimal = 2`` (``refs`` is
  ``[{'id': <column id>, 'abbr': <variable>}]``, ``decimal`` defaults to 5). A column of a type this client
  does not know is kept as it is.
* ``load_all_elements()`` skips templates that do not validate (with a warning); pass ``strict=True`` to
  :meth:`GenericElementKlass.load_all` to get the error instead.
* Element types are cached by the instance. :meth:`~chemotion_api.collection.Collection.new_generic_by_label`
  reloads them if a label is unknown; ``instance.element_manager.reload()`` does it explicitly.

.. autoclass:: chemotion_api.labImotion.GenericManager
    :members: get_element, get_segment, get_dataset, load_all_elements, load_all_segments, load_all_datasets,
        create_new_element, search_ontology_terms, get_ontology_term

.. autoclass:: chemotion_api.elements.generic_element.GenericElement
    :members:

Template lifecycle, hub and variations
--------------------------------------

.. code-block:: python

    from chemotion_api.labImotion.items.options import ElementType

    gm = instance.generic_manager()
    klass = gm.get_element(name='wrk')
    klass.download('wrk.json')                      # upload() it on another ELN
    for rev in klass.revisions(): print(rev.version)
    gm.import_hub_template(gm.hub_templates(ElementType.SEGMENT)[0]['identifier'], ElementType.SEGMENT)

    element.export_docx('element.docx')
    element.save_variations({'row-1': {'properties': {}, 'metadata': {'notes': 'first'}, 'segments': {}}})
    link = element.create_mtt_request(plate)        # opens the external MTT app
    collection.split_generic_elements(element)

    klass.delete(confirm=klass.label)               # admins only, irreversible

.. autoclass:: chemotion_api.labImotion.base_generic_obj.KlassRevision

