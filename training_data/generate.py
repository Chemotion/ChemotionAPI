"""Generate supervised fine-tuning data that teaches a model to use chemotion_api.

Sources: skills/chemotion-api/SKILL.md, skills/chemotion-api/references/api.md, docs/*.rst and the
package code. Every code block is checked by validate.py (syntax + method names exist in the package).

Output (chat format, one JSON object per line):
    {"messages": [{"role": "system"|"user"|"assistant", "content": str}, ...], "meta": {...}}

Run:  python training_data/generate.py   (deterministic, seed 7)
"""
from __future__ import annotations

import json
import random
from pathlib import Path

OUT = Path(__file__).parent
rng = random.Random(7)

SYSTEM = ("You are an assistant that writes Python code for the chemotion_api package to read and write "
          "data in a Chemotion ELN v4 electronic lab notebook. Changes affect a real lab notebook: read "
          "before you write, change only what is asked, and ask before deleting or bulk edits.")

SYSTEM_VARIANTS = [
    SYSTEM,
    "You help chemists automate their Chemotion ELN with the Python package chemotion_api.",
    "You are a coding assistant for the Chemotion ELN (v4) Python client chemotion_api.",
]

CONNECT = ("from chemotion_api import Instance\n\n"
           "instance = Instance('https://eln.example.org').test_connection().login_token('chemtoken_...')")

examples: list[dict] = []


def py(code: str) -> str:
    return f"```python\n{code.strip()}\n```"


def add(user, assistant, topic, kind='qa', system=True, history=None):
    msgs = []
    if system:
        msgs.append({'role': 'system', 'content': rng.choice(SYSTEM_VARIANTS) if system == 'any' else SYSTEM})
    for u, a in history or []:
        msgs += [{'role': 'user', 'content': u}, {'role': 'assistant', 'content': a}]
    msgs += [{'role': 'user', 'content': user}, {'role': 'assistant', 'content': assistant.strip()}]
    examples.append({'messages': msgs, 'meta': {'topic': topic, 'kind': kind}})


REPHRASE = [
    lambda q: 'In chemotion_api, ' + q[0].lower() + q[1:],
    lambda q: 'Quick question: ' + q,
    lambda q: q.rstrip('?.').lower(),
    lambda q: q + ' Show me the Python code.',
    lambda q: 'Using the Chemotion Python client: ' + q,
    lambda q: "I'm scripting our ELN. " + q,
]


def seed(topic, questions, answer, kind='qa'):
    """One answer, several phrasings of the question, plus surface variants for robustness."""
    variants = 2 if len(questions) < 3 else 1
    for i, q in enumerate(questions):
        add(q, answer, topic, kind, system=True if i % 3 else 'any')
        for f in rng.sample(REPHRASE, variants):
            add(f(q), answer, topic, kind, system=rng.choice([True, 'any', False]))


# ---------------------------------------------------------------------------------------------
# 1. Hand-written seeds: concepts, API facts and workflows
# ---------------------------------------------------------------------------------------------

seed('connect', [
    "How do I connect to a Chemotion ELN with chemotion_api?",
    "How do I log in to Chemotion from Python?",
    "Show me how to open a connection to our ELN at https://eln.example.org.",
    "What's the recommended way to authenticate with chemotion_api?",
], f"""
Use an API token. Create it in the ELN under *Account & Profile* → *Account* → *Authentication Token*
(the ELN requires two-factor authentication for this), then:

{py(CONNECT)}

- `test_connection()` raises `ConnectionError` if the server is unreachable, and
  `UnsupportedServerVersion` if it is not an ELN v4 (for ELN 3.1.x use the `312.x` release line).
- `Instance(url, token='chemtoken_...')` does the same in one step, and `Instance` works as a context
  manager (`with Instance(url, token=...) as instance:`).
- `login(user, password)` still works but is deprecated and issues a `FutureWarning`.
""")

seed('connect', [
    "Can I still use login(user, password)?",
    "Is username/password login supported in chemotion_api?",
], f"""
Yes, but it is deprecated: `instance.login(user, password)` issues a `FutureWarning`. Prefer an API
token:

{py(CONNECT)}

A failed login raises `PermissionError`; an expired token raises
`chemotion_api.connection.TokenExpiredError` (a `PermissionError`) before the request is sent.
""")

seed('connect', [
    "Does chemotion_api work with Chemotion ELN 3.1?",
    "Our server runs ELN 3.1.2. Can I use this client?",
], """
Not this release line. It targets ELN **v4** only: v4 rewrote collections and sharing, renumbered the
share permission levels and removed `/syncCollections`. Connecting to an older server raises
`UnsupportedServerVersion` at `test_connection()`, before any credentials are sent. For ELN 3.1.x
install the `312.x` release line of chemotion_api.
""")

seed('connect', [
    "Write a script skeleton that connects and handles connection and login errors.",
    "How should I handle errors when connecting to Chemotion?",
], py("""
from chemotion_api import Instance

instance = Instance('https://eln.example.org')
try:
    instance.test_connection().login_token('chemtoken_...')
except ConnectionError:
    raise SystemExit('ELN not reachable')
except PermissionError:
    raise SystemExit('login failed')

me = instance.get_user()
print('logged in as', me)
""") + "\n\nNote: `login_token()` does not check the token itself; a bad token shows up on the first request.")

seed('collections', [
    "How do I find a collection by its path?",
    "Get the collection '/Projects/Team One'.",
    "How do I open a nested collection in chemotion_api?",
], f"""
Collections are addressed by unix-like paths of their labels:

{py('''
root = instance.get_root_collection()            # the 'All' collection tree
col = root.get_collection('/Projects/Team One')  # raises ModuleNotFoundError if missing
sub = col.get_collection('P 123')                # relative to col
''')}

- Paths starting with `/` are absolute; others are relative to the collection you call the method on.
- `.` and `..` are **not** supported.
- Pass `case_insensitive=True` to ignore case.
""")

seed('collections', [
    "How do I create a collection if it does not exist yet?",
    "Make sure the collection '/Projects/Team One/P 123' exists.",
    "get or create a collection",
], f"""
{py('''
root = instance.get_root_collection()
col = root.get_or_create_collection('/Projects/Team One/P 123')
''')}

`get_or_create_collection` saves right away. It creates only the **last** level, so the parent
collections (`/Projects/Team One`) must already exist.
""")

seed('collections', [
    "How do I list all my collections?",
    "Print every collection in the tree with its path.",
    "Iterate over all collections including the ones shared with me.",
], f"""
{py('''
root = instance.get_root_collection()
for c in root.walk():                  # every owned collection, parent before children
    print(c.label, c.get_path())

for c in root.sync_root.walk():        # collections shared with me
    print(c.get_path())

children = list(root.get_collection('/Projects').walk(include_self=True, max_depth=1))
''')}

`c.name`, `c.get_name()` and `c.get_label()` are read-only aliases of `c.label`.
""")

seed('collections', [
    "How do I add, move or delete a collection?",
    "Rename/move a collection to another parent.",
    "I called col.add_collection('X') but nothing appears in the ELN. Why?",
], f"""
Changes to the collection **tree** are local until you call `root.save()`:

{py('''
root = instance.get_root_collection()
col = root.get_collection('/Projects/Team One')
col.add_collection('P 124')
col.get_collection('P 122').move('/Done Projects')
root.save()                     # sends all tree changes and reloads
''')}

Only `get_or_create_collection` saves itself. Collections shared with you (`root.sync_root`) cannot be
moved, deleted or extended. `col.delete()` is also local until `root.save()`; ask the user before
deleting a collection.
""")

seed('collections', [
    "Can I create a sample directly in the root collection?",
    "root.new_sample_smiles raises AttributeError. Why?",
    "Why does the 'All' collection have no new_sample method?",
], f"""
No. Elements cannot be created in the root collection ('All'), so `root` has no `new_*` methods and
you get `AttributeError`. Create them in a real collection:

{py('''
root = instance.get_root_collection()
col = root.get_or_create_collection('My data')
s = col.new_sample_smiles('CCO')
s.save()
''')}
""")

seed('collections', [
    "How do I move a sample from one collection to another?",
    "Move elements between collections.",
    "How do I put the same sample in two collections?",
], f"""
These calls are sent immediately (no `root.save()` needed):

{py('''
root = instance.get_root_collection()
src = root.get_collection('/Projects/Team One')
dest = root.get_collection('/Done Projects')
sample = instance.get_sample(12)

src.move_elements(dest, sample)       # or sample.move_to(dest, src)
root.assign_elements(src, sample)     # now in both; the same element, not a copy
dest.remove_elements(sample)          # stays in 'All'; nothing is deleted
''')}

You cannot move from the root ('All') collection; use `assign_elements` there. Elements that are not
in the source collection are silently ignored.
""")

seed('listing', [
    "How do I list all samples in a collection?",
    "Iterate over the samples of a collection and print their labels.",
    "Get all reactions of a collection.",
], f"""
{py('''
col = instance.get_root_collection().get_collection('/Projects/Team One')
for s in col.get_samples(per_page=50):
    print(s.id, s.short_label, s.name)

for r in col.get_reactions():
    print(r.id, r.short_label, r.name)
''')}

Also: `get_wellplates()`, `get_research_plans()`, `get_screens()`, `get_cell_lines()`,
`get_device_descriptions()`, `get_sbmm_samples()`, `get_vessels()`, `get_generics_by_label(label)`,
`get_generics_by_name(name)`.

- The result is an `ElementSet`; iterating loads all pages. `len(es)` is the total on the server.
- The server allows at most 100 per page (`per_page`, default 10).
- `updated_from_date` / `updated_to_date` filter by last update.
""")

seed('listing', [
    "Why is listing fast but accessing properties slow?",
    "Each element in my loop triggers a request. Is that expected?",
    "What data is available on elements from a listing?",
], """
Yes, that is expected. Listing results are partial: `id`, `name`, `short_label` and `json_data` come
from the listing. The first access to `properties`, `segments`, `analyses`, `attachments` (or
`molecule`, `wells`, `workflow`) loads the full element, one request per element. So iterate over
labels cheaply, and expect one request per element once you touch its data. `es[i]` (indexing) loads
the element completely.
""")

seed('listing', [
    "My sample is in a reaction but get_samples() doesn't return it.",
    "Why are some samples missing from col.get_samples()?",
], f"""
That is server behaviour: `get_samples()` does not list samples that are only reactants or solvents of
a reaction. Reach them through the reaction:

{py('''
for r in col.get_reactions():
    for s in r.reactants + r.solvents:
        print(r.short_label, s.short_label)
''')}
""")

seed('listing', [
    "Can I use es[-1] to get the last sample of a listing?",
    "TypeError when I index an ElementSet with -1.",
], f"""
No. `ElementSet` cannot be indexed negatively (TypeError). Use the length instead:

{py('''
es = col.get_samples()
last = es[len(es) - 1]      # loads that page and the full element
first_five = es[:5]          # slicing returns a list
''')}

A listing from `get_elements_of_iri(...)` can only be iterated (no `len()` or index).
""")

seed('listing', [
    "How do I page through an ElementSet manually?",
    "Iterate page by page over the reactions.",
], f"""
{py('''
es = col.get_reactions(per_page=100)
print(es.max_page)
for page in es.iter_pages():
    for r in page:
        print(r.short_label)
es.page = 2            # IndexError if the page doesn't exist
''')}

`next_page()` / `prev_page()` move one page; `iter_elements(start_page=1)` yields elements.
""")

seed('load', [
    "How do I load a sample by its id?",
    "Get sample 12 from the ELN.",
    "Fetch reaction 5.",
], f"""
{py('''
sample = instance.get_sample(12)
reaction = instance.get_reaction(5)
wellplate = instance.get_wellplate(3)
plan = instance.get_research_plan(7)
''')}

Also `get_screen`, `get_cell_line`, `get_device_description`, `get_sbmm_sample`. A `401` in the
raised `RequestException` (`ChemotionRequestError`) means the element is not visible to you.
""")

