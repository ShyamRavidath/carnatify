"""Offline AST/import/call and duplicate inventory; excludes installed packages."""
from __future__ import annotations
import ast
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from scripts.raga_pipeline import write_json


def inventory(root):
    excluded={'venv','venv_train','runtime_deps','node_modules','.git','.agents','.codex','.claude','__pycache__'}
    rows, hashes = [], defaultdict(list)
    for p in sorted(root.rglob('*.py')):
        if any(x in excluded for x in p.relative_to(root).parts):
            continue
        source=p.read_text(); name=str(p.relative_to(root))
        hashes[hashlib.sha256(p.read_bytes()).hexdigest()].append(name)
        row=dict(path=name,lines=len(source.splitlines()),imports=[],calls=[],definitions=[])
        try:
            tree=ast.parse(source,filename=name)
        except SyntaxError as e:
            row['syntax_error']=dict(line=e.lineno,message=e.msg)
            row['notebook_magics']=any(l.lstrip().startswith(('!','%')) for l in source.splitlines())
            rows.append(row); continue
        for node in ast.walk(tree):
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                row['definitions'].append(dict(name=node.name,line=node.lineno))
            elif isinstance(node,(ast.Import,ast.ImportFrom)):
                row['imports'].append(dict(code=ast.unparse(node),line=node.lineno))
            elif isinstance(node,ast.Call):
                row['calls'].append(dict(name=ast.unparse(node.func),line=node.lineno))
        rows.append(row)
    return dict(python_files=len(rows),files=rows,exact_duplicates=[v for v in hashes.values() if len(v)>1])


if __name__=='__main__':
    result=inventory(ROOT)
    write_json(ROOT/'data/architecture_audit/inventory.json',result)
    print(json.dumps(dict(python_files=result['python_files'],
        syntax_errors=[dict(path=r['path'],**r['syntax_error'],notebook_magics=r['notebook_magics'])
                       for r in result['files'] if 'syntax_error' in r],
        duplicate_groups=len(result['exact_duplicates'])),indent=2))
