# Roadmap: teaching a small model to use chemotion_api

Goal: a small, locally runnable model that writes correct `chemotion_api` code for a Chemotion ELN v4
and follows the safety rules: confirm before deleting, dry-run bulk edits, ask when a request is unclear.

The approach: **fine-tune with LoRA on the chat data in this folder, give the model the API reference
through retrieval (RAG) at answer time, and measure it by running its code against the docker test ELN.**
Fine-tuning teaches the style and the conventions; retrieval supplies the exact signatures that a small
model will otherwise make up.

---

## Phase 0: choose a base model

Use an *instruct* model that already writes Python well. Fine-tune with LoRA; don't train from scratch.

| model | size | why | fits 6 GB (QLoRA)? |
|---|---|---|---|
| **Qwen2.5-Coder-Instruct** | 1.5B / 3B / 7B | strongest small code models, Apache-2.0 (3B: Qwen research licence) | 1.5B yes, 3B yes (tight), 7B no |
| **Qwen3** | 0.6B – 8B | general + code, thinking mode can be turned off, Apache-2.0 | ≤ 4B yes |
| **Llama 3.2 Instruct** | 1B / 3B | widely supported, Llama licence | yes |
| **Gemma 3** | 1B / 4B | good instruction following, Gemma licence | 1B yes, 4B tight |
| **Phi-4-mini-instruct** | 3.8B | good reasoning for its size, MIT | tight |
| **SmolLM2/3** | 135M – 3B | very small, fully open, for experiments | yes |

