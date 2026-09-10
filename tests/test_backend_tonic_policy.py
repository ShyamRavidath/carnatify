"""Exercise the API tonic guard without booting ASR models or network services."""
import ast
from pathlib import Path
import numpy as np
import pytest

SOURCE=Path(__file__).resolve().parents[1]/'backend/main.py'


def test_backend_tonic_guard_rejects_missing_and_invalid_values():
    tree=ast.parse(SOURCE.read_text())
    guard=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_require_tonic')
    class HTTPError(Exception):
        def __init__(self,*,status_code,detail):
            self.status_code=status_code
            super().__init__(detail)
    scope={'np':np,'HTTPException':HTTPError}
    exec(compile(ast.Module(body=[guard],type_ignores=[]),str(SOURCE),'exec'),scope)
    for value in (None,0,-1,float('nan'),float('inf')):
        with pytest.raises(HTTPError,match='tonic Sa') as error:
            scope['_require_tonic'](value)
        assert error.value.status_code==422
    assert scope['_require_tonic'](146.83)==146.83


def test_backend_has_no_median_tonic_and_guards_before_separation():
    tree=ast.parse(SOURCE.read_text())
    assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
                   and n.func.attr=='median' for n in ast.walk(tree))
    routes=[n for n in tree.body if isinstance(n,ast.AsyncFunctionDef)]
    route=next(n for n in routes if any(isinstance(x,ast.Call) and isinstance(x.func,ast.Name)
                 and x.func.id=='_require_tonic' for x in ast.walk(n)))
    calls=[n for n in ast.walk(route) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)]
    assert min(n.lineno for n in calls if n.func.id=='_require_tonic') < min(
        n.lineno for n in calls if n.func.id=='_separate_vocals_sync')
