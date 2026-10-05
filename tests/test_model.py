import copy
import json
from pathlib import Path
import unittest

from rename_lab.core import evaluate
from rename_lab.jsonio import analyze_json, serialize_report

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT/'fixtures/oracles.json').read_text(encoding='utf-8'))
DOMAIN = json.loads((ROOT/'fixtures/domain.json').read_text(encoding='utf-8'))


class ModelTests(unittest.TestCase):
    def test_full_reports(self):
        for case in CASES:
            with self.subTest(case=case['id']):
                self.assertEqual(case['expected'], evaluate(case['request']))

    def test_finite_coordinate_oracle(self):
        self.assertEqual(693, len(DOMAIN))
        base = copy.deepcopy(CASES[0]['request'])
        for row in DOMAIN:
            req = copy.deepcopy(base)
            req['bindings'] = [dict(name_id='ABC'[i],file_id=f) for i,f in enumerate(row['before']) if f]
            req['references'] = [dict(reference_id='R'+str(i),file_id=f) for i,f in enumerate(row['holds'])]
            req['events'] = [dict(event_id='E',op='rename',source_name='ABC'[row['source']],destination_name='ABC'[row['destination']])]
            result = evaluate(req)
            if row['after'] is None:
                self.assertEqual('invalid_trace', result['status'])
                self.assertIsNone(result['initial'])
                self.assertEqual([], result['steps'])
            else:
                expected = [dict(name_id='ABC'[i],file_id=f) for i,f in enumerate(row['after']) if f]
                self.assertEqual(expected, result['final']['bindings'])
                self.assertEqual(req['references'], result['final']['references'])

    def test_caller_unchanged_and_fresh_reports(self):
        for case in CASES:
            request = copy.deepcopy(case['request']); original = copy.deepcopy(request)
            result = evaluate(request)
            self.assertEqual(original, request)
            result['verification']['real_effects'] = 'changed'
            if result['initial']:
                result['initial']['bindings'].clear()
            self.assertEqual(case['expected'], evaluate(request))

    def test_no_snapshot_aliasing(self):
        req = next(c['request'] for c in CASES if c['id']=='chain')
        report = evaluate(req)
        report['steps'][0]['after']['references'].clear()
        self.assertEqual([dict(reference_id='R',file_id='G')], report['final']['references'])

    def test_native_hooks_not_called(self):
        class BadString(str):
            def __hash__(self): raise AssertionError('hash hook')
            def __eq__(self, other): raise AssertionError('equality hook')
            def __len__(self): raise AssertionError('length hook')
        class BadList(list):
            def __iter__(self): raise AssertionError('iteration hook')
        class BadDict(dict):
            def __iter__(self): raise AssertionError('dict iteration hook')
        class BadInt(int):
            def __eq__(self, other): raise AssertionError('integer equality hook')
        for value in (BadDict(), None, (), 'text'):
            self.assertEqual('invalid_shape', evaluate(value)['reason'])
        for field,value in [('file_ids',BadList()),('version',BadInt(1)),('profile',BadString('ordinary_rename_v1'))]:
            req=copy.deepcopy(CASES[0]['request']);req[field]=value
            self.assertEqual('invalid_shape',evaluate(req)['reason'])
        # Insert via inherited native hash before arming the key's hooks.
        class Armed(str):
            armed=False
            def __hash__(self):
                if self.armed:raise AssertionError('armed key hash')
                return str.__hash__(self)
            def __eq__(self,other):
                if self.armed:raise AssertionError('armed key equality')
                return str.__eq__(self,other)
        key=Armed('context');req=copy.deepcopy(CASES[0]['request']);context=req.pop('context');req[key]=context;key.armed=True
        self.assertEqual('invalid_shape',evaluate(req)['reason'])

    def test_nested_shapes_and_complete_priority(self):
        for field in ('bindings','references','events'):
            req=copy.deepcopy(CASES[0]['request']);req[field]=[{}]
            self.assertEqual('invalid_shape',evaluate(req)['reason'])
        req=copy.deepcopy(CASES[0]['request']);req['context']['namespace']='unknown';req['bindings'][0]['file_id']='H'
        self.assertEqual('unknown_id',evaluate(req)['reason'])
        req=copy.deepcopy(CASES[0]['request']);req['context']['namespace']='unknown';req['context']['resolution']='unknown'
        self.assertEqual([dict(location='context.namespace',feature='unknown'),dict(location='context.resolution',feature='unknown')],evaluate(req)['unsupported'])
        req=copy.deepcopy(CASES[0]['request']);req['context'][10]=1
        self.assertEqual('invalid_shape',evaluate(req)['reason'])

    def test_id_and_bound_edges(self):
        for identity in ('', 'A'*25, '../A', 'A B', 'é', 'A\n', 'A\\B'):
            req=copy.deepcopy(CASES[0]['request']);req['file_ids'][0]=identity
            self.assertEqual('invalid_value',evaluate(req)['reason'])
        for field, value in [('file_ids',[]),('name_ids',['N'+str(i) for i in range(9)]),('events',[{}]*25),('references',[{}]*9)]:
            req=copy.deepcopy(CASES[0]['request']);req[field]=value
            self.assertEqual('invalid_value',evaluate(req)['reason'])

    def test_json_envelopes(self):
        rows=[(b'\xff','invalid_utf8'),(b'\xef\xbb\xbf{}','invalid_utf8'),(b' '*32769,'input_size'),
              (b'{"x":1,"x":2}','json_duplicate_key'),(b'NaN','json_constant'),
              (b'1e999','json_constant'),(b'11111111111','json_integer'),(b'['*7+b']'*7,'json_depth'),
              (b'{} trailing','invalid_json'),(b'', 'invalid_json'),(b'"[[[[[[[[["','invalid_shape')]
        for raw,reason in rows:
            with self.subTest(reason=reason):self.assertEqual(reason,analyze_json(raw)['reason'])
        for case in CASES:
            self.assertEqual(case['expected'], analyze_json(json.dumps(case['request']).encode()))

    def test_output_cap_seam(self):
        from unittest.mock import patch
        with patch('rename_lab.jsonio.MAX_OUTPUT_BYTES',1):
            with self.assertRaises(ValueError):serialize_report(evaluate(CASES[0]['request']))


if __name__=='__main__':unittest.main()
