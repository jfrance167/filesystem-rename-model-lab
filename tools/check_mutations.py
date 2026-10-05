"""Six fixed owned-source in-memory mutants; never accepts external code."""
import hashlib
import io
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'rename_lab/core.py'
original=SOURCE.read_bytes()
text=original.decode('utf-8')
cases=json.loads((ROOT/'fixtures/oracles.json').read_text(encoding='utf-8'))
mutants=[
 ('alias_remove',"    if victim == file:\n        return 'same_file_noop', file, None", "    if victim == file:\n        bindings.pop(source)\n        return 'same_file_noop', file, None"),
 ('retarget_references',"    bindings.pop(source)\n    bindings[destination] = file", "    bindings.pop(source)\n    for key in references:\n        if references[key] == victim:\n            references[key] = file\n    bindings[destination] = file"),
 ('erase_victim_aliases',"    bindings.pop(source)\n    bindings[destination] = file", "    bindings.pop(source)\n    for key in list(bindings):\n        if bindings[key] == victim:\n            bindings.pop(key)\n    bindings[destination] = file"),
 ('preserve_source',"    bindings.pop(source)\n    bindings[destination] = file", "    bindings[destination] = file"),
 ('publish_prefix',"            return _empty('invalid_trace', 'missing_source', trace_error=dict(", "            failure = _empty('invalid_trace', 'missing_source', trace_error=dict("),
 ('early_unsupported',"        _validate(document)", "        if _unsupported(document):\n            return _empty('unsupported', 'unsupported_context_or_operation', unsupported=_unsupported(document))\n        _validate(document)"),
]
results=[]
for name,before,after in mutants:
    if text.count(before)!=1:raise RuntimeError('mutation anchor not unique')
    modified=text.replace(before,after,1)
    if name=='publish_prefix':
        marker="                event_index=i, event_id=event['event_id'], violation='source_unbound'))"
        modified=modified.replace(marker,marker+"\n            failure['steps'] = report['steps']\n            return failure",1)
    namespace={}
    # Trusted task-owned source + fixed replacements only, no input-selected code.
    exec(compile(modified, str(SOURCE), 'exec'),namespace)  # nosec B102
    suite=unittest.TestSuite()
    for case in cases:
        def check(case=case):
            unittest.TestCase().assertEqual(case['expected'],namespace['evaluate'](case['request']))
        suite.addTest(unittest.FunctionTestCase(check,description=case['id']))
    stream=io.StringIO();result=unittest.TextTestRunner(stream=stream).run(suite)
    results.append(dict(mutant=name,assertion_failures=len(result.failures),errors=len(result.errors),raw=stream.getvalue()))
    if not result.failures or result.errors:raise RuntimeError('mutant did not meet assertion-only requirement')
if SOURCE.read_bytes()!=original:raise RuntimeError('production source changed')
print(json.dumps(dict(results=results,source_unchanged=True,source_sha256=hashlib.sha256(original).hexdigest()),indent=2))