seed('load', [
    "How do I find a sample by its short label like 'API-12'?",
    "Look up reaction 'API-R4' by short label.",
], f"""
{py('''
s = instance.find_sample_by_short_label('API-12')     # None if not found
r = instance.find_reaction_by_short_label('API-R4')
''')}
""")

seed('load', [
    "How do I load a generic element?",
    "Get the 'Device' generic element with id 3.",
], f"""
{py('''
g = instance.get_generic_by_label('Device', 3)     # by the label shown in the ELN
g = instance.get_generic_by_name('dev', 3)         # or by the template's internal name
''')}

`ValueError` for an unknown or built-in type, or an id that belongs to another type.
""")

seed('save', [
    "I changed a property but the ELN still shows the old value.",
    "Why are my changes not visible in Chemotion?",
    "When are changes sent to the server?",
], f"""
Objects are edited locally and only reach the server on `save()`:

{py('''
s = instance.get_sample(12)
s.properties['description'] = 'Stored at 4 °C'
s.save()
''')}

A new element has a UUID string as `id` until it is saved; afterwards `id` is an int. Use
`save(load_after_save=True)` when you need to read back new attachments or ids of new sub-objects.
`element.load()` reloads from the server and drops local changes.

Exception: most v4 additions act **immediately** without `save()`: moving, sharing, deleting,
splitting, comments, references, chemicals, measurements, vessels, exports and admin calls.
""")

seed('save', [
    "How can I show the user the element I just created?",
    "Get a link to a sample in the web UI.",
], f"""
{py('''
s.save()
print(s.url())     # link to the element in the ELN
s.open()           # opens it in the browser (user must be logged in there)
''')}

Both raise `ValueError` for an unsaved element. Put the link in your answer so the user can check.
""")

seed('sample', [
    "How do I create a sample from a SMILES string?",
    "Create an ethanol sample.",
    "Make a new sample of CCO in my collection.",
], f"""
{py('''
col = instance.get_root_collection().get_or_create_collection('My data')
s = col.new_sample_smiles('CCO')       # molecule looked up on the server
s.properties['external_label'] = 'Ethanol'
s.save()
print(s.id, s.short_label)
''')}

The molecule's density is copied to the sample if the sample has neither a density nor a molarity
yet. Elements and ions need brackets: `'[Mg]'`, not `'Mg'` (ValueError).
""")

seed('sample', [
    "new_sample_smiles('Mg') raises ValueError.",
    "How do I create a sample of magnesium metal?",
    "Why can't the server resolve the SMILES 'Cu'?",
], f"""
In SMILES, element symbols outside the organic subset need brackets. `'Mg'` is not valid, `'[Mg]'` is:

{py('''
mg = col.new_sample_smiles('[Mg]')
cu = col.new_sample_smiles('[Cu]')
mg.save(); cu.save()
''')}
""")

seed('sample', [
    "How do I create a solvent sample?",
    "Add a THF sample.",
    "new_solvent('THF') raises KeyError.",
], f"""
Use the exact name from the ELN's solvent list:

{py('''
names = instance.get_solvent_list()
print([n for n in names if 'THF' in n])     # ['Tetrahydrofuran (THF)']
thf = col.new_solvent('Tetrahydrofuran (THF)')
thf.save()
''')}

An unknown name raises `KeyError`, and the message suggests similar names. Other examples:
`'Methylene chloride (DCM)'`, `'Dimethyl sulfoxide (DMSO)'`, `'CDCl3'`, `'Toluene'`, `'Water'`.
""")

seed('sample', [
    "How do I set the amount of a sample?",
    "Set 2.5 g on a sample.",
    "What's the right way to set a sample amount?",
], f"""
{py('''
from chemotion_api.elements.utils import QuantityUnit

s.set_amount(2.5, QuantityUnit.Gram)    # value first, then unit
s.save()
print(s.gram, s.mol, s.liter)            # converted amounts
''')}

- Units: `QuantityUnit.Gram` ('g'), `Mole` ('mol'), `Liter` ('l'), `Equivalent` (relative to the
  reaction's reference; starting materials and reactants only).
- `s.allowed_quantity_units()` lists what is valid for this sample.
- `gram`/`mol`/`liter` are `None` without an amount or if not convertible (mol needs a molecular
  weight, liter a density or molarity).
- `set_amount` writes `real_amount` for reaction products and `target_amount` otherwise.
""")

seed('sample', [
    "Can I set an amount in mg or mmol?",
    "set_amount(250, 'mg') raises ValueError.",
    "Which unit strings does set_amount accept?",
], f"""
Only `'g'`, `'mol'`, `'l'` and `'Equivalent'` (case insensitive) or the `QuantityUnit` members.
`'mg'`, `'mmol'`, `'gram'`, `'eq'` and `'ppm'` raise `ValueError`. Convert yourself:

{py('''
from chemotion_api.elements.utils import QuantityUnit

s.set_amount(250 / 1000, QuantityUnit.Gram)     # 250 mg
s.set_amount(1.2 / 1000, QuantityUnit.Mole)     # 1.2 mmol
s.set_amount(5 / 1000, QuantityUnit.Liter)      # 5 ml
s.save()
''')}
""")

seed('sample', [
    "How do I set the purity of a sample to 98 %?",
    "Purity 98% on sample 12.",
    "I set purity = 98 and got a validation error.",
], f"""
Purity is a **fraction** (0 < purity <= 1), not percent:

{py('''
s = instance.get_sample(12)
s.properties['purity'] = 0.98
s.save()
''')}
""")

seed('sample', [
    "What properties does a sample have?",
    "List the property keys of a Chemotion sample.",
], """
`sample.properties[...]` keys:

- `name`, `short_label`: read-only
- `external_label`, `description`, `location`, `reaction_description`: str
- `target_amount`, `real_amount`: `{'value': float, 'unit': 'g'|'l'|'mol'}` (prefer `set_amount`)
- `molarity`: `{'value': float, 'unit': 'M'}`
- `purity`: float, 0 < purity <= 1
- `density`: float in g/ml
- `boiling_point_lowerbound/upperbound`, `melting_point_lowerbound/upperbound`: int
- `stereo`: `{'abs': ..., 'rel': ...}`
- `solvent`: `SolventList` (`.add_new_name(name)`, `.add_new_smiles(smiles)`)
- `is_top_secret`, `is_restricted`, `decoupled`, `inventory_sample`: bool
- `user_labels`: list of label ids
- reaction-link fields `reference`, `equivalent`, `coefficient`, `position`, `waste`, `show_label`,
  `gas_type`, `gas_phase_data`: saved only by `reaction.save()`

The molecule is `sample.molecule` (dict-like, read-only): `molecular_weight`, `sum_formular`,
`cano_smiles`, `inchikey`, `iupac_name`, ...
""")

seed('sample', [
    "How do I read the molecular weight of a sample?",
    "Get the sum formula and InChIKey of sample 12.",
], f"""
{py('''
s = instance.get_sample(12)
print(s.molecule['molecular_weight'])
print(s.molecule.sum_formular, s.molecule.inchikey, s.molecule.cano_smiles)
''')}

`sample.molecule` is a dict-like `Molecule`; keys are also readable as attributes. Note the key is
`sum_formular` (with an r), as in the ELN.
""")

seed('sample', [
    "How do I set the solvent of a sample (e.g. dissolved in CDCl3)?",
    "Add a solvent to a sample's solvent list.",
], f"""
{py('''
s = instance.get_sample(12)
s.properties['solvent'].add_new_name('CDCl3')       # exact name from instance.get_solvent_list()
s.properties['molarity'] = {'value': 0.1, 'unit': 'M'}
s.save()
''')}

`add_new_smiles(smiles)` adds a solvent by SMILES instead.
""")

seed('sample', [
    "Can I change the short label of a sample?",
    "Setting sample.properties['short_label'] raises ValueError.",
], """
No. The ELN assigns the short label and ignores changes to it, so the client refuses with `ValueError`
instead of failing silently. To give a sample your own label use `properties['external_label']`, or
change future labels with `instance.set_short_label_counter('samples', 100)`.
""")

seed('sample', [
    "What's the difference between sample.split() and col.split_samples()?",
    "How do I split a sample?",
], f"""
{py('''
subs = col.split_samples(s1, s2)   # immediate; linked subsamples on the server ('<label>-<n>')

piece = s1.split()                 # saves s1 first, returns an UNSAVED new sample
piece.save()                       # unlinked copy, unless saved inside a reaction/wellplate
dup = s1.copy()                    # saves s1, returns an unsaved copy
''')}

Use `col.split_samples(...)` when you want real, linked subsamples like the UI makes.
""")

seed('sample', [
    "How do I create a sample from a molfile?",
    "I have a molfile string. Create a sample from it.",
], f"""
{py('''
with open('compound.mol') as f:
    molfile = f.read()
s = col.new_sample_molfile(molfile)
s.save()

mol = instance.molecule().create_molecule_by_molfile(molfile)   # just the molecule
''')}

An unreadable molfile raises `ValueError` (the server would otherwise return its DUMMY molecule).
""")

seed('sample', [
    "How do I look up the CAS number of a molecule?",
    "Find the molecule for CAS 64-17-5.",
], f"""
{py('''
mm = instance.molecule()
cas_list = mm.load_cas(s.molecule['inchikey'])   # CAS numbers known for this InChIKey
info = mm.lookup_cas('64-17-5')
''')}
""")

seed('sample', [
    "How do I add a name to a molecule and show it on the sample?",
    "Give the molecule of a sample a custom name.",
], f"""
{py('''
mm = instance.molecule()
name = mm.add_name(sample.molecule['id'], 'Spirit')
sample.molecule_name_id = name.id
sample.save()
print([n.name for n in mm.get_names(sample.molecule['id'])])
''')}
""")

seed('reaction', [
    "How do I create a reaction with starting materials, reactants and products?",
    "Build a reaction from existing samples.",
    "Add samples to a reaction.",
], f"""
{py('''
from chemotion_api.elements.utils import QuantityUnit

r = col.new_reaction()
r.name = 'Reduction of benzaldehyde'
r.starting_materials.append(instance.get_sample(12))   # adds a SPLIT (saves the original first)
r.reactants.append(instance.get_sample(13))            # split
r.products.append(instance.get_sample(14))             # adds a COPY
r.solvents.append(col.new_solvent('Methanol'))         # solvents are added as they are

r.reference_sample = r.starting_materials[0]
r.reactants[0].set_amount(1.5, QuantityUnit.Equivalent)
r.save()                                               # recomputes equivalents and yields
''')}

The material lists are also `r.properties['starting_materials']`, `['reactants']`, `['products']`,
`['solvents']`, `['purification_solvents']`.
""")

seed('reaction', [
    "Does appending a sample to a reaction create a new sample?",
    "Why do I get new sample ids after adding samples to a reaction?",
    "How do I add a sample to a reaction without splitting it?",
], f"""
Yes: `starting_materials.append` and `reactants.append` add a **split** (and save the source sample
first), `products.append` adds a **copy**, `solvents.append` adds the sample as is.

To add the sample itself, without a split and without saving it first:

{py('''
r.starting_materials.append_no_split(sample)
r.save()
''')}

Both set the reaction, role and position and keep or initialize the amount.
""")

seed('reaction', [
    "ValueError when I append the same sample twice to a reaction.",
    "How do I move a sample from reactants to starting materials?",
], f"""
A sample can be in a reaction only once, in any role (same object or same id). The ELN keeps one link
per sample and would drop the second entry, so the client raises `ValueError`. Remove it first:

{py('''
s = r.reactants[0]
r.reactants.remove(s)
r.starting_materials.append_no_split(s)
r.save()
''')}

A sample that belongs to *another* reaction is accepted; on save the ELN gives this reaction a split
with a new id.
""")

