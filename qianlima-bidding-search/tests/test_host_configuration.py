"""Host-neutral private handoff: synthetic identities, no network or real settings."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from test_account_flow import account, FakeAPI, LoginAPI, inputs


class HandoffTests(unittest.TestCase):
    def test_new_and_existing_user_private_handoff_and_fresh_process(self):
        for new in (True, False):
            with self.subTest(new=new):
                reader, writer = os.pipe()
                try:
                    api = LoginAPI(new=new)
                    data = inputs(action='verify', smsCode='1234')
                    with patch.object(account, 'AccountAPI', return_value=api), \
                         patch.object(account, 'CodexConfig') as codex, \
                         patch.object(sys, 'argv', ['account','register','--input-stdin','--credential-fd',str(writer)]), \
                         patch.object(sys, 'stdin', io.StringIO(json.dumps(data))), \
                         patch.object(sys, 'stdout', io.StringIO()) as output:
                        # fstat(stdout) uses actual descriptor 1, not StringIO.
                        self.assertEqual(account.main(), 0)
                    codex.assert_not_called()
                    result = json.loads(output.getvalue())
                    self.assertEqual(result['status'], 'credential_ready')
                    self.assertFalse(result['configuration_written'])
                    self.assertFalse(result['current_environment_loaded'])
                    secret = os.read(reader, 512).decode()
                    self.assertEqual(secret, api.secret)
                    for value in (secret, api.token, data['smsCode']):
                        self.assertNotIn(value, output.getvalue())
                    env = dict(os.environ, QIANLIMA_API_KEY=secret)
                    child = subprocess.run([sys.executable, '-c',
                        'import os; assert os.environ["QIANLIMA_API_KEY"].startswith("qlm_"); print("ready")'],
                        env=env, capture_output=True, text=True, check=True)
                    self.assertEqual(child.stdout.strip(), 'ready')
                    self.assertEqual(api.calls[-1][1], '/api/auth/logout')
                finally:
                    os.close(reader); os.close(writer)

    def test_prepare_and_send_never_create_host_configuration(self):
        for argv, data, expected in [(['prepare'],None,'prepared'),
                                     (['register','--input-stdin'],inputs(),'sms_sent')]:
            with patch.object(account, 'AccountAPI', return_value=FakeAPI()), \
                 patch.object(account, 'CodexConfig') as codex, \
                 patch.object(sys, 'argv', ['account',*argv]), \
                 patch.object(sys, 'stdin', io.StringIO(json.dumps(data))), \
                 patch.object(sys, 'stdout', io.StringIO()) as output:
                self.assertEqual(account.main(),0)
            codex.assert_not_called()
            self.assertEqual(json.loads(output.getvalue())['status'],expected)

    def test_explicit_invalid_private_receiver_blocks_login(self):
        api = LoginAPI()
        with patch.object(account,'AccountAPI',return_value=api), \
             patch.object(sys,'argv',['account','register','--input-stdin','--credential-fd','1']), \
             patch.object(sys,'stdin',io.StringIO(json.dumps(inputs(action='verify',smsCode='1234')))), \
             patch.object(sys,'stdout',io.StringIO()) as out:
            self.assertEqual(account.main(),1)
        self.assertEqual(json.loads(out.getvalue())['status'],'private_pipe_required')
        self.assertEqual(api.calls,[])

    def test_visible_descriptors_and_regular_file_rejected(self):
        with tempfile.TemporaryFile() as file:
            for fd in (None,1,2,file.fileno()):
                with self.subTest(fd=fd), self.assertRaises(account.AccountError):
                    account.PrivateHandoff(fd).preflight()

    def test_closed_receiver_failure_logs_out_without_claiming_save(self):
        reader, writer = os.pipe(); os.close(reader)
        try:
            api=LoginAPI()
            result=account.register(inputs(action='verify',smsCode='1234'),api,account.PrivateHandoff(writer))
            self.assertEqual(result['status'],'credential_handoff_failed')
            self.assertFalse(result['configuration_written'])
            self.assertTrue(result['logout_confirmed'])
            self.assertNotIn(api.secret,json.dumps(result))
        finally:
            os.close(writer)

    def test_bad_sms_never_hands_off_or_writes(self):
        reader,writer=os.pipe()
        try:
            api=LoginAPI(); api.fail['/api/auth/login']=account.AccountError('sms_invalid')
            handoff=account.PrivateHandoff(writer)
            result=account.register(inputs(action='verify',smsCode='1234'),api,handoff)
            self.assertEqual(result['status'],'sms_invalid')
            self.assertFalse(handoff.delivered)
            self.assertFalse(handoff.written)
        finally:
            os.close(reader);os.close(writer)

    def test_subprocess_receiver_saves_to_existing_platform_fixture_and_reloads(self):
        # This file represents a platform's existing store, not a Skill store.
        with tempfile.TemporaryDirectory() as directory:
            settings = Path(directory)/'platform-settings.json'
            settings.write_text(json.dumps({'unrelated': 'preserved'}))
            reader, writer = os.pipe()
            try:
                child_code = ('import sys; sys.path.insert(0,sys.argv[1]); '
                    'from test_account_flow import account,LoginAPI; '
                    'account.AccountAPI=LoginAPI; '
                    'sys.argv=["account","register","--input-stdin","--credential-fd",sys.argv[2]]; '
                    'raise SystemExit(account.main())')
                child = subprocess.Popen([sys.executable,'-c',child_code,str(Path(__file__).parent),str(writer)],
                    stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                    text=True,pass_fds=(writer,))
                os.close(writer);writer=None
                stdout,stderr=child.communicate(json.dumps(inputs(action='verify',smsCode='1234')),timeout=10)
                self.assertEqual(child.returncode,0,stderr)
                self.assertEqual(json.loads(stdout)['status'],'credential_ready')
                key=os.read(reader,512).decode()
                self.assertTrue(account.valid_key(key))
                self.assertNotIn(key,stdout+stderr)
                # Receiver uses its known platform API; no Key crosses tool-visible output.
                values=json.loads(settings.read_text());values['QIANLIMA_API_KEY']=key
                settings.write_text(json.dumps(values))
                loaded=json.loads(settings.read_text())
                self.assertEqual(loaded['QIANLIMA_API_KEY'],key)
                self.assertEqual(loaded['unrelated'],'preserved')
                check=subprocess.run([sys.executable,'-c',
                    'import json,sys; v=json.load(open(sys.argv[1])); assert v["QIANLIMA_API_KEY"].startswith("qlm_"); print("readable")',str(settings)],
                    capture_output=True,text=True,check=True)
                self.assertEqual(check.stdout.strip(),'readable')
                self.assertNotIn(key,check.stdout+check.stderr)
            finally:
                os.close(reader)
                if writer is not None:os.close(writer)
