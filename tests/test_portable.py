import importlib.util
import io
import ipaddress
import json
import os
import subprocess
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
from portable import PortableMoodle, private_write, instance_lock
from build import extract_zip, extract_tar


class PortableTests(unittest.TestCase):
    def test_child_processes_cannot_consume_desktop_control_input(self):
        with tempfile.TemporaryDirectory() as folder:
            application = PortableMoodle(folder)
            application.config = {'database_password': 'fictional'}
            with patch('portable.subprocess.run') as run:
                application.run(['fictional-tool'])
            self.assertEqual(run.call_args.kwargs['stdin'], subprocess.DEVNULL)
            self.assertEqual(run.call_args.kwargs['env']['PHPRC'], str(application.root / 'app' / 'php.ini'))

    def test_mcp_request_policy_excludes_only_the_single_loopback_address(self):
        networks = [ipaddress.ip_network(line) for line in (ROOT / 'src' / 'mcp-blocked-hosts.txt').read_text().splitlines()]
        for value in ['0.0.0.0', '10.0.0.1', '127.0.0.0', '127.0.0.2', '127.255.255.255', '192.168.1.1',
                      '8.8.8.8', '255.255.255.255', '::1', '2001:db8::1']:
            address = ipaddress.ip_address(value)
            self.assertTrue(any(address in network for network in networks if network.version == address.version))
        self.assertFalse(any(ipaddress.ip_address('127.0.0.1') in network for network in networks if network.version == 4))

    def test_zip_rejects_parent_traversal(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive = root / 'evil.zip'
            with zipfile.ZipFile(archive, 'w') as output:
                output.writestr('../escaped', 'bad')
            with self.assertRaises(ValueError):
                extract_zip(archive, root / 'destination')
            self.assertFalse((root / 'escaped').exists())

    def test_tar_rejects_escaping_symlink(self):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w') as archive:
            link = tarfile.TarInfo('link')
            link.type = tarfile.SYMTYPE
            link.linkname = '../outside'
            archive.addfile(link)
        stream.seek(0)
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(tarfile.FilterError):
                extract_tar(stream, Path(folder))

    def test_private_write_replaces_complete_content(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / 'private' / 'token.txt'
            private_write(destination, 'first')
            private_write(destination, 'second')
            self.assertEqual(destination.read_text(), 'second')
            self.assertFalse(destination.with_suffix('.txt.tmp').exists())
            if os.name != 'nt':
                self.assertEqual(destination.stat().st_mode & 0o777, 0o600)

    def test_instance_lock_refuses_second_writer(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'lock'
            with instance_lock(path):
                with self.assertRaises(OSError):
                    with instance_lock(path):
                        self.fail('Second writer acquired lock')

    def test_generated_client_configs_do_not_contain_token(self):
        with tempfile.TemporaryDirectory() as folder:
            application = PortableMoodle(folder)
            application.config = {'plugin_enabled': True}
            application.url = 'http://127.0.0.1:8787'
            private_write(application.connection / 'token.txt', 'fictional-secret')
            application.write_client_files()
            for path in application.connection.iterdir():
                if path.name != 'token.txt':
                    self.assertNotIn('fictional-secret', path.read_text())
            opencode = json.loads((application.connection / 'opencode.json').read_text())
            self.assertFalse(opencode['mcp']['moodlia']['oauth'])

    def test_core_mode_has_no_mcp_configuration(self):
        with tempfile.TemporaryDirectory() as folder:
            application = PortableMoodle(folder)
            application.config = {'plugin_enabled': False}
            application.url = 'http://127.0.0.1:8787'
            application.write_client_files()
            self.assertFalse((application.connection / 'codex.toml').exists())
            self.assertTrue((application.connection / 'load-token.ps1').exists())

    def test_snapshot_failure_preserves_existing_state(self):
        with tempfile.TemporaryDirectory() as folder:
            application = PortableMoodle(folder)
            application.data.mkdir()
            application.config = {'database_port': 9999}
            application.database_started = True
            private_write(application.data / 'config.json', 'original')
            with patch.object(application, 'run', side_effect=OSError('disk full')):
                with self.assertRaises(OSError):
                    application.snapshot()
            self.assertEqual((application.data / 'config.json').read_text(), 'original')
            self.assertFalse(list((application.data / 'backups').glob('*/snapshot.json')))

    def test_existing_workspace_cannot_change_moodle_version(self):
        with tempfile.TemporaryDirectory() as folder:
            application = PortableMoodle(folder)
            application.php.parent.mkdir(parents=True)
            application.php.touch()
            application.pg.mkdir(parents=True)
            (application.pg / ('initdb' + application.suffix)).touch()
            original = {'schema': 1, 'moodle_version': '4.5.15', 'plugin_enabled': True, 'password': 'fictional'}
            private_write(application.data / 'config.json', json.dumps(original))
            with self.assertRaisesRegex(RuntimeError, 'already uses Moodle'):
                application.prepare('5.3.0')
            self.assertEqual(json.loads((application.data / 'config.json').read_text()), original)


if __name__ == '__main__':
    unittest.main()