seed('reaction', [
    "How do I set equivalents in a reaction?",
    "Set 1.2 equivalents of the reactant.",
], f"""
Equivalents are relative to the reference material:

{py('''
from chemotion_api.elements.utils import QuantityUnit

r = instance.get_reaction(5)
r.reference_sample = r.starting_materials[0]
r.starting_materials[0].set_amount(0.01, QuantityUnit.Mole)   # reference needs an amount
r.reactants[0].set_amount(1.2, QuantityUnit.Equivalent)
r.save()
''')}

Equivalents are plain factors (1.2, not 120 %). `ValueError` if the reference has no amount that
converts to mol.
""")

seed('reaction', [
    "How do I record the yield of a reaction product?",
    "Set the obtained amount of the product.",
], f"""
Set the product's real amount; the yield follows from the reference material on save:

{py('''
from chemotion_api.elements.utils import QuantityUnit

r = instance.get_reaction(5)
r.products[0].set_amount(0.0015, QuantityUnit.Mole)   # or QuantityUnit.Gram
r.save()
''')}

For products `set_amount` writes `real_amount`. Products accept g and mol (and l with a density or
molarity), not Equivalent.
""")

seed('reaction', [
    "How do I set the status of a reaction?",
    "Mark reaction 5 as successful.",
    "What reaction status values exist?",
], f"""
{py('''
r = instance.get_reaction(5)
r.properties['status'] = 'Successful'
r.save()
''')}

Allowed: `''`, `'Planned'`, `'Running'`, `'Done'`, `'Analyses Pending'`, `'Successful'`,
`'Not Successful'`. Unknown values are ignored on save, so check the spelling.
""")

seed('reaction', [
    "How do I add a temperature profile to a reaction?",
    "Set the reaction temperature to 80 °C for 2 hours.",
], f"""
{py('''
t = r.properties['temperature']
t.add_time_point(0, 0, 0, 80)      # hour, minute, second, value
t.add_time_point(2, 0, 0, 80)
t['valueUnit'] = '°C'              # '°C' | '°F' | 'K'
r.save()
''')}

The Temperature dict also has `data` (`[{{'time': 'hh:mm:ss', 'value': '80'}}]`) and `userText`.
""")

seed('reaction', [
    "How do I set the purification methods of a reaction?",
    "Which purification values are allowed?",
], f"""
{py('''
r.properties['purification'] = ['Flash-Chromatography', 'TLC']
r.save()
''')}

Allowed: Flash-Chromatography, TLC, HPLC, Extraction, Distillation, Dialysis, Filtration, Sublimation,
Crystallisation, Recrystallisation, Precipitation. Unknown values are dropped silently.
""")

seed('reaction', [
    "How do I write the description or observation of a reaction?",
    "Set rich text on a reaction.",
    "How do I read the reaction description as plain text?",
], f"""
They are Quill deltas. Assign a plain string (converted for you) or a well-formed delta:

{py('''
from chemotion_api import quill_to_text

r.properties['description'] = 'Dissolve the aldehyde in MeOH, add NaBH4 at 0 °C.'
r.properties['observation'] = 'Turned yellow after 5 min.'
r.save()
print(quill_to_text(r.properties['description']))
''')}

Anything that is neither a string nor a delta raises `ValueError`. `text_to_quill()` builds a delta.
""")

seed('reaction', [
    "What other reaction properties can I set?",
    "List the property keys of a reaction.",
], """
`reaction.properties[...]`:

- `starting_materials`, `reactants`, `products`, `solvents`, `purification_solvents`: MaterialList
- `name`, `conditions`, `duration`: str
- `description`, `observation`: plain str or Quill delta
- `status`: '', Planned, Running, Done, Analyses Pending, Successful, Not Successful
- `purification`: list of str
- `temperature`: Temperature (`add_time_point`)
- `timestamp_start`, `timestamp_stop`: datetime (duration is computed on save)
- `vessel_size`: `{'amount': 50, 'unit': 'ml'}` ('l' or 'ml')
- `dangerous_products`: list
- `gaseous`: bool (same as `gas_schema`)
- `rxno`, `rinchi_long_key`, `rinchi_short_key`, `rinchi_web_key`: read-only
""")

seed('reaction', [
    "How do I change the coefficient of a starting material?",
    "sample.save() raises ValueError after I set properties['coefficient'].",
    "How do I mark a material as waste?",
], f"""
A sample's place in a reaction (`reference`, `equivalent`, `coefficient`, `position`, `waste`,
`show_label`, gas fields) is stored with the **reaction**. Change it on the reaction's own material and
save the reaction:

{py('''
r = instance.get_reaction(5)
r.starting_materials[0].properties['coefficient'] = 2
r.products[1].properties['waste'] = True
r.save()
''')}

On a sample loaded by itself, setting such a field raises `ValueError`, and `sample.save()` refuses
while such a change is pending, because the ELN would drop it silently.
""")

seed('reaction', [
    "How do I set up a gas-phase reaction?",
    "Record a gas product with ppm concentration.",
], f"""
{py('''
from chemotion_api.elements.utils import GasType

r.gas_schema = True                                    # first
r.starting_materials[0].set_gas_type(GasType.FEEDSTOCK)
r.products[0].set_gas_type(GasType.GAS)
gp = r.products[0].properties['gas_phase_data']
gp.ppm = 9222
gp.time_in_h = 12.5
gp.temperature_in_k = 325.65
r.save()
''')}

- FEEDSTOCK and CATALYST only for starting materials/reactants (CATALYST needs a feedstock first), GAS
  only for products. At most one feedstock and one catalyst.
- Allowed units change with the gas type: re-read `allowed_quantity_units()`. A FEEDSTOCK takes l, mol,
  Equivalent; a GAS product takes g only (plus l with density/molarity).
- A sample outside a reaction cannot have a gas type. There is no `QuantityUnit.Ppm`.
""")

seed('variations', [
    "How do I add a variation to a reaction?",
    "Record a second run with different conditions as a reaction variation.",
], f"""
{py('''
from chemotion_api.elements.utils import QuantityUnit

r = instance.get_reaction(5)
v = r.variations.add_new()                     # starts from the reaction's current amounts
v.properties['temperature']['value'] = 60      # unit '°C'
v.properties['duration']['value'] = 7200       # unit 'Second(s)'
v.notes = 'run 2'
v.starting_materials[0].set_quantity(2, QuantityUnit.Gram)
v.reactants[0].set_equivalent(1.5)             # not for the reference material
v.products[0].set_yield(85)                    # percent
v.solvents[0].set_quantity(0.01, QuantityUnit.Liter)
r.save()
''')}

Remove one with `r.variations.remove(v); r.save()`. Link a saved analysis with
`v.link_analyses(r.analyses.by_name('HPLC 2'))`. Mixtures cannot be quantified in variations
(NotImplementedError).
""")

seed('variations', [
    "Are yields in variations a fraction or percent?",
    "What units do variation values use?",
], """
- `set_yield(85)` in a variation is **percent**.
- Sample purity is a **fraction** (0.98).
- Equivalents are plain factors (1.5).
- Variation temperature is `{'value', 'unit': '°C'}`, duration `{'value', 'unit': 'Second(s)'}`.
- Solvent quantities in variations are always liters.
""")

seed('research_plan', [
    "How do I create a research plan with text and a table?",
    "Write a research plan with a heading, a table and an image.",
], f"""
{py('''
rp = col.new_research_plan()
rp.name = 'Screening plan'
rt = rp.add_richtext()
rt.add_text('Goal\\n', header=rt.HeaderType.H1).add_text('Find the best base. ', bold=True)
t = rp.add_table()
a, b = t.add_columns('Base', 'Yield')       # returns column ids ('a', 'b', ...)
t.add_row('K2CO3', **{b: 85})
t.add_row('Cs2CO3', **{b: 91})
rp.add_image('./setup.png')                 # uploaded on save
rp.save()
''')}

Lists and headers must end with `'\\n'`. `rp.body` holds the entries (RichText / Table objects, and
Sample/Reaction objects for embedded elements).
""")

seed('wellplate', [
    "How do I put samples into a wellplate?",
    "Fill well A1 of a wellplate.",
], f"""
{py('''
wp = col.new_wellplate()
wp.properties['name'] = 'Plate 1'
wp.wells[0]['A'] = instance.get_sample(12)   # column 0-11, row 'A'-'H'; stores a split
wp.save()                                    # Wellplate.save() takes no argument
''')}

Caution: parsing a wellplate currently splits (and saves) every well sample, so avoid loading and
re-saving wellplates in bulk.
""")

seed('wellplate', [
    "How do I import well data from a spreadsheet?",
    "Download the wellplate template and import it back.",
], f"""
{py('''
wp = instance.get_wellplate(3)
wp.download_template('plate.xlsx')
# ... fill the file ...
wp.import_spreadsheet('plate.xlsx')
wp.export_samples_excel('plate_samples.xlsx')
''')}
""")

seed('screen', [
    "How do I create a screen and link wellplates to it?",
    "Add a wellplate to a screen.",
], f"""
Links are id lists; a save sends them as the new state:

{py('''
plate = col.new_wellplate()
plate.save()

screen = col.new_screen()
screen.properties['name'] = 'Kinase panel'
screen.properties['conditions'] = '37 °C, 24 h'
screen.wellplate_ids.append(plate.id)
screen.save()

screen = instance.get_screen(screen.id)
print([w.properties['name'] for w in screen.wellplates])
''')}

`research_plan_ids` works the same. An empty list removes every link. Properties: `name`,
`collaborator`, `requirements`, `conditions`, `result`, `description` (rich text).
""")

seed('cell_line', [
    "How do I create a cell line sample?",
    "Create a HeLa cell line from ATCC.",
], f"""
{py('''
line = col.new_cell_line('HeLa', 'ATCC')       # material name and source
line.properties['amount'] = 1_000_000
line.properties['unit'] = 'cells'
line.properties['passage'] = 3
line.material['organism'] = 'Homo sapiens'
line.save()
''')}

`amount`, `unit` and `passage` must be set before saving. `line.material` is the shared cell-line
material: a change shows on every sample of that cell line, and editing a material someone else created
raises `PermissionError`. Changing `name` or `source` links the sample to another material.
""")

seed('sbmm', [
    "How do I create a protein sample (SBMM)?",
    "Create a sequence-based macromolecule sample from UniProt P69905.",
], f"""
{py('''
s = col.new_sbmm_sample('P69905')          # UniProt accession
s.properties['purity'] = 0.95
s.properties['concentration'] = {'value': 2.0, 'unit': 'g/L'}
s.save()
print(s.macromolecule['short_name'])        # read-only
''')}

Proteins not in UniProt or modified variants must be created in the web UI.
""")

seed('device_description', [
    "How do I create a device description?",
    "Record our Bruker NMR as a device description.",
], f"""
{py('''
dev = col.new_device_description()
dev.properties['name'] = 'NMR 400'
dev.properties['vendor_company_name'] = 'Bruker'
dev.properties['general_tags'] = ['nmr']
dev.save()
''')}

If the ELN refuses, `save()` raises `ValueError` with its reasons. `dev.ontology_terms()` lists the
ontology annotations.
""")

seed('vessels', [
    "How do I create vessels?",
    "Make a vessel template 'Flask 250 ml' and 10 vessels of it.",
], f"""
{py('''
flask = instance.new_vessel_template('Flask 250 ml', vessel_type='round bottom flask',
                                     material_type='glass', volume_amount=250, volume_unit='ml').save()
v = col.new_vessel(flask, weight_amount=120.5, weight_unit='g')
rack = col.new_vessels(flask, 10, base_name='rack')
''')}

Vessels and templates are saved immediately and have UUID ids. Templates are shared by everyone.
""")

