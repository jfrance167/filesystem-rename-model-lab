"""Repeat owned lab checks and frozen hashes, saving fresh process receipts."""
import hashlib
import json
from pathlib import Path
import subprocess  # nosec B404 - fixed local test/SAST child commands only
import sys
import uuid

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'research'/'runs'/uuid.uuid4().hex
OUTPUT.mkdir(parents=True, exist_ok=False)
freeze=json.loads((ROOT/'research/oracle-freeze.json').read_text(encoding='utf-8-sig'))
for row in freeze['files']:
    if hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()!=row['sha256']:
        raise RuntimeError('frozen contract/oracle changed')
checks=[('normal',['-m','unittest','discover','-s','tests','-v']),
        ('optimized',['-O','-m','unittest','discover','-s','tests','-v']),
        ('mutations',['tools/check_mutations.py']),('mutations-optimized',['-O','tools/check_mutations.py']),
        ('measurement',['tools/measure_report.py']),('measurement-optimized',['-O','tools/measure_report.py']),
        ('bandit',['-m','bandit','-r','rename_lab','tools','-f','json'])]
results=[]
for label,args in checks:
    # sys.executable is this installed runtime; args are fixed owned checks.
    run=subprocess.run([sys.executable]+args,cwd=ROOT,capture_output=True,timeout=60)  # nosec B603
    for suffix,data in [('stdout',run.stdout),('stderr',run.stderr)]:
        (OUTPUT/('verified-'+label+'.'+suffix)).write_bytes(data)
    results.append(dict(check=label,exit=run.returncode))
    if run.returncode:break
(OUTPUT/'check-status.json').write_text(json.dumps(dict(frozen_hashes_matched=len(freeze['files']),checks=results,passed=all(r['exit']==0 for r in results) and len(results)==len(checks)),indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(output_directory=str(OUTPUT.relative_to(ROOT)),checks=results)))
raise SystemExit(0 if len(results)==len(checks) and all(r['exit']==0 for r in results) else 1)
