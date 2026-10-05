"""Measure maximum-shape control and conservative incompatible-width envelope."""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from rename_lab.core import evaluate
from rename_lab.jsonio import serialize_report

long=lambda prefix:prefix+'X'*23
files=[long(c) for c in 'FGHI']
names=[long(c) for c in 'ABCDEFGH']
req=dict(version=1,profile='ordinary_rename_v1',file_ids=files,name_ids=names,
         bindings=[dict(name_id=n,file_id=files[i%4]) for i,n in enumerate(names)],
         references=[dict(reference_id=long(c),file_id=files[i%4]) for i,c in enumerate('RSTUVWYZ')],
         events=[dict(event_id='E'+str(i)+'X'*(23-len(str(i))),op='rename',source_name=names[0],destination_name=names[0]) for i in range(24)],
         context=dict(object_kind='regular_files',namespace='same_mount',resolution='complete',execution='assumed_success',reference_coverage='complete'))
report=evaluate(req)
if report['status']!='modeled':raise RuntimeError('stress not admitted')
# Serializer width proof uses declared counts and independent maximal rows, no app limit constant.
encode=lambda value:json.dumps(value,ensure_ascii=True,sort_keys=True,separators=(',',':')).encode()
snapshot=dict(bindings=[dict(name_id='X'*24,file_id='X'*24)]*8,
              references=[dict(reference_id='X'*24,file_id='X'*24)]*8,
              files=[dict(file_id='X'*24,name_count=8,reference_count=8,retention='no_declared_holders')]*4)
step=dict(event_index=23,event_id='X'*24,source_name='X'*24,destination_name='X'*24,
          effect='same_name_noop',file_id='X'*24,displaced_file_id='X'*24,after=snapshot)
envelope=dict(report);envelope['initial']=snapshot;envelope['final']=snapshot;envelope['steps']=[step]*24
upper=len(encode(envelope))+1
unsupported=dict(report,status='unsupported',reason='unsupported_context_or_operation',initial=None,final=None,steps=[])
unsupported['unsupported']=[dict(location='context.reference_coverage',feature='assumed_success')]*5+[
    dict(location='events.23.op',feature='noreplace')]*24
unsupported_upper=len(encode(unsupported))+1
if not (len(encode(snapshot))<3500 and len(encode(step))<4000 and upper<100500<262144):
    raise RuntimeError('conservative width claim failed')
print(json.dumps(dict(input_bytes=len(encode(req)),output_bytes=len(serialize_report(report)),snapshot_width=len(encode(snapshot)),step_width=len(encode(step)),
                      conservative_serializer_envelope=upper,unsupported_envelope=unsupported_upper,coarse_bound=100500,output_cap=262144,exact_maximum=False,natural_overflow=False),indent=2))