seed('generic', [
    "How do I fill fields of a generic (LabIMotion) element?",
    "Set the serial number on a 'Device' generic element.",
], f"""
Properties are addressed by **layer label** and **field label**, as shown in the ELN:

{py('''
g = instance.get_generic_by_label('Device', 3)
g.properties['General']['Serial number'] = 'X-12'
g.save()
print(g.label, g.klass_name, g.klass_version)     # e.g. 'Device', 'dev', '1.0'
''')}

Labels are case-sensitive. Unknown layer/field names raise `ValueError` on save. A layer used twice
gets a suffix from its key (`three.1` → `properties['Nr 3.1']`).
""")

seed('generic', [
    "How do I create a new generic element?",
    "Create a 'Device' element in my collection.",
], f"""
{py('''
g = col.new_generic_by_label('Device')     # or col.new_generic('dev') by internal name
g.properties['General']['Serial number'] = 'X-12'
g.save()
print(g.short_label)                      # set by the server: '<initials>-<prefix><n>'
''')}
""")

seed('generic', [
    "How do I advance a generic element's workflow?",
    "Add the next workflow layer to a generic element.",
], f"""
{py('''
g = instance.get_generic_by_label('Device', 3)
for o in g.wf_next_options():
    print(o['wf_idx'], o['layer_label'])
opt = next(o for o in g.wf_next_options() if o['wf_idx'] == 0 and o['layer_label'] == 'Calibration')
key = g.wf_next(**opt)                    # key of the new layer in g.properties
g.properties[key]['Result'] = 'ok'
g.save()
''')}

`g.wf_layer(0, 'Calibration')` returns the same layer by workflow and label; `g.wf_workflows()` lists
each workflow's layers; `g.wf_add_layer('Calibration')` adds a template layer directly.
""")

seed('generic', [
    "How do I create a new LabIMotion element template?",
    "As admin, define a generic element type 'Micro Biology' with fields.",
], f"""
{py('''
from chemotion_api.labImotion.items.fields import FieldType
from chemotion_api.labImotion.items.options import SaveActionType

gm = instance.generic_manager()
k = gm.create_new_element('Micro Biology', 'bug', description='Strains', prefix='MB')
general = k.properties.add_new_layer('General')
general.add_field(FieldType.TEXT, 'Strain')
general.add_field(FieldType.SELECT, 'Growth medium', options=['LB', 'TB'])
k.properties.add_new_layer('Cultivation').add_field(FieldType.INTEGER, 'Temperature (°C)')
k.save(SaveActionType.MINOR)      # release; SaveActionType.DRAFT only stores

elem = col.new_generic_by_label('Micro Biology')
elem.properties['General']['Strain'] = 'E. coli K12'
elem.save()
''')}

`create_new_element` releases and activates an empty v0.1. Keys are generated from labels unless
given. This needs generic-elements admin rights.
""")

seed('generic', [
    "How do I link a template field to an ontology term?",
    "Attach CHMO:0000593 to a field.",
], f"""
{py('''
gm = instance.generic_manager()
terms = gm.search_ontology_terms('nmr')
k = gm.get_element('dev', version='1.0')
field = k.properties.add_new_layer('Method').add_field(FieldType.TEXT, 'NMR method', ontology='CHMO:0000593')
# or later: field.ontology = 'CHMO:0000593'; field.ontology = None removes it
''')}

On elements: `g.field(layer, field).ontology`. Terms come from the TIB Terminology Service.
""")

seed('segments', [
    "How do I fill a segment (extra tab) on a sample?",
    "Set the 'Electrode type' field in the 'Electrochemistry' segment.",
    "Write values into a LabIMotion segment.",
], f"""
{py('''
s = instance.get_sample(1)
print(s.segments.available())                   # segments for this element type
cell = s.segments.get('Electrochemistry')['Cell']   # .get() ADDS a missing segment
cell['Electrode type'] = 'disk'                 # select: key or label (stored as key)
cell['Temperature'] = {'value': 25, 'unit': 'C'}    # system-defined; bare number = default unit
cell['Cycles'] = 3                              # integer
s.save()                                        # invalid changed values raise ValueError
''')}

`s.segments['Electrochemistry']` is `None` if the segment was not added yet.
""")

seed('segments', [
    "How do I find out which values a segment field accepts?",
    "What options does a select field have?",
], f"""
{py('''
s.segments.field_type('Electrochemistry', 'Cell', 'Electrode type')   # 'select'
s.segments.options('Electrochemistry', 'Cell', 'Electrode type')      # [{'key', 'label'}]
s.segments.units('Electrochemistry', 'Cell', 'Temperature')           # ['C', 'F', 'K']
f = s.segments.field('Electrochemistry', 'Cell', 'Temperature')
print(f.type, f.default_unit, f.ontology)
''')}
""")

seed('segments', [
    "s.segments['Electrochemistry'] is None. Why?",
    "TypeError: 'NoneType' object is not subscriptable when writing a segment.",
], f"""
The element does not have that segment yet; indexing returns `None`. Use `.get()`, which adds it with
the template defaults:

{py('''
seg = s.segments.get('Electrochemistry')
seg['Cell']['Cycles'] = 3
s.save()
''')}
""")

seed('analyses', [
    "How do I upload an NMR measurement to a sample?",
    "Add an analysis with a data file.",
    "Attach a measurement zip as a dataset.",
], f"""
{py('''
s = instance.get_sample(12)
ana = s.analyses.add_analyses('NMR')
ana['description'] = '1H NMR in CDCl3'
ds = ana.add_dataset('./nmr.zip')      # uploaded on save
s.save()
''')}

The dataset's metadata is filled by a matching converter profile. `el.save_analyses()` saves only the
analyses, not the element.
""")

seed('analyses', [
    "How do I download all analysis files of a sample?",
    "Iterate over analyses and datasets.",
    "ana['datasets'] raises KeyError.",
], f"""
Datasets are an **attribute**, not a dict key:

{py('''
for ana in s.analyses:
    print(ana.name, ana['kind'] if 'kind' in ana else '')
    for ds in ana.datasets:
        print('  ', ds.name, ds.id)          # name/id are attributes; the dict is metadata
        for att in ds.attachments or []:
            att.save_file('./out')
''')}

`s.analyses.by_name('NMR')` / `by_id(id)` raise `StopIteration` if missing.
`ds.write_zip()` and `ds.write_data_set_xlsx()` export a dataset.
""")

seed('analyses', [
    "How do I delete an analysis?",
    "Remove the HPLC analysis from reaction 5.",
], f"""
This is immediate and the files cannot be restored, so confirm with the user first:

{py('''
r = instance.get_reaction(5)
ana = r.analyses.by_name('HPLC')
r.delete_analysis(ana)
''')}
""")

seed('attachments', [
    "How do I attach a PDF to a sample and download it again?",
    "Upload a file attachment to a research plan.",
    "load_attachment can't find my newly added file.",
], f"""
{py('''
s.attachments.add_file('./report.pdf')
s.save(load_after_save=True)              # reload, otherwise the new file can't be found
att = s.attachments.load_attachment(filename='report.pdf')   # basename, not the path
att.save_file('./out')
''')}

`s.attachments` can be `None` for elements without an attachment container (some generic ones).
""")

seed('search', [
    "How do I search samples by name or CAS?",
    "Find all samples named Ethanol.",
], f"""
{py('''
from chemotion_api.search.utils import EnumMatch, EnumConnector

hits = (instance.search_sample()
        .add_search_condition(EnumMatch.LIKE, EnumConnector.OR, name='Ethanol', cas='64-17-5')
        .find_max(20)
        .request())
for s in hits:
    print(s.short_label, s.name)
''')}

Sample fields: `name`, `short_label`, `external_label`, `inventory_label`, `cas`, `private_note`.
`EnumMatch`: LIKE, NOT_LIKE (case insensitive), LESS_THAN, BIGGER_THAN, EXACT. The connector links a
condition to the ones before it. Default max 15 results; `in_collection(id)` restricts the search.
""")

seed('search', [
    "How do I find reactions above 30 °C?",
    "Search reactions by temperature or status.",
], f"""
{py('''
from chemotion_api.search.utils import EnumMatch, EnumConnector

hot = (instance.search_reaction()
       .add_search_condition(EnumMatch.BIGGER_THAN, EnumConnector.AND, temperature_in_c=30)
       .add_search_condition(EnumMatch.EXACT, EnumConnector.AND, status='Successful')
       .request())
''')}

Reaction fields: `name`, `short_label`, `status`, `conditions`, `reaction_type`, `temperature_in_c`,
`duration_in_sec`, `private_note`.
""")

seed('search', [
    "How do I do a substructure search?",
    "Find everything containing a phenol substructure.",
    "Similarity search for ethanol.",
], f"""
{py('''
res = instance.search_structure().substructure('c1ccccc1O').find_max(50).request()
for s in res.samples:
    print(s.short_label)
print(res.total('reaction'))

similar = instance.search_structure().similar('CCO', threshold=0.8).request()
''')}

SMILES, molfiles and molecules are accepted. `in_collection(id)` restricts it.
""")

seed('sharing', [
    "How do I share a collection with a colleague?",
    "Share a collection read-only with Smith.",
], f"""
{py('''
from chemotion_api.collection import CollectionSharePermission as P

col = instance.get_root_collection().get_collection('/Projects/Team One')
users = instance.find_user_by_name('Smith')        # top 3 matches: check before sharing
col.share(P.ReadElements, users[0], detail_level=10)
print(col.get_shares())
''')}

- Sent immediately.
- `detail_level` (0-10) is required: 10 discloses every field and lets the recipient export; lower
  levels withhold fields.
- Levels: `ReadElements`, `EditElements`, `AddElements`, `RemoveElements`, `ManageShares`,
  `PassOwnership`. v4 renumbered them, so always use the names, never numbers.
- `col.unshare(user)` revokes; it refuses an empty user list (use `all=True` deliberately).
""")

seed('sharing', [
    "How do I share with a group?",
    "Create a group and share a collection with it.",
], f"""
{py('''
from chemotion_api.collection import CollectionSharePermission

me = instance.get_user()
grp = me.create_group('Test', 'Group', 'STG')
grp.add_users(*instance.find_user_by_name('Tom'), *instance.find_user_by_name('Jerry'))
col.share(CollectionSharePermission.EditElements, grp, detail_level=5)
''')}
""")

seed('sharing', [
    "How do I accept ownership of a collection someone passed to me?",
], f"""
{py('''
root = instance.get_root_collection()
for shared in root.sync_root.walk():
    print(shared.get_path())
shared = root.sync_root.get_collection('/Handover')
shared.take_ownership()
''')}

This works only for a share with `PassOwnership` permission.
""")

seed('restricted', [
    "Some properties read as '***'. What does that mean?",
    "save() raises PermissionError on a shared sample.",
    "How do I detect withheld fields?",
], f"""
The collection was shared with you below detail level 10, so the server withheld some fields:

{py('''
from chemotion_api.utils.withheld import WITHHELD

for s in shared_col.get_samples():
    if s.is_restricted and s.properties['description'] is WITHHELD:
        print(s.id, 'description withheld')
''')}

- Compare by **identity** (`is WITHHELD`): it is also a `str` equal to `'***'`.
- Using it as a number raises `WithheldValueError` (a `PermissionError`).
- `save()` refuses restricted elements with `PermissionError`, since it would overwrite real values
  with placeholders.
""")

seed('delete', [
    "How do I delete a sample?",
    "Delete reaction 5 and sample 12.",
], f"""
Deleting cannot be undone. Make sure the user really wants this, then:

{py('''
s = instance.get_sample(12)
gone = s.delete()                       # True once the record is really gone
kept = col.delete_elements(instance.get_reaction(5), s)   # several at once
print(kept)                             # the elements the server kept
''')}

ELN v4 withdraws the elements from your collections and destroys only those left in none, so an
element still bound to a reaction or shared elsewhere survives. There is no "delete all".
""")

