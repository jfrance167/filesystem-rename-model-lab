"""Independent pre-core literal endpoints and coordinate oracle; no app imports."""
import copy
import itertools
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERIFY = dict.fromkeys(('real_effects', 'permissions', 'durability', 'concurrency'), 'unverified')
CONTEXT = dict(object_kind='regular_files', namespace='same_mount', resolution='complete',
               execution='assumed_success', reference_coverage='complete')

def request(bindings, refs=(), events=(), files=('F', 'G')):
    return dict(version=1, profile='ordinary_rename_v1', file_ids=list(files),
                name_ids=['A', 'B', 'C'], bindings=[dict(name_id=n, file_id=f) for n,f in bindings],
                references=[dict(reference_id=r, file_id=f) for r,f in refs],
                events=[dict(event_id='E'+str(i), op=op, source_name=s, destination_name=d)
                        for i,(op,s,d) in enumerate(events)], context=CONTEXT.copy())

def snapshot(bindings, refs, files):
    return dict(bindings=[dict(name_id=n,file_id=f) for n,f in sorted(bindings)],
                references=[dict(reference_id=r,file_id=f) for r,f in sorted(refs)],
                files=[dict(file_id=f,name_count=sum(v==f for _,v in bindings),
                            reference_count=sum(v==f for _,v in refs),
                            retention='named' if any(v==f for _,v in bindings) else
                            'reference_only' if any(v==f for _,v in refs) else 'no_declared_holders')
                       for f in sorted(files)])

def empty(status, reason, unsupported=None, trace_error=None):
    return dict(status=status,profile='ordinary_rename_v1',reason=reason,unsupported=unsupported,
                trace_error=trace_error,initial=None,steps=[],final=None,verification=VERIFY.copy())

cases=[]
def modeled(label, req, endpoints):
    refs=[(x['reference_id'],x['file_id']) for x in req['references']]
    initial=[(x['name_id'],x['file_id']) for x in req['bindings']]
    report=empty('modeled','complete')
    report['initial']=snapshot(initial,refs,req['file_ids'])
    for i,(effect,file,victim,bindings) in enumerate(endpoints):
        event=req['events'][i]
        report['steps'].append(dict(event_index=i,event_id=event['event_id'],
            source_name=event['source_name'],destination_name=event['destination_name'],
            effect=effect,file_id=file,displaced_file_id=victim,
            after=snapshot(bindings,refs,req['file_ids'])))
    report['final']=snapshot(endpoints[-1][3] if endpoints else initial,refs,req['file_ids'])
    cases.append(dict(id=label,request=req,expected=report))

modeled('baseline',request([('A','F'),('B','G')]),[])
modeled('same_name',request([('A','F')],files=('F',),events=[('rename','A','A')]),[('same_name_noop','F',None,[('A','F')])])
modeled('same_alias',request([('A','F'),('B','F')],files=('F',),events=[('rename','A','B')]),[('same_file_noop','F',None,[('A','F'),('B','F')])])
modeled('move',request([('A','F')],files=('F',),events=[('rename','A','B')]),[('moved','F',None,[('B','F')])])
modeled('move_other_alias',request([('A','F'),('C','F')],files=('F',),events=[('rename','A','B')]),[('moved','F',None,[('B','F'),('C','F')])])
modeled('replace_unheld',request([('A','F'),('B','G')],events=[('rename','A','B')]),[('replaced','F','G',[('B','F')])])
modeled('replace_ref',request([('A','F'),('B','G')],[('R','G')],[('rename','A','B')]),[('replaced','F','G',[('B','F')])])
modeled('victim_alias',request([('A','F'),('B','G'),('C','G')],events=[('rename','A','B')]),[('replaced','F','G',[('B','F'),('C','G')])])
modeled('source_alias',request([('A','F'),('B','G'),('C','F')],events=[('rename','A','B')]),[('replaced','F','G',[('B','F'),('C','F')])])
modeled('both_refs',request([('A','F'),('B','G')],[('R','G'),('S','F')],[('rename','A','B')]),[('replaced','F','G',[('B','F')])])
modeled('reference_only_initial',request([('A','F')],[('R','G')],[('rename','A','B')]),[('moved','F',None,[('B','F')])])
modeled('chain',request([('A','F'),('B','G')],[('R','G')],[('rename','A','B'),('rename','B','C')]),[('replaced','F','G',[('B','F')]),('moved','F',None,[('C','F')])])
modeled('reuse_name',request([('A','F'),('B','G'),('C','G')],[('R','F')],[('rename','A','B'),('rename','C','A')]),[('replaced','F','G',[('B','F'),('C','G')]),('moved','G',None,[('A','G'),('B','F')])])
modeled('move_back',request([('A','F')],files=('F',),events=[('rename','A','B'),('rename','B','A')]),[('moved','F',None,[('B','F')]),('moved','F',None,[('A','F')])])