**Recommendation:** start with **Qwen2.5-Coder-1.5B-Instruct** (fast loop on the local RTX 3060, 6 GB),
then train **Qwen2.5-Coder-7B-Instruct** or **Qwen3-8B** on a rented GPU for the version you deploy.
New small models come out often, so check the current
[Hugging Face leaderboards](https://huggingface.co/spaces) and the Qwen/Llama/Gemma release pages
before you choose.

**Baseline first:** run the untuned model on `chemotion_api_eval.jsonl` (Phase 4) with and without the
skill in the prompt. If base model + RAG is already good enough, you may not need fine-tuning.

## Phase 1: prepare the data (done, maintain it)

- `chemotion_api_train.jsonl` / `chemotion_api_eval.jsonl`: chat format, `meta` holds topic and kind.
- `chemotion_api_corpus.txt`: skill + reference + docs for RAG or continued pre-training.
- Regenerate after API changes: `uv run python training_data/generate.py && uv run python training_data/validate.py`.

**Grow the data** where coverage is thin (measurements, account, admin, research plans and screens have
3–6 examples each; samples have 226):

1. **Hand-written seeds** in `generate.py`, taken from the tests (`tests/test_*.py`) and the docs.
2. **Distillation:** have a large model (Claude, GPT, a large Qwen) answer new user questions *with
   SKILL.md and api.md in its context*, then keep only answers that pass `validate.py`, and ideally
   only those whose code runs (Phase 4). This is how you get from ~900 to 3–10k examples.
3. **Real questions:** collect what chemists actually ask (anonymised) and add them.
4. Keep the eval split free of anything derived from it.

Rough sizes: about 1k examples teach the conventions; 3–5k make a 1.5–3B model reliable on the common
tasks.

## Phase 2: fine-tune (LoRA / QLoRA)

### Tools

| tool | use it when |
|---|---|
| **[Unsloth](https://github.com/unslothai/unsloth)** | single GPU, little VRAM: about 2× faster and 50–70 % less memory. **Best fit for the 6 GB laptop.** Exports GGUF directly. |
| **[TRL](https://github.com/huggingface/trl) + [PEFT](https://github.com/huggingface/peft)** | the reference Hugging Face stack (`SFTTrainer`); most flexible |
| **[Axolotl](https://github.com/axolotl-ai-cloud/axolotl)** | YAML-configured runs, multi-GPU, reproducible |
| **[LLaMA-Factory](https://github.com/hiyouga/LLaMA-Factory)** | web UI, many models, no code |
| **[MLX-LM](https://github.com/ml-explore/mlx-lm)** | Apple Silicon Macs |

Hardware: the local RTX 3060 (6 GB) handles QLoRA up to about 3B at a sequence length of 2048. For 7–8B,
rent a 24 GB GPU (RTX 4090 / A10 / L4 on RunPod, Lambda, vast.ai, or Colab Pro). A run over 1k examples
takes minutes; over 5k, under an hour.

### Settings to start from

```
LoRA r=16, alpha=32, dropout=0.05, all linear layers (q,k,v,o,gate,up,down)
learning rate 2e-4 (cosine, warmup 3 %), 2–3 epochs
max sequence length 2048, effective batch size 16 (batch 2 × grad-accum 8)
loss on assistant tokens only
4-bit base (QLoRA) on 6 GB; bf16 LoRA when VRAM allows
```

Watch the eval loss: if it rises while training loss falls, stop earlier or use fewer epochs. With this
much templated data, overfitting after epoch 3 is likely.

### Minimal TRL script

Check it against the TRL version you install; the argument names change between releases.

```python
# pip install trl peft transformers datasets bitsandbytes accelerate
from datasets import load_dataset
from peft import LoraConfig
from trl import SFTConfig, SFTTrainer

data = load_dataset('json', data_files={'train': 'training_data/chemotion_api_train.jsonl',
                                        'eval': 'training_data/chemotion_api_eval.jsonl'})
data = data.remove_columns('meta')

trainer = SFTTrainer(
    model='Qwen/Qwen2.5-Coder-1.5B-Instruct',
    train_dataset=data['train'], eval_dataset=data['eval'],
    peft_config=LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, target_modules='all-linear',
                           task_type='CAUSAL_LM'),
    args=SFTConfig(output_dir='out/chemotion-1.5b', num_train_epochs=3, learning_rate=2e-4,
                   per_device_train_batch_size=2, gradient_accumulation_steps=8,
                   max_length=2048, assistant_only_loss=True, bf16=True,
                   eval_strategy='epoch', save_strategy='epoch', logging_steps=10),
)
trainer.train()
trainer.save_model('out/chemotion-1.5b')
```

For 6 GB, use Unsloth's `FastLanguageModel.from_pretrained(..., load_in_4bit=True)` with the same
dataset and settings (see its Qwen2.5-Coder notebook).

## Phase 3: retrieval at answer time (RAG)

A small model will not memorise 25 sections of signatures. At answer time, retrieve the relevant parts of
`chemotion_api_corpus.txt` and put them in the prompt.

- Split the corpus by section headers (`## 5. Sample`, rst headings), about 300–800 tokens per chunk.
- Embeddings: `BAAI/bge-small-en-v1.5`, `nomic-embed-text` (also available through Ollama) or
  `Qwen3-Embedding-0.6B`.
- Store: a plain numpy array is enough for a few hundred chunks; otherwise Chroma, LanceDB or FAISS.
- Always include SKILL.md's *Pitfalls checklist*: it is short and prevents the most common mistakes.
- **Train the way you serve:** generate some training examples with retrieved chunks in the system
  prompt, so the model learns to use them.

## Phase 4: evaluate

Three levels; report all of them per `meta.topic` and compare against the Phase 0 baseline.

1. **Static (cheap, run on every checkpoint):** for each eval prompt, generate an answer, extract the
   code blocks and run the checks from `validate.py`: does it parse, and are all methods and imports
   real? Track the share of answers with zero unknown names (target > 95 %).
2. **Execution (the real test):** run the generated code against the docker test ELN
   (`just stack-up`, reset with `just stack-reset`) with a test token, then check the result through the
   API: does the sample exist, are the amount, purity and segment value right? Start with 30–50 tasks
   whose results a script can check. Never point this at a productive ELN.
3. **Behaviour (manual or LLM-as-judge):** on delete, bulk-edit and ambiguous prompts, does it dry-run,
   ask and confirm instead of acting? Does it say "not supported" instead of inventing a method?

Feed the failures back into Phase 1 as new seeds and pitfall examples, then retrain.

## Phase 5: package and serve

- Merge the LoRA into the base model (`model.merge_and_unload()`), or keep the adapter separate.
- Quantise to GGUF (Q4_K_M or Q5_K_M) with llama.cpp `convert_hf_to_gguf.py` or Unsloth's
  `save_pretrained_gguf`.
- Serve locally with **[Ollama](https://ollama.com)** or **llama.cpp server** (both have
  OpenAI-compatible APIs); for several users, **[vLLM](https://github.com/vllm-project/vllm)** with LoRA
  adapters.
- Put it behind a small agent loop that retrieves context (Phase 3), shows the generated code to the
  user and **executes it only after the user approves**, at least for anything that writes, shares or
  deletes.
- Publish the adapter and the dataset with a model card that names the chemotion_api version it was
  trained on (e.g. 402.x); a new API version needs a refreshed dataset and a retrain.

## Phase 6: keep it current

- Add `generate.py` + `validate.py` to CI so that API renames break the data build, not the model.
- On every chemotion_api release: regenerate, validate, rerun the Phase 4 evals, retrain if scores drop.
- Version the model together with the package: `chemotion-coder-1.5b-402.0`.

## Milestones

| # | milestone | done when |
|---|---|---|
| 1 | baseline | base model ± skill-in-prompt scored on eval (static) |
| 2 | first LoRA | Qwen2.5-Coder-1.5B trained locally, beats baseline on static eval |
| 3 | execution harness | 30+ checkable tasks run against the docker ELN |
| 4 | data × 3 | ≥ 3k validated examples, thin topics ≥ 30 each |
| 5 | RAG | retrieval in the prompt, trained with retrieved context |
| 6 | 7B model | trained on a rented GPU; ≥ 90 % execution success on the task set |
| 7 | deploy | GGUF on Ollama with an approval-gated agent loop |