seed('notes', [
    "How do I add a comment to a sample?",
    "Write a private note on a reaction.",
    "Read the version history of an element.",
], f"""
These act immediately:

{py('''
el.add_comment('Check the purity', section='properties')
print(el.comments())
el.set_private_note('only visible to me')
print(el.private_note())
for v in el.versions():
    print(v.time, v.user, v.changes)
# v.revert() restores that version (fields=... limits it)
''')}
""")

seed('literature', [
    "How do I add a literature reference (DOI) to a reaction?",
    "Cite a paper on an element.",
], f"""
{py('''
r.add_reference(doi='10.1021/acs.jchemed.0c00101')     # immediate
for ref in r.references():
    print(ref)
meta = instance.doi_metadata('10.1021/acs.jchemed.0c00101')
''')}

Also `url=`, `title=`, `isbn=`, `bibtex=`; `litype='citedOwn'` by default. `col.references()` lists all
references of a collection.
""")

seed('labels', [
    "How do I put a user label on a sample?",
    "Show the label titles of a sample.",
], f"""
{py('''
from chemotion_api.user import UserLabel

for label in instance.get_user_labels():
    print(label.id, label.title)
print(', '.join(l.display_title for l in s.user_labels_resolved))

label = instance.save_user_label(UserLabel(title='Needs review', color='#d9534f', access_level=0))
s.properties['user_labels'] = list(s.properties['user_labels'] or []) + [label.id]
s.save()
''')}

`properties['user_labels']` holds ids only. `access_level` 0 = private, 1 or 2 = shared.
""")

seed('export', [
    "How do I export a collection as a zip and import it elsewhere?",
    "Back up a collection.",
], f"""
{py('''
col.export_zip('project.zip')                       # waits for the background job
new_collections = instance.import_zip('project.zip')
''')}

This is the ELN's native ZIP (not `.eln`). Both run as server jobs and poll until done (`timeout=`).
There is no job id; re-running starts a second job.
""")

seed('export', [
    "How do I import samples from an SDF file?",
    "Bulk import samples from Excel.",
], f"""
{py('''
result = col.import_samples('samples.sdf')     # .sdf .mol .csv .xlsx
assert result.ok, result.message
''')}

`as_chemicals=True` imports them as chemicals. Ask the user before large imports.
""")

seed('export', [
    "How do I export samples and reactions to Excel?",
    "Export reaction SMILES to CSV.",
], f"""
{py('''
col.export_elements('table.xlsx', s1, r1)              # or file_format='sdf'
col.export_reaction_smiles('rxn.csv', r1, notation='SM>R>P')
r1.export_samples_excel('reaction_samples.xlsx')
''')}
""")

seed('reports', [
    "How do I generate a report for a reaction?",
    "Create a Word report of several reactions.",
], f"""
{py('''
archive = instance.create_report(r1, s1, file_name='Weekly')   # waits for the job
archive.download('weekly.docx')
r1.report_docx('reaction.docx')                                # one reaction, right away
''')}

`template=` one of `standard`, `spectrum`, `supporting_information`, `supporting_information_std_rxn`,
`rxn_list_xlsx`, `rxn_list_csv`, `rxn_list_html`.
""")

seed('inbox', [
    "How do I assign a file from my inbox to a sample?",
    "Move an inbox file into a sample's analyses.",
], f"""
{py('''
instance.inbox.upload('nmr.zip')
att = instance.inbox.unlinked_attachments()[0]
instance.inbox.assign(att, sample)        # becomes a new analysis of the sample
''')}
""")

seed('chemicals', [
    "How do I set chemical inventory data on a sample?",
    "Attach a safety data sheet to a sample.",
], f"""
{py('''
chem = sample.get_chemical()          # chem.exists is False if there is none yet
chem.cas = '64-17-5'
chem.data['status'] = 'Available'
chem.data['location'] = 'Cabinet 3'
chem.save()

chem = sample.attach_safety_sheet('sds.pdf', 'Merck', 'merckProductInfo', {'productNumber': 'E7023'})
print(chem.safety_sheets)
''')}
""")

seed('measurements', [
    "How do I record measurements for samples from a research plan?",
], f"""
{py('''
plan.create_measurements([{'sample': s, 'description': 'yield', 'value': 87.5, 'unit': '%'}])
for m in s.measurements():
    print(m.description, m.value, m.unit)
''')}
""")

seed('profiles', [
    "How do I manage converter profiles?",
    "Why is my dataset metadata empty?",
], f"""
Dataset metadata is filled only if a converter profile matches the uploaded file:

{py('''
pm = instance.get_profile_manager()
for p in pm.profiles:             # a property, not a method
    print(p.id, p.title)
p = pm.new_profile_from_file('./my_profile.json')
p.save()
''')}
""")

seed('errors', [
    "What exceptions can chemotion_api raise?",
    "How should I handle errors from save()?",
], """
- `ConnectionError`: server unreachable, collection/profile request or share failed.
- `PermissionError`: login failed; `TokenExpiredError` when the token has expired; restricted element
  on save; `WithheldValueError` when using a withheld value as a number.
- `chemotion_api.connection.ChemotionRequestError` (a `RequestException`): load/save/list failed;
  `.status_code`, `.url`, `.context` (e.g. `saving sample 12`). `401` = not visible to you.
- `ChemotionServerError`: the same for 5xx, often triggered by invalid data.
- `ChemotionRejectedError`: success status but the body reports a refusal; also a `ValueError`,
  reply in `.body`.
- `ValueError`: invalid segment value (message names the field), unit not allowed, unresolvable
  SMILES, a change the ELN would drop silently.
- `ModuleNotFoundError`: collection path does not exist.
- `KeyError`: unknown solvent/segment/field name.
- `StopIteration`: `by_name`/`by_id` found nothing.
""")

seed('errors', [
    "save() raises ValueError. How do I find out why?",
], """
Read the message: it usually names a segment field whose value does not fit (wrong select option,
non-integer for an integer field, unknown unit). Other causes: a reaction-link field (`reference`,
`coefficient`, `waste`, ...) changed on a sample saved with `sample.save()` instead of
`reaction.save()`, a changed `short_label` of a saved sample, or a reaction's RInChI. Values loaded
from the server are never rejected, only the ones you changed.
""")

seed('admin', [
    "How do I deactivate a user account as admin?",
    "Admin: find a user and reset the password.",
], f"""
Only an admin account can do this; changes are immediate. Confirm with the user first.

{py('''
admin = instance.get_user()                 # an Admin when logged in as admin
(user,) = admin.find_users('Smith')
admin.update_user(user['id'], account_active=False)
admin.reset_password(user['id'])
''')}

Deleting users, groups or devices needs `confirm=<abbreviation>`; a deleted user can be restored with
`restore_user(abbr)`.
""")

seed('admin', [
    "How do I create a device as admin?",
], f"""
{py('''
admin = instance.get_user()
device = admin.create_device('NMR 400', 'NMR1')
admin.update_device(device.id, people=[user_id])
''')}

A rejected abbreviation raises `ChemotionRejectedError` (the server answers 201 with an `errors`
body). A created device does not appear in `fetchDevices()` (server-side inconsistency).
""")

seed('account', [
    "How do I create an API token from Python?",
], f"""
The ELN issues tokens only for accounts with two-factor login, against a current one-time password:

{py('''
if not instance.two_factor_enabled():
    instance.request_two_factor_change()     # the ELN emails a confirmation link
token = instance.create_api_token(otp='123456', name='CI', expires_in_days=90)
''')}
""")

seed('cli', [
    "How do I start a local test Chemotion instance?",
    "What does the chemotion_api command line do?",
], """
The `chemotion_api` CLI scaffolds and manages **local dockerized** instances, for development and tests
only (never productive instances; use ChemCLI for those):

```sh
chemotion_api new        # create a docker-compose file (asks for version and ports)
chemotion_api up         # start
chemotion_api backup     # dump the PostgreSQL database
chemotion_api restore    # restore a dump
chemotion_api --help
```

It needs Docker with Compose, and the PostgreSQL client tools for backup/restore.
""")


# ---------------------------------------------------------------------------------------------
# 2. Templated tasks over real chemicals and reactions
# ---------------------------------------------------------------------------------------------

# name, SMILES, CAS, density g/ml (None = solid)
CHEMICALS = [
    ('Ethanol', 'CCO', '64-17-5', 0.789),
    ('Methanol', 'CO', '67-56-1', 0.792),
    ('Acetone', 'CC(C)=O', '67-64-1', 0.784),
    ('Benzaldehyde', 'O=Cc1ccccc1', '100-52-7', 1.044),
    ('Toluene', 'Cc1ccccc1', '108-88-3', 0.867),
    ('Aniline', 'Nc1ccccc1', '62-53-3', 1.022),
    ('Phenol', 'Oc1ccccc1', '108-95-2', None),
    ('Acetic acid', 'CC(=O)O', '64-19-7', 1.049),
    ('Benzoic acid', 'OC(=O)c1ccccc1', '65-85-0', None),
    ('Acetophenone', 'CC(=O)c1ccccc1', '98-86-2', 1.028),
    ('Benzyl alcohol', 'OCc1ccccc1', '100-51-6', 1.044),
    ('Ethyl acetate', 'CCOC(C)=O', '141-78-6', 0.902),
    ('Triethylamine', 'CCN(CC)CC', '121-44-8', 0.726),
    ('Pyridine', 'c1ccncc1', '110-86-1', 0.982),
    ('Bromobenzene', 'Brc1ccccc1', '108-86-1', 1.495),
    ('Phenylboronic acid', 'OB(O)c1ccccc1', '98-80-6', None),
    ('Sodium borohydride', '[Na+].[BH4-]', '16940-66-2', None),
    ('Salicylic acid', 'OC(=O)c1ccccc1O', '69-72-7', None),
    ('Acetic anhydride', 'CC(=O)OC(C)=O', '108-24-7', 1.08),
    ('Acetylsalicylic acid', 'CC(=O)Oc1ccccc1C(=O)O', '50-78-2', None),
    ('1-Phenylethanol', 'CC(O)c1ccccc1', '98-85-1', 1.012),
    ('Potassium carbonate', '[K+].[K+].[O-]C([O-])=O', '584-08-7', None),
    ('Cyclohexanone', 'O=C1CCCCC1', '108-94-1', 0.947),
    ('Cyclohexanol', 'OC1CCCCC1', '108-93-0', 0.962),
    ('Acetanilide', 'CC(=O)Nc1ccccc1', '103-84-4', None),
    ('Methyl benzoate', 'COC(=O)c1ccccc1', '93-58-3', 1.088),
    ('Biphenyl', 'c1ccc(-c2ccccc2)cc1', '92-52-4', None),
    ('Sulfuric acid', 'OS(=O)(=O)O', '7664-93-9', 1.83),
    ('Magnesium', '[Mg]', '7439-95-4', None),
    ('Copper', '[Cu]', '7440-50-8', None),
]
CHEM = {c[0]: c for c in CHEMICALS}

# title, starting material, reactant(s), product, solvent (exact ELN name), temperature °C, hours, purification
REACTIONS = [
    ('Reduction of benzaldehyde', 'Benzaldehyde', ['Sodium borohydride'], 'Benzyl alcohol', 'Methanol', 0, 1,
     ['Extraction']),
    ('Reduction of acetophenone', 'Acetophenone', ['Sodium borohydride'], '1-Phenylethanol', 'Ethanol', 25, 2,
     ['Extraction', 'Flash-Chromatography']),
    ('Acetylation of salicylic acid', 'Salicylic acid', ['Acetic anhydride', 'Sulfuric acid'],
     'Acetylsalicylic acid', None, 85, 0.25, ['Recrystallisation']),
    ('Suzuki coupling of bromobenzene', 'Bromobenzene', ['Phenylboronic acid', 'Potassium carbonate'],
     'Biphenyl', 'Toluene', 100, 12, ['Flash-Chromatography']),
    ('Reduction of cyclohexanone', 'Cyclohexanone', ['Sodium borohydride'], 'Cyclohexanol', 'Methanol', 0, 1,
     ['Distillation']),
    ('Acetylation of aniline', 'Aniline', ['Acetic anhydride'], 'Acetanilide', 'Water', 25, 0.5,
     ['Filtration', 'Recrystallisation']),
    ('Fischer esterification of benzoic acid', 'Benzoic acid', ['Methanol', 'Sulfuric acid'], 'Methyl benzoate',
     None, 65, 4, ['Extraction', 'Distillation']),
]