def error_case(label, req, status, reason, **kw):
    cases.append(dict(id=label,request=req,expected=empty(status,reason,**kw)))

for label,events,index in [('missing',[('rename','C','B')],0),('unbound_same',[('rename','C','C')],0),('late_missing',[('rename','A','B'),('rename','A','C')],1)]:
    error_case(label,request([('A','F'),('B','G')],events=events),'invalid_trace','missing_source',trace_error=dict(event_index=index,event_id='E'+str(index),violation='source_unbound'))
for op in ('exchange','noreplace','whiteout'):
    error_case(op,request([('A','F'),('B','G')],events=[(op,'C','A')]),'unsupported','unsupported_context_or_operation',unsupported=[dict(location='events.0.op',feature=op)])
for field in CONTEXT:
    req=request([('A','F'),('B','G')]);req['context'][field]='unknown'
    error_case(field+'_unknown',req,'unsupported','unsupported_context_or_operation',unsupported=[dict(location='context.'+field,feature='unknown')])
req=request([('A','F'),('B','G')]);req['context']['namespace']='cross_mount'
error_case('cross_mount',req,'unsupported','unsupported_context_or_operation',unsupported=[dict(location='context.namespace',feature='cross_mount')])
req=request([('A','F'),('B','G')],events=[('exchange','A','B'),('rename','B','C')]);req['events'][1]['op']='invented'
error_case('unsupported_then_malformed',req,'invalid_input','invalid_value')
req=request([('A','F'),('B','G')],events=[('exchange','A','B')]);req['context']['namespace']=False
error_case('unsupported_bad_context',req,'invalid_input','invalid_shape')
req=request([('A','F'),('B','G')]);req['version']=True
error_case('bool_version',req,'invalid_input','invalid_shape')
req=request([('A','F'),('B','G')]);req['bindings'][1]['name_id']='A'
error_case('duplicate_binding',req,'invalid_input','duplicate_id')
req=request([('A','F'),('B','G')]);req['bindings'][0]['file_id']='H'
error_case('unknown_file',req,'invalid_input','unknown_id')
error_case('unheld_file',request([('A','F')]),'invalid_input','unheld_file')

# Coordinate equation: for each name independently choose its post-state binding.
# This does not use the production pop/assignment transition or production reports.
domain=[]
for vector in itertools.product((None,'F','G'),repeat=3):
    for holds in ((),('F',),('G',),('F','G')):
        if not all(f in vector or f in holds for f in ('F','G')):continue
        for s,d in itertools.product(range(3),repeat=2):
            source=vector[s];dest=vector[d]
            result=None if source is None else [
                value if s==d or source==dest else source if i==d else None if i==s else value
                for i,value in enumerate(vector)]
            domain.append(dict(before=list(vector),holds=list(holds),source=s,destination=d,after=result))
delivery=dict(help='usage: rename_lab [--help]\n\nBounded synthetic ordinary rename; real effects unverified.\nRead one UTF8 JSON document from stdin.\n',arguments='{"error":"invalid_arguments"}\n',io='{"error":"input_or_output_failure"}\n')
for name,value in [('oracles',cases),('domain',domain),('delivery',delivery)]:
    path=ROOT/'fixtures'/(name+'.json');path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(value,indent=2,ensure_ascii=True)+'\n',encoding='utf-8')
print(json.dumps(dict(full_reports=len(cases),finite_cases=len(domain),no_application_imports=True)))
