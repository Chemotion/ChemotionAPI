"""Check the generated training data against the real package.

1. Every ```python block in an assistant message must parse.
2. Every attribute/method name used on an object (`x.name`) must be defined somewhere in chemotion_api
   (def, property, class attribute, enum member, instance attribute) or be a builtin/stdlib name.
3. Every `from chemotion_api... import X` must import successfully.

Run:  uv run python training_data/validate.py
"""
from __future__ import annotations

import ast
import importlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / 'chemotion_api'

# names defined anywhere in the package
known: set[str] = set()
for f in PKG.rglob('*.py'):
    tree = ast.parse(f.read_text(encoding='utf-8'))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            known.add(node.name)
        elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store):
            known.add(node.attr)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                if isinstance(t, ast.Name):
                    known.add(t.id)

# builtin / stdlib attribute names used in examples (str, list, dict, file, datetime...)
GENERIC = {
    'append', 'items', 'keys', 'values', 'get', 'remove', 'insert', 'extend', 'pop', 'read', 'write',
    'replace', 'join', 'strip', 'lower', 'upper', 'format', 'isoformat', 'now', 'content', 'startswith',
    'split', 'copy', 'save', 'load', 'delete', 'id', 'name',
}

blocks = re.compile(r'```python\n(.*?)```', re.S)
errors: list[str] = []
n_blocks = 0
imports: set[tuple[str, str]] = set()

for fname in ('chemotion_api_train.jsonl', 'chemotion_api_eval.jsonl'):
    for ln, line in enumerate(open(ROOT / 'training_data' / fname, encoding='utf-8'), 1):
        ex = json.loads(line)
        for m in ex['messages']:
            if m['role'] != 'assistant':
                continue
            for code in blocks.findall(m['content']):
                n_blocks += 1
                try:
                    tree = ast.parse(code)
                except SyntaxError as e:
                    errors.append(f'{fname}:{ln} syntax: {e}\n{code}')
                    continue
                for node in ast.walk(tree):
                    if isinstance(node, ast.Attribute) and node.attr not in known | GENERIC:
                        errors.append(f'{fname}:{ln} unknown attribute .{node.attr}')
                    if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith('chemotion_api'):
                        for a in node.names:
                            imports.add((node.module, a.name))

for mod, name in sorted(imports):
    try:
        getattr(importlib.import_module(mod), name)
    except Exception as e:  # noqa: BLE001
        errors.append(f'import {name} from {mod}: {e}')

uniq = sorted(set(errors))
print(f'{n_blocks} code blocks, {len(imports)} distinct imports, {len(uniq)} problems')
for e in uniq:
    print(' ', e)
sys.exit(1 if uniq else 0)