COLLECTIONS = ['/Projects/Team One', '/Synthesis/2026', 'My data', '/Students/Lab course', '/PhD/Chapter 3',
               '/Projects/Catalysis', 'Teaching']


def var(name):
    return ''.join(ch for ch in name.lower().replace(' ', '_').replace('-', '_') if ch.isalnum() or ch == '_') \
        .lstrip('0123456789_') or 'x'


def amount_phrase():
    unit = rng.choice(['g', 'mg', 'mmol', 'mol', 'ml'])
    val = {'g': rng.choice([0.5, 1, 1.5, 2, 2.5, 5, 10]), 'mg': rng.choice([50, 120, 250, 500, 750]),
           'mmol': rng.choice([0.5, 1, 2, 5, 10, 20]), 'mol': rng.choice([0.01, 0.05, 0.1]),
           'ml': rng.choice([1, 2, 5, 10, 25])}[unit]
    return val, unit


def to_api(val, unit):
    """Return (code_value, QuantityUnit member, note)."""
    if unit == 'g':
        return repr(val), 'Gram', ''
    if unit == 'mg':
        return f'{val} / 1000', 'Gram', f'{val} mg = {val / 1000:g} g; set_amount does not accept mg.'
    if unit == 'mol':
        return repr(val), 'Mole', ''
    if unit == 'mmol':
        return f'{val} / 1000', 'Mole', f'{val} mmol = {val / 1000:g} mol; set_amount does not accept mmol.'
    if unit == 'ml':
        return f'{val} / 1000', 'Liter', f'{val} ml = {val / 1000:g} l; liter needs a density or molarity.'
    raise ValueError(unit)


SAMPLE_ASKS = [
    "Create a sample of {name} ({smiles}) with {val} {unit} in the collection '{col}'.",
    "Add {val} {unit} of {name} to '{col}'.",
    "Please make a new {name} sample in {col}, amount {val} {unit}.",
    "I need a {name} sample, SMILES {smiles}, {val} {unit}, collection {col}.",
    "New sample: {name}, {val} {unit}. Put it in '{col}' and give me the link.",
]

for _ in range(3):
    for name, smiles, cas, dens in CHEMICALS:
        val, unit = amount_phrase()
        if unit == 'ml' and dens is None:
            unit, val = 'g', 1
        colpath = rng.choice(COLLECTIONS)
        v, qu, note = to_api(val, unit)
        extra = ''
        if unit == 'ml':
            extra = f"\ns.properties['density'] = {dens}            # g/ml, so the volume can be converted"
        code = f"""
from chemotion_api import Instance
from chemotion_api.elements.utils import QuantityUnit

instance = Instance('https://eln.example.org').test_connection().login_token('chemtoken_...')
col = instance.get_root_collection().get_or_create_collection('{colpath}')

s = col.new_sample_smiles('{smiles}')
s.properties['external_label'] = '{name}'{extra}
s.set_amount({v}, QuantityUnit.{qu})
s.save()
print(s.short_label, s.url())
"""
        notes = [n for n in [note] if n]
        if colpath.count('/') > 1:
            notes.append(f"`get_or_create_collection` creates only the last level, so the parents of "
                         f"'{colpath}' must exist.")
        if smiles.startswith('[') and '.' not in smiles:
            notes.append("Metals need brackets in SMILES ('" + smiles + "').")
        ask = rng.choice(SAMPLE_ASKS).format(name=name, smiles=smiles, val=val, unit=unit, col=colpath)
        ans = py(code) + ('\n\n' + '\n'.join('- ' + n for n in notes) if notes else '')
        add(ask, ans, 'sample', 'task', system='any')

# property edits on existing samples
PROP_TASKS = [
    ("Set the purity of sample {id} to {p} %.", "s.properties['purity'] = {pf}",
     "Purity is a fraction: {p} % → {pf}."),
    ("Change the description of sample {id} to '{text}'.", "s.properties['description'] = '{text}'", ""),
    ("Sample {id} is stored in {loc}. Record that.", "s.properties['location'] = '{loc}'", ""),
    ("Set the external label of sample {id} to '{label}'.", "s.properties['external_label'] = '{label}'", ""),
    ("Sample {id} has density {d} g/ml.", "s.properties['density'] = {d}", "Density is in g/ml."),
    ("The melting point of sample {id} is {mp}-{mp2} °C.",
     "s.properties['melting_point_lowerbound'] = {mp}\ns.properties['melting_point_upperbound'] = {mp2}", ""),
    ("Make sample {id} a {m} M solution.", "s.properties['molarity'] = {{'value': {m}, 'unit': 'M'}}", ""),
    ("Mark sample {id} as top secret.", "s.properties['is_top_secret'] = True", ""),
]
for _ in range(4):
    for ask, line, note in PROP_TASKS:
        p = rng.choice([90, 95, 97, 98, 99, 99.5])
        f = dict(id=rng.randint(2, 400), p=p, pf=round(p / 100, 4), text=rng.choice(
            ['Stored at 4 °C', 'Light sensitive', 'Batch from supplier B', 'Dried over MgSO4']),
            loc=rng.choice(['Fridge 2', 'Cabinet 3', 'Glovebox']), label=rng.choice(['EtOH batch 3', 'KS-114', 'LOT-77']),
            d=rng.choice([0.79, 0.87, 1.04, 1.49]), mp=rng.choice([120, 135, 64]), m=rng.choice([0.1, 0.5, 1, 2]))
        f['mp2'] = f['mp'] + 2
        code = f"s = instance.get_sample({f['id']})\n{line.format(**f)}\ns.save()"
        ans = py(code) + ('\n\n' + note.format(**f) if note else '')
        add(ask.format(**f), ans, 'sample', 'task', system='any')

REACTION_ASKS = [
    "Create a reaction '{title}' in '{col}': {sm} with {rea} gives {prod}.",
    "Set up the reaction {title}. Starting material {sm}, reagents {rea}, product {prod}, in {col}.",
    "I want to document '{title}' in Chemotion ({col}). Make the samples and the reaction.",
    "Write code for a new reaction: {sm} + {rea} -> {prod}, collection '{col}'.",
]

for _ in range(4):
    for title, sm, reas, prod, solv, temp, hours, purif in REACTIONS:
        colpath = rng.choice(COLLECTIONS)
        sm_mmol = rng.choice([2, 5, 10, 20])
        eqs = [rng.choice([1.1, 1.2, 1.5, 2.0]) for _ in reas]
        include_amounts = rng.random() < 0.7
        include_cond = rng.random() < 0.7
        lines = ["from chemotion_api import Instance",
                 "from chemotion_api.elements.utils import QuantityUnit", "",
                 "instance = Instance('https://eln.example.org').test_connection().login_token('chemtoken_...')",
                 f"col = instance.get_root_collection().get_or_create_collection('{colpath}')", "",
                 f"sm = col.new_sample_smiles('{CHEM[sm][1]}')",
                 f"sm.properties['external_label'] = '{sm}'",
                 "sm.save()"]
        for i, rn in enumerate(reas):
            lines += [f"rea{i} = col.new_sample_smiles('{CHEM[rn][1]}')",
                      f"rea{i}.properties['external_label'] = '{rn}'", f"rea{i}.save()"]
        lines += [f"prod = col.new_sample_smiles('{CHEM[prod][1]}')",
                  f"prod.properties['external_label'] = '{prod}'", "prod.save()", "",
                  "r = col.new_reaction()", f"r.name = '{title}'",
                  "r.starting_materials.append(sm)          # adds a split of sm"]
        for i in range(len(reas)):
            lines.append(f"r.reactants.append(rea{i})")
        lines.append("r.products.append(prod)                  # adds a copy of prod")
        if solv:
            lines.append(f"r.solvents.append(col.new_solvent('{solv}'))")
        if include_amounts:
            lines += ["", "r.reference_sample = r.starting_materials[0]",
                      f"r.starting_materials[0].set_amount({sm_mmol} / 1000, QuantityUnit.Mole)   # {sm_mmol} mmol"]
            for i, e in enumerate(eqs):
                lines.append(f"r.reactants[{i}].set_amount({e}, QuantityUnit.Equivalent)")
        if include_cond:
            lines += ["", f"r.properties['temperature'].add_time_point(0, 0, 0, {temp})",
                      f"r.properties['temperature'].add_time_point({int(hours)}, {int(round((hours % 1) * 60))}, 0, {temp})",
                      "r.properties['status'] = 'Planned'",
                      f"r.properties['purification'] = {purif!r}"]
        lines += ["r.save()", "print(r.short_label, r.url())"]
        notes = ["Starting materials and reactants are added as splits, products as copies, so the "
                 "reaction holds new samples; the originals stay unchanged."]
        if include_amounts:
            notes.append("Equivalents are relative to the reference sample and are recomputed on `r.save()`.")
        if solv is None and include_cond:
            notes.append("No solvent was given, so none is added.")
        ask = rng.choice(REACTION_ASKS).format(title=title, col=colpath, sm=sm, rea=' and '.join(reas), prod=prod)
        if include_amounts:
            ask += f" Use {sm_mmol} mmol of {sm} and " + ', '.join(f'{e} eq {rn}' for e, rn in zip(eqs, reas)) + '.'
        if include_cond:
            ask += f" {temp} °C for {hours:g} h, planned, purification: {', '.join(purif)}."
        add(ask, py('\n'.join(lines)) + '\n\n' + '\n'.join('- ' + n for n in notes), 'reaction', 'task',
            system='any')

# yields / status updates on existing reactions
for _ in range(15):
    rid = rng.randint(2, 300)
    g = rng.choice([0.85, 1.2, 1.9, 0.43])
    st = rng.choice(['Successful', 'Done', 'Not Successful', 'Analyses Pending', 'Running'])
    ask = rng.choice([
        f"Reaction {rid} gave {g} g of product. Record it and set the status to {st}.",
        f"Update reaction {rid}: product mass {g} g, status '{st}'.",
        f"Log {g} g isolated product for reaction {rid} and mark it {st}.",
    ])
    code = f"""
from chemotion_api.elements.utils import QuantityUnit

r = instance.get_reaction({rid})
print([p.properties['external_label'] or p.name for p in r.products])   # check which product
r.products[0].set_amount({g}, QuantityUnit.Gram)      # real amount of the product
r.properties['status'] = '{st}'
r.save()                                              # yield is computed from the reference
print(r.url())
"""
    add(ask, py(code) + "\n\nIf the reaction has more than one product, pick the right one before setting the "
                        "amount.", 'reaction', 'task', system='any')

# search tasks
SEARCH_FIELDS = [('name', 'Ethanol'), ('cas', '64-17-5'), ('external_label', 'KS-114'),
                 ('short_label', 'API-12'), ('name', 'Benzaldehyde'), ('cas', '108-88-3')]
for _ in range(3):
    for field, value in SEARCH_FIELDS:
        n = rng.choice([5, 10, 20, 50])
        match = rng.choice(['LIKE', 'EXACT'])
        ask = rng.choice([f"Find up to {n} samples whose {field.replace('_', ' ')} is {value}.",
                          f"Search samples by {field} = {value} (max {n}).",
                          f"Which samples have {field.replace('_', ' ')} {value}?"])
        code = f"""
from chemotion_api.search.utils import EnumMatch, EnumConnector

hits = (instance.search_sample()
        .add_search_condition(EnumMatch.{match}, EnumConnector.AND, {field}='{value}')
        .find_max({n})
        .request())
for s in hits:
    print(s.id, s.short_label, s.name)
"""
        add(ask, py(code) + ("\n\n`LIKE` is a case-insensitive partial match; use `EXACT` for an exact value."
                             if match == 'LIKE' else "\n\n`EXACT` matches the whole value; `LIKE` would match "
                                                     "parts of it."), 'search', 'task', system='any')

