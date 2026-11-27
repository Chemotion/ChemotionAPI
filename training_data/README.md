# chemotion_api training data

Fine-tuning data that teaches a (small) model to write `chemotion_api` code for a Chemotion ELN v4.
Built from `skills/chemotion-api/`, `docs/` and the package code.

| file | content |
|---|---|
| `chemotion_api_train.jsonl` | 812 chat examples for SFT |
| `chemotion_api_eval.jsonl` | 65 held-out examples (answers that never appear in train) |
| `chemotion_api_corpus.txt` | skill + API reference + docs as plain text, for continued pre-training or RAG |
| `generate.py` | builds all three (deterministic) |
| `validate.py` | parses every code block, checks every attribute and import against the package |
| `roadmap.md` | how to train, evaluate and serve a model with this data: tools and models |

Format, one object per line (OpenAI / Hugging Face chat format; drop `meta` if your trainer complains):

```json
{"messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."},
              {"role": "assistant", "content": "..."}], "meta": {"topic": "reaction", "kind": "task"}}
```

`kind`: `qa` (concepts and API facts), `task` (write code for a concrete request), `fix` (broken code →
explanation + corrected code), `behaviour` (confirm before deleting or bulk edits, ask when the request
is ambiguous, say no to things the API cannot do), `dialogue` (multi-turn). Some examples have no system
prompt and the system prompt varies, so the model does not depend on one exact wording.

Regenerate after changing the API or the skill:

```sh
uv run python training_data/generate.py && uv run python training_data/validate.py
```

`validate.py` checks names, not behaviour: a method that exists but is used wrongly is not caught.
New seeds should be taken from the docs, the skill or the tests, not written from memory.
