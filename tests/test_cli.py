import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from rename_lab import __main__ as cli
from test_model import CASES, ROOT

DELIVERY=json.loads((ROOT/'fixtures/delivery.json').read_text(encoding='utf-8'))


class CLITests(unittest.TestCase):
    def test_physical_json_envelopes(self):
        prefix=[sys.executable]+(['-O'] if not __debug__ else [])
        rows=[(b'\xff','invalid_utf8'),(b'\xef\xbb\xbf{}','invalid_utf8'),(b' '*32769,'input_size'),
              (b'{"x":1,"x":2}','json_duplicate_key'),(b'NaN','json_constant'),(b'1e999','json_constant'),
              (b'11111111111','json_integer'),(b'['*7+b']'*7,'json_depth'),(b'{} trailing','invalid_json'),
              (b'','invalid_json'),(b'"[[[[[[[[["','invalid_shape')]
        for raw,reason in rows:
            run=subprocess.run(prefix+['-m','rename_lab'],input=raw,cwd=ROOT,capture_output=True,timeout=10)
            self.assertEqual(2,run.returncode)
            self.assertEqual(reason,json.loads(run.stdout)['reason']);self.assertEqual(b'',run.stderr)
        raw=json.dumps(CASES[0]['request']).encode();raw+=b' '*(32768-len(raw))
        run=subprocess.run(prefix+['-m','rename_lab'],input=raw,cwd=ROOT,capture_output=True,timeout=10)
        self.assertEqual(0,run.returncode);self.assertEqual(CASES[0]['expected'],json.loads(run.stdout))

    def test_physical_reports_and_delivery_bytes(self):
        prefix=[sys.executable]+(['-O'] if not __debug__ else [])
        for case in CASES:
            run=subprocess.run(prefix+['-m','rename_lab'],input=json.dumps(case['request']).encode(),
                cwd=ROOT,capture_output=True,timeout=10)
            self.assertEqual(0 if case['expected']['status'] in ('modeled','unsupported') else 2,run.returncode)
            expected=(json.dumps(case['expected'],sort_keys=True,separators=(',',':'))+'\n').encode()
            self.assertEqual(expected,run.stdout)
            self.assertEqual(b'',run.stderr)
        for args,code,out,err in [(['--help'],0,DELIVERY['help'],''),(['-h'],0,DELIVERY['help'],''),
                                  (['invalid'],2,'',DELIVERY['arguments']),(['--help','x'],2,'',DELIVERY['arguments'])]:
            run=subprocess.run(prefix+['-m','rename_lab']+args,capture_output=True,cwd=ROOT,timeout=10)
            self.assertEqual((code,out.encode(),err.encode()),(run.returncode,run.stdout,run.stderr))

    def test_physical_closed_streams_and_os_pipes(self):
        prefix=[sys.executable]+(['-O'] if not __debug__ else [])
        setups=[('sys.stdout.close()',[]),('sys.stdout.close()', ['--help']),
                ('sys.stderr.close()',['bad']),('sys.stdout.close();sys.stderr.close()',[]),
                ('os.close(1)',[]),('os.close(1);os.close(2)',[])]
        for setup,args in setups:
            script='import sys,os;from rename_lab.__main__ import main;sys.argv=["rename_lab"]+'+repr(args)+';'+setup+';raise SystemExit(main())'
            run=subprocess.run(prefix+['-c',script],input=json.dumps(CASES[0]['request']).encode(),
                               capture_output=True,cwd=ROOT,timeout=10)
            self.assertEqual(3,run.returncode,(setup,run.stderr))

    def test_checked_write_fault_seams(self):
        class IntSubclass(int):pass
        class Sink:
            def __init__(self,count=None,write_error=None,flush_error=None):
                self.buffer=self;self.count=count;self.write_error=write_error;self.flush_error=flush_error
            def write(self,text):
                if self.write_error:raise self.write_error
                if self.count=='float_full':return float(len(text))
                if self.count=='subclass_full':return IntSubclass(len(text))
                return self.count if self.count!='full' else len(text)
            def flush(self):
                if self.flush_error:raise self.flush_error
        sinks=[None]+[Sink(count=v) for v in (None,True,0,1.0,IntSubclass(1),'float_full','subclass_full')]+[
            Sink(write_error=OSError()),Sink(write_error=ValueError()),Sink(count='full',flush_error=OSError()),
            Sink(count='full',flush_error=ValueError())]
        raw=json.dumps(CASES[0]['request']).encode()
        for kind in ('report','help','arguments'):
            for sink in sinks:
                stdout=sink if kind!='arguments' else io.StringIO()
                stderr=sink if kind=='arguments' else io.StringIO()
                stdin=io.TextIOWrapper(io.BytesIO(raw))
                args=['rename_lab']+(['--help'] if kind=='help' else ['bad'] if kind=='arguments' else [])
                # Patch both public sinks: IO handler deliberately detaches both.
                with patch.object(sys,'stdout',stdout),patch.object(sys,'stderr',stderr),patch.object(sys,'stdin',stdin),patch.object(sys,'argv',args):
                    self.assertEqual(3,cli.main())
                    self.assertIsNone(sys.stdout);self.assertIsNone(sys.stderr)

    def test_input_fault_seams(self):
        class BadInput:
            buffer=None
            def read(self,n):raise OSError('input')
        bad=BadInput();bad.buffer=bad
        for stream in (None,bad):
            with patch.object(sys,'stdin',stream),patch.object(sys,'stdout',io.StringIO()),patch.object(sys,'stderr',io.StringIO()),patch.object(sys,'argv',['rename_lab']):
                self.assertEqual(3,cli.main())


if __name__=='__main__':unittest.main()