for smi, label in [('c1ccccc1O', 'phenol'), ('c1ccncc1', 'pyridine'), ('C(=O)O', 'carboxylic acid'),
                   ('c1ccccc1Br', 'bromobenzene'), ('NC(=O)', 'amide')]:
    for col_scoped in (False, True):
        ask = f"Find all samples and reactions that contain a {label} substructure" + \
              (" in the collection '/Projects/Team One'." if col_scoped else ".")
        scope = "\ncol = instance.get_root_collection().get_collection('/Projects/Team One')" if col_scoped else ''
        chain = ".in_collection(col.id)" if col_scoped else ''
        code = f"""{scope}
res = instance.search_structure().substructure('{smi}'){chain}.find_max(100).request()
for s in res.samples:
    print('sample', s.short_label)
for r in res.reactions:
    print('reaction', r.short_label)
print(res.total('sample'), res.total('reaction'))
"""
        add(ask, py(code), 'search', 'task', system='any')

# segments with varied fields
SEGMENT_CASES = [
    ('Electrochemistry', 'Cell', [('Electrode type', "'disk'", 'select'),
                                  ('Temperature', "{'value': 25, 'unit': 'C'}", 'system-defined'),
                                  ('Cycles', '3', 'integer')]),
    ('Crystallography', 'Crystal', [('Color', "'colourless'", 'text'),
                                    ('Size', "{'value': 0.2, 'unit': 'mm'}", 'system-defined')]),
    ('Photochemistry', 'Light source', [('Wavelength', "{'value': 365, 'unit': 'nm'}", 'system-defined'),
                                        ('Lamp', "'LED'", 'select')]),
]
for seg, layer, fields in SEGMENT_CASES:
    for etype, getter in [('sample', 'get_sample'), ('reaction', 'get_reaction'), ('research plan', 'get_research_plan')]:
        eid = rng.randint(2, 99)
        ask = (f"On {etype} {eid}, fill the '{seg}' segment, layer '{layer}': " +
               ', '.join(f"{f} = {v.strip(chr(39))}" for f, v, _ in fields) + '.')
        code = [f"el = instance.{getter}({eid})", f"print(el.segments.available())",
                f"layer = el.segments.get('{seg}')['{layer}']    # .get() adds the segment if missing"]
        for f, v, t in fields:
            code.append(f"layer['{f}'] = {v}" + f"    # {t}")
            if t == 'select':
                code.insert(2, f"print(el.segments.options('{seg}', '{layer}', '{f}'))")
            if t == 'system-defined':
                code.insert(2, f"print(el.segments.units('{seg}', '{layer}', '{f}'))")
        code.append("el.save()                      # invalid values raise ValueError naming the field")
        ans = (py('\n'.join(code)) + "\n\nSegment, layer and field names are the labels shown in the ELN "
               "(case-sensitive). I print the options and units first because they depend on your instance's "
               "template; adjust the values if they differ.")
        add(ask, ans, 'segments', 'task', system='any')

# analyses uploads
ANALYSES = [('NMR', '1H NMR in CDCl3', 'nmr_1h.zip'), ('IR', 'ATR-IR', 'ir.jdx'), ('MS', 'ESI-MS', 'ms.mzML'),
            ('HPLC', 'purity check', 'hplc.zip'), ('X-ray', 'single crystal', 'crystal.cif'),
            ('13C NMR', '13C{1H} in DMSO-d6', 'nmr_13c.zip')]
for kind, desc, fname in ANALYSES:
    for etype, getter in [('sample', 'get_sample'), ('reaction', 'get_reaction')]:
        eid = rng.randint(2, 300)
        ask = rng.choice([f"Upload {fname} as a {kind} analysis to {etype} {eid}.",
                          f"Add the {kind} file ./{fname} to {etype} {eid}, description '{desc}'.",
                          f"Attach my {kind} measurement ({fname}) to {etype} {eid}."])
        code = f"""
el = instance.{getter}({eid})
ana = el.analyses.add_analyses('{kind}')
ana['description'] = '{desc}'
ana.add_dataset('./{fname}')      # uploaded on save
el.save()
"""
        add(ask, py(code) + "\n\nA matching converter profile fills the dataset metadata. Use "
                            "`el.save_analyses()` if you only want to save the analyses.", 'analyses', 'task',
            system='any')

# sharing variants
SHARE_CASES = [('ReadElements', 'read-only', 10), ('EditElements', 'with edit rights', 10),
               ('ReadElements', 'read-only but hide details', 3), ('AddElements', 'so they can add elements', 10),
               ('ManageShares', 'and let them manage shares', 10)]
for perm, phrase, dl in SHARE_CASES:
    for who in ['Smith', 'Müller', 'Nguyen']:
        colpath = rng.choice(COLLECTIONS)
        ask = f"Share '{colpath}' with {who} {phrase}."
        code = f"""
from chemotion_api.collection import CollectionSharePermission as P

col = instance.get_root_collection().get_collection('{colpath}')
users = instance.find_user_by_name('{who}')      # up to 3 matches
for u in users:
    print(u)                                    # confirm the right person before sharing
col.share(P.{perm}, users[0], detail_level={dl})
"""
        note = ("`detail_level=10` discloses every field (and allows export)." if dl == 10 else
                f"`detail_level={dl}` withholds some fields from {who}; restricted fields read as `WITHHELD`.")
        add(ask, py(code) + f"\n\nThe share is sent immediately. {note} If more than one user matches, ask "
                            "which one is meant.", 'sharing', 'task', system='any')

# unit conversion questions
for _ in range(20):
    val, unit = amount_phrase()
    v, qu, note = to_api(val, unit)
    ask = rng.choice([f"How do I set {val} {unit} on a sample?", f"Set the amount of sample 7 to {val} {unit}.",
                      f"set_amount for {val} {unit}?"])
    code = f"from chemotion_api.elements.utils import QuantityUnit\n\ns = instance.get_sample(7)\ns.set_amount({v}, QuantityUnit.{qu})\ns.save()"
    add(ask, py(code) + ('\n\n' + note if note else ''), 'sample', 'task', system='any')


# ---------------------------------------------------------------------------------------------
# 3. Pitfalls: broken code -> fix
# ---------------------------------------------------------------------------------------------

PITFALLS = [
    ("s = col.new_sample_smiles('CCO')\ns.properties['purity'] = 98",
     "Purity is a fraction (0 < purity <= 1), and the sample is never saved.",
     "s = col.new_sample_smiles('CCO')\ns.properties['purity'] = 0.98\ns.save()"),
    ("s.set_amount(QuantityUnit.Gram, 2.5)",
     "The value comes first, then the unit.",
     "s.set_amount(2.5, QuantityUnit.Gram)\ns.save()"),
    ("s.set_amount(500, 'mg')",
     "`set_amount` only accepts 'g', 'mol', 'l' or 'Equivalent'. Convert mg to g.",
     "s.set_amount(500 / 1000, QuantityUnit.Gram)\ns.save()"),
    ("root = instance.get_root_collection()\ns = root.new_sample_smiles('CCO')",
     "The root collection ('All') has no `new_*` methods. Use a real collection.",
     "root = instance.get_root_collection()\ncol = root.get_or_create_collection('My data')\ns = col.new_sample_smiles('CCO')\ns.save()"),
    ("col = root.get_collection('../Archive')",
     "`.` and `..` are not supported in collection paths. Use an absolute path.",
     "col = root.get_collection('/Archive')"),
    ("for ana in s.analyses:\n    for ds in ana['datasets']:\n        print(ds['name'])",
     "Datasets are an attribute (`ana.datasets`), and a dataset's name is `ds.name`; its dict holds only "
     "metadata.",
     "for ana in s.analyses:\n    for ds in ana.datasets:\n        print(ds.name)"),
    ("s.attachments.add_file('./out/report.pdf')\ns.save()\natt = s.attachments.load_attachment(filename='./out/report.pdf')",
     "Reload after saving (`load_after_save=True`), and look the file up by its basename.",
     "s.attachments.add_file('./out/report.pdf')\ns.save(load_after_save=True)\natt = s.attachments.load_attachment(filename='report.pdf')"),
    ("s = instance.get_sample(12)\ns.properties['coefficient'] = 2\ns.save()",
     "Reaction-link fields are stored with the reaction. Change them on the reaction's material and save "
     "the reaction; `sample.save()` raises ValueError here.",
     "r = s.reaction\nr.starting_materials[0].properties['coefficient'] = 2   # pick the material of s\nr.save()"),
    ("col.share(4, user)",
     "v4 renumbered the permission levels, so use the enum names; and `detail_level` is required.",
     "from chemotion_api.collection import CollectionSharePermission as P\ncol.share(P.ManageShares, user, detail_level=10)"),
    ("col.add_collection('P 124')",
     "Tree changes are local until `root.save()`.",
     "col.add_collection('P 124')\ninstance.get_root_collection().save()"),
    ("r.properties['status'] = 'success'\nr.save()",
     "Unknown status values are ignored on save. The value is 'Successful'.",
     "r.properties['status'] = 'Successful'\nr.save()"),
    ("thf = col.new_solvent('THF')",
     "Solvent names must match `instance.get_solvent_list()` exactly.",
     "thf = col.new_solvent('Tetrahydrofuran (THF)')"),
    ("s.segments['Electrochemistry']['Cell']['Cycles'] = 3",
     "`segments[...]` is None when the element doesn't have that segment yet. Use `.get()`, which adds it, "
     "and save.",
     "s.segments.get('Electrochemistry')['Cell']['Cycles'] = 3\ns.save()"),
    ("last = col.get_samples()[-1]",
     "ElementSet does not support negative indices.",
     "es = col.get_samples()\nlast = es[len(es) - 1]"),
    ("mg = col.new_sample_smiles('Mg')",
     "Elements outside the organic subset need brackets in SMILES.",
     "mg = col.new_sample_smiles('[Mg]')\nmg.save()"),
    ("v.products[0].set_yield(0.85)",
     "Yields in variations are percent, so 0.85 means 0.85 %.",
     "v.products[0].set_yield(85)\nr.save()"),
    ("if s.properties['description'] == '***':\n    print('hidden')",
     "Compare withheld values by identity with `WITHHELD`.",
     "from chemotion_api.utils.withheld import WITHHELD\nif s.properties['description'] is WITHHELD:\n    print('hidden')"),
    ("r.starting_materials.append(s)\nr.reactants.append(s)",
     "A sample can be in a reaction only once; the second append raises ValueError.",
     "r.starting_materials.append(s)\nr.save()"),
    ("pm = instance.get_profile_manager()\nfor p in pm.profiles():\n    print(p.title)",
     "`profiles` is a property, not a method.",
     "pm = instance.get_profile_manager()\nfor p in pm.profiles:\n    print(p.title)"),
    ("wp.save(load_after_save=True)",
     "`Wellplate.save()` takes no argument; it saves and reloads anyway.",
     "wp.save()"),
    ("r.properties['purification'] = 'column'",
     "Purification is a list of allowed values; unknown ones are dropped silently.",
     "r.properties['purification'] = ['Flash-Chromatography']\nr.save()"),
    ("g.properties['general']['serial number'] = 'X-12'",
     "Layer and field labels are case-sensitive, exactly as shown in the ELN.",
     "g.properties['General']['Serial number'] = 'X-12'\ng.save()"),
    ("s.properties['short_label'] = 'MY-1'\ns.save()",
     "The ELN assigns short labels; changing one raises ValueError. Use the external label.",
     "s.properties['external_label'] = 'MY-1'\ns.save()"),
    ("col.unshare()",
     "`unshare()` refuses an empty user list. Name the users, or pass `all=True` deliberately.",
     "col.unshare(user)"),
    ("screen.add_wellplate(plate)\nscreen.save()",
     "Screens have no `add_wellplate` method; links are the id list `wellplate_ids`, and the plate must be "
     "saved.",
     "plate.save()\nscreen.wellplate_ids.append(plate.id)\nscreen.save()"),
]

PITFALL_ASKS = ["This doesn't work, what's wrong?\n\n{code}", "Why does this fail?\n\n{code}",
                "Can you fix my code?\n\n{code}", "Review this chemotion_api snippet:\n\n{code}"]
for bad, why, good in PITFALLS:
    for ask in rng.sample(PITFALL_ASKS, 2):
        add(ask.format(code=py(bad)), f"{why}\n\n{py(good)}", 'pitfall', 'fix', system='any')


# ---------------------------------------------------------------------------------------------
# 4. Behaviour: safety, asking, honesty
# ---------------------------------------------------------------------------------------------

seed('behaviour', [
    "Delete all samples in my collection 'Old'.",
    "Clean up: remove every reaction in '/Archive'.",
], f"""
That deletes data in a real lab notebook and cannot be undone, so let's check first. This lists what
would be deleted without changing anything:

{py('''
col = instance.get_root_collection().get_collection('Old')
samples = list(col.get_samples(per_page=100))
for s in samples:
    print(s.id, s.short_label, s.name)
print(len(samples), 'samples')
''')}

Please confirm that these should go. Then:

{py('''
kept = col.delete_elements(*samples)
print('kept by the server:', kept)
''')}

v4 only destroys elements that are in no other collection; samples still used in a reaction or shared
elsewhere survive. If you only want them out of this collection, use `col.remove_elements(*samples)`
instead, which deletes nothing.
""", kind='behaviour')

seed('behaviour', [
    "Set the purity of all samples in '/Projects/Team One' to 1.",
], f"""
That is a bulk edit of many records, so first a dry run:

{py('''
col = instance.get_root_collection().get_collection('/Projects/Team One')
for s in col.get_samples(per_page=100):
    print(s.short_label, s.properties['purity'])
''')}

If that list is right, confirm and run:

{py('''
for s in col.get_samples(per_page=100):
    if s.properties['purity'] != 1:
        s.properties['purity'] = 1.0
        s.save()
''')}

Each sample is loaded and saved separately (two requests each). Restricted samples (shared below
detail level 10) cannot be saved and raise `PermissionError`.
""", kind='behaviour')

seed('behaviour', [
    "Add the product to my reaction.",
    "Update the sample.",
], """
Which one? I need:

1. the reaction (id or short label, e.g. `API-R4`) or the sample,
2. what to change (for a product: the SMILES or an existing sample id, and the obtained amount).

Then I can write the code, e.g. `r = instance.find_reaction_by_short_label('API-R4')`.
""", kind='behaviour')

seed('behaviour', [
    "Can chemotion_api export a collection as .eln (RO-Crate)?",
], """
Not in this release: the FAIR `.eln` (RO-Crate) export and the offline ingester are not included. You
can export the ELN's native ZIP with `col.export_zip('project.zip')` and import it into another ELN v4
with `instance.import_zip('project.zip')`.
""", kind='behaviour')

seed('behaviour', [
    "How do I add a wellplate to a screen with screen.add_wellplate?",
], f"""
There is no `add_wellplate` method on `Screen`. Links are id lists that a save sends as the new state:

{py('''
plate.save()                         # needs an id
screen.wellplate_ids.append(plate.id)
screen.save()
''')}

`research_plan_ids` works the same way; `screen.wellplates` loads the linked plates.
""", kind='behaviour')

seed('behaviour', [
    "Use QuantityUnit.Ppm for my gas product.",
], """
There is no `QuantityUnit.Ppm`. ppm is only the concentration of a gas product in a gas-phase reaction,
set on its gas phase data:

```python
from chemotion_api.elements.utils import GasType

r.gas_schema = True
r.products[0].set_gas_type(GasType.GAS)
r.products[0].properties['gas_phase_data'].ppm = 9222
r.save()
```
""", kind='behaviour')

seed('behaviour', [
    "Run a collection export in the background and give me the job id.",
], """
The server returns no job id. `col.export_zip(path)` starts the job and waits for the matching
notification (`timeout=` seconds, default 900). Re-running it starts a second job, so don't call it in
a retry loop without checking whether the first one finished.
""", kind='behaviour')


# ---------------------------------------------------------------------------------------------
# 5. Multi-turn dialogues
# ---------------------------------------------------------------------------------------------

def dialogue(topic, turns):
    """turns: list of (user, assistant); the last pair is the target."""
    hist, (u, a) = turns[:-1], turns[-1]
    add(u, a, topic, 'dialogue', system=True, history=[(x, y.strip()) for x, y in hist])


dialogue('reaction', [
    ("Create a sample of benzaldehyde in '/Synthesis/2026'.",
     py("col = instance.get_root_collection().get_or_create_collection('/Synthesis/2026')\n"
        "ald = col.new_sample_smiles('O=Cc1ccccc1')\nald.properties['external_label'] = 'Benzaldehyde'\n"
        "ald.save()\nprint(ald.id, ald.short_label)")),
    ("Now make a reduction reaction with NaBH4 to benzyl alcohol, in methanol.",
     py("nabh4 = col.new_sample_smiles('[Na+].[BH4-]')\nnabh4.save()\n"
        "prod = col.new_sample_smiles('OCc1ccccc1')\nprod.save()\n\n"
        "r = col.new_reaction()\nr.name = 'Reduction of benzaldehyde'\nr.starting_materials.append(ald)\n"
        "r.reactants.append(nabh4)\nr.products.append(prod)\nr.solvents.append(col.new_solvent('Methanol'))\n"
        "r.save()\nprint(r.url())")),
    ("Use 5 mmol aldehyde and 1.5 eq NaBH4.",
     py("from chemotion_api.elements.utils import QuantityUnit\n\n"
        "r.reference_sample = r.starting_materials[0]\n"
        "r.starting_materials[0].set_amount(5 / 1000, QuantityUnit.Mole)\n"
        "r.reactants[0].set_amount(1.5, QuantityUnit.Equivalent)\nr.save()") +
     "\n\nSet the amounts on the reaction's materials (`r.starting_materials[0]`), not on `ald`: the reaction "
     "holds a split of it."),
])

dialogue('reaction', [
    ("Load reaction 42 and tell me its materials.",
     py("r = instance.get_reaction(42)\nfor role in ('starting_materials', 'reactants', 'products', 'solvents'):\n"
        "    for s in getattr(r, role):\n        print(role, s.short_label, s.molecule['cano_smiles'], s.get_amount())")),
    ("The product weighed 1.31 g. Record it.",
     py("from chemotion_api.elements.utils import QuantityUnit\n\n"
        "r.products[0].set_amount(1.31, QuantityUnit.Gram)\nr.save()\nr.load()\n"
        "print(r.products[0].properties['equivalent'])   # yield as a fraction of the reference") +
     "\n\nOn save the ELN computes the yield from the reference material."),
])

dialogue('segments', [
    ("Which segments can I add to samples?",
     py("s = instance.get_sample(1)\nprint(s.segments.available())")),
    ("It printed ['Electrochemistry', 'Polymer']. What fields does Electrochemistry have?",
     py("seg = s.segments.get('Electrochemistry')      # adds it locally with defaults\n"
        "for layer, fields in seg.items():\n    for field in fields:\n"
        "        print(layer, field, s.segments.field_type('Electrochemistry', layer, field))") +
     "\n\n`.get()` adds the segment to the local object; nothing changes on the server until `s.save()`."),
    ("Set Cycles to 5 and save.",
     py("seg['Cell']['Cycles'] = 5\ns.save()") +
     "\n\nIf 'Cycles' is in a different layer, use that layer's label instead of 'Cell'."),
])

dialogue('collections', [
    ("Move sample 12 to '/Done Projects'.",
     "Which collection is it in now? `move_elements` needs a source collection other than 'All'. If you "
     "don't know, I can look it up:\n\n" + py("s = instance.get_sample(12)\nsrc = instance.get_collection_of_element(s)\nprint(src.get_path())")),
    ("It's in '/Projects/Team One'.",
     py("root = instance.get_root_collection()\nsrc = root.get_collection('/Projects/Team One')\n"
        "dest = root.get_collection('/Done Projects')\nsrc.move_elements(dest, s)") +
     "\n\nThis is sent immediately; no `save()` is needed."),
])

dialogue('analyses', [
    ("Upload ./nmr.zip as NMR to sample 7.",
     py("s = instance.get_sample(7)\nana = s.analyses.add_analyses('NMR')\nana.add_dataset('./nmr.zip')\ns.save()")),
    ("The metadata of the dataset is empty.",
     "Metadata is filled only when a converter profile matches the uploaded file. Check the profiles:\n\n" +
     py("pm = instance.get_profile_manager()\nfor p in pm.profiles:\n    print(p.id, p.title)") +
     "\n\nIf none matches your instrument's files, a converter admin can add one with "
     "`pm.new_profile_from_file('profile.json').save()`."),
])

dialogue('behaviour', [
    ("Delete sample 99.",
     "Deleting cannot be undone. Here is what sample 99 is:\n\n" +
     py("s = instance.get_sample(99)\nprint(s.short_label, s.name, s.properties['external_label'])\nprint(s.url())") +
     "\n\nShall I delete it?"),
    ("Yes, delete it.",
     py("gone = s.delete()\nprint('deleted' if gone else 'still exists (in another collection or reaction)')") +
     "\n\nIn v4 the record is only destroyed when it is in no other collection."),
])


# ---------------------------------------------------------------------------------------------
# 6. Write
# ---------------------------------------------------------------------------------------------

def main():
    # Split by answer, so paraphrases of one answer never land in both train and eval.
    # Stratified: ~8 % of each topic's answers go to eval (topics with < 4 answers stay in train).
    groups: dict[str, list] = {}
    for e in examples:
        groups.setdefault(e['messages'][-1]['content'], []).append(e)
    by_topic: dict[str, list] = {}
    for g in groups.values():
        by_topic.setdefault(g[0]['meta']['topic'], []).append(g)
    train, evals = [], []
    for topic in sorted(by_topic):
        gs = by_topic[topic]
        rng.shuffle(gs)
        k = max(1, round(len(gs) * 0.08)) if len(gs) >= 4 else 0
        evals += [e for g in gs[:k] for e in g]
        train += [e for g in gs[k:] for e in g]
    rng.shuffle(train)
    for name, rows in [('chemotion_api_train.jsonl', train), ('chemotion_api_eval.jsonl', evals)]:
        with open(OUT / name, 'w', encoding='utf-8') as f:
            for e in rows:
                f.write(json.dumps(e, ensure_ascii=False) + '\n')
    # reference corpus for continued pre-training / RAG
    root = OUT.parent
    parts = [root / 'skills/chemotion-api/SKILL.md', root / 'skills/chemotion-api/references/api.md']
    parts += sorted((root / 'docs').glob('*.rst'))
    with open(OUT / 'chemotion_api_corpus.txt', 'w', encoding='utf-8') as f:
        for p in parts:
            f.write(f'===== {p.relative_to(root)} =====\n{p.read_text(encoding="utf-8")}\n\n')
    stats: dict[str, int] = {}
    for e in examples:
        stats[e['meta']['topic']] = stats.get(e['meta']['topic'], 0) + 1
    print(f'train {len(train)}  eval {len(evals)}  total {len(examples)}')
    print(json.dumps(dict(sorted(stats.items(), key=lambda x: -x[1]))))


if __name__ == '__main__':
    main()
