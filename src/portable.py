"""Local Moodle lifecycle manager; frozen into a native launcher for each OS."""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import time
import threading
import urllib.parse
import urllib.request
import webbrowser
from archives import extract_source
from local_proxy import create_proxy


def bundle_root():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(os.environ.get('MOODLIA_BUNDLE_ROOT', Path(__file__).resolve().parents[1]))


def private_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_suffix(path.suffix + '.tmp')
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, 'w', encoding='utf-8', newline='\n') as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    if os.name != 'nt':
        path.chmod(0o600)


def free_port():
    with socket.socket() as server:
        server.bind(('127.0.0.1', 0))
        return server.getsockname()[1]


def check_port(port):
    with socket.socket() as server:
        if os.name == 'nt':
            server.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            # Match the proxy's restart policy when closed connections remain in TIME_WAIT.
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('127.0.0.1', port))


@contextlib.contextmanager
def instance_lock(path):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open('a+b') as stream:
        if os.name == 'nt':
            import msvcrt
            stream.write(b'0')
            stream.flush()
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            if os.name == 'nt':
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)


class PortableMoodle:
    def __init__(self, root, workspace=None):
        self.root = Path(root).resolve()
        self.workspace = Path(workspace).resolve() if workspace else self.root
        self.data = self.workspace / 'data'
        self.connection = self.workspace / 'connection'
        self.moodle = self.root / 'app' / 'moodle'
        self.suffix = '.exe' if os.name == 'nt' else ''
        self.php = self.root / 'runtime' / 'php' / ('php' + self.suffix)
        self.pg = self.root / 'runtime' / 'postgres' / 'bin'
        self.php_process = None
        self.php_workers = []
        self.proxy = None
        self.database_started = False
        self.logs = []
        self.config = None
        self.stop_requested = threading.Event()

    def run(self, arguments, **kwargs):
        environment = os.environ.copy()
        environment.update({'PGPASSWORD': self.config['database_password'],
                            'MOODLIA_PRIVATE_CONFIG': str(self.data / 'config.json'),
                            'MOODLIA_RUNTIME_ROOT': str(self.root),
                            'OPENSSL_CONF': str(self.root / 'app' / 'openssl.cnf'),
                            'PHPRC': str(self.root / 'app' / 'php.ini'),
                            'MOODLIA_PHP_EXT': str(self.root / 'runtime' / 'php' / 'ext')})
        return subprocess.run([str(item) for item in arguments], cwd=self.root,
                              env=environment, stdin=subprocess.DEVNULL, check=True, **kwargs)

    def php_args(self):
        arguments = [self.php, '-c', self.root / 'app' / 'php.ini']
        if os.name == 'nt':
            arguments += ['-d', 'extension_dir=' + str(self.php.parent / 'ext')]
        return arguments

    def selected_plugins(self, version, selected):
        catalog_file = self.root / 'plugins.json'
        catalog = json.loads(catalog_file.read_text(encoding='utf-8')) if catalog_file.exists() else {}
        branch = '.'.join(version.split('.')[:2])
        if not isinstance(selected, list) or any(not isinstance(item, str) for item in selected):
            raise RuntimeError('Optional plugins must be a list of component names.')
        if len(set(selected)) != len(selected):
            raise RuntimeError('An optional plugin was selected more than once.')
        for component in selected:
            if component not in catalog or branch not in catalog[component]['versions']:
                raise RuntimeError('The selected plugin is unavailable for Moodle ' + version + ': ' + component)
        return {component: catalog[component] for component in selected}

    def copy_plugins(self, staged, selected, version):
        public = staged / 'public' if (staged / 'public' / 'index.php').is_file() else staged
        branch = '.'.join(version.split('.')[:2])
        for component, plugin in self.selected_plugins(version, selected).items():
            destination = (public / plugin['path']).resolve()
            if not destination.is_relative_to(public.resolve()):
                raise RuntimeError('Optional plugin path escapes the Moodle site.')
            source = self.root / 'app' / 'plugins' / component / branch
            if not (source / 'version.php').is_file():
                raise RuntimeError('Bundled optional plugin is missing: ' + component)
            shutil.copytree(source, destination)

    def prepare(self, requested_version=None, plugin_enabled=True, optional_plugins=None):
        if not self.php.is_file() or not (self.pg / ('initdb' + self.suffix)).is_file():
            raise RuntimeError('Bundled PHP/PostgreSQL missing. Use a built native package, or run scripts/build.py.')
        private_directories = [self.data, self.connection, self.workspace / 'exports', self.data / 'logs', self.data / 'moodledata']
        for directory in private_directories:
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        if os.name == 'nt':
            # Restrict credentials and database files to the current Windows user.
            identity = subprocess.check_output(['whoami'], text=True).strip()
            # Python's mode=0700 can create protected child ACLs owned by Administrators
            # in elevated sessions. Grant the user directly on every managed directory
            # so PostgreSQL's restricted child can create its log file there.
            for directory in private_directories:
                subprocess.run(['icacls', str(directory), '/inheritance:r', '/grant:r',
                                identity + ':(OI)(CI)F'], check=True, capture_output=True)
        config_path = self.data / 'config.json'
        if config_path.exists():
            self.config = json.loads(config_path.read_text(encoding='utf-8'))
            if self.config.get('schema') != 1:
                raise RuntimeError('Unsupported workspace format. No migration was attempted.')
            if requested_version and requested_version != self.config['moodle_version']:
                raise RuntimeError('This workspace already uses Moodle ' + self.config['moodle_version'] + '. Use a new workspace to select another version.')
            if optional_plugins is not None and sorted(optional_plugins) != sorted(self.config.get('optional_plugins', [])):
                raise RuntimeError('This workspace already has its plugin selection. Manage changes inside Moodle.')
        else:
            versions = json.loads((self.root / 'versions.json').read_text(encoding='utf-8'))
            if requested_version is None:
                print('Available Moodle versions: ' + ', '.join(versions), flush=True)
                requested_version = input('Moodle version [' + versions[0] + ']: ').strip() or versions[0]
            if requested_version not in versions:
                raise RuntimeError('The selected Moodle version is not included in this package.')
            self.selected_plugins(requested_version, optional_plugins or [])
            self.config = {'schema': 1, 'http_port': 8787, 'database_port': free_port(),
                           'database_password': secrets.token_urlsafe(32),
                           'username': 'teacher', 'password': 'Aa9!' + secrets.token_urlsafe(24),
                           'moodle_version': requested_version, 'plugin_enabled': plugin_enabled,
                           'optional_plugins': optional_plugins or []}
            self.config['database_major'] = 17 if requested_version.startswith('5.3.') else 16
            private_write(config_path, json.dumps(self.config, indent=2) + '\n')
        self.database_major = self.config.get('database_major', 16)
        self.pg = self.root / 'runtime' / ('postgres17' if self.database_major == 17 else 'postgres') / 'bin'
        self.moodle = self.workspace / 'site'
        if not (self.moodle / '.portable-ready').is_file():
            if self.moodle.exists():
                raise RuntimeError('Incomplete site preparation. Preserve the workspace and inspect it before retrying.')
            staged = self.workspace / 'site.preparing'
            if staged.exists():
                raise RuntimeError('An incomplete site copy exists at site.preparing. Preserve it before retrying.')
            extract_source(self.root / 'app' / 'versions' / (self.config['moodle_version'] + '.zip'), staged)
            public = staged / 'public' if (staged / 'public' / 'index.php').is_file() else staged
            if self.config['plugin_enabled']:
                shutil.copytree(self.root / 'app' / 'plugin', public / 'local' / 'moodlia')
            self.copy_plugins(staged, self.config.get('optional_plugins', []), self.config['moodle_version'])
            shutil.copyfile(self.root / 'app' / 'config.php', staged / 'config.php')
            (staged / '.portable-ready').touch()
            staged.rename(self.moodle)
        self.docroot = self.moodle / 'public' if (self.moodle / 'public' / 'index.php').is_file() else self.moodle
        check_port(self.config['http_port'])
        check_port(self.config['database_port'])
        self.run(self.php_args() + [self.root / 'app' / 'check.php'])
        self.url = 'http://127.0.0.1:' + str(self.config['http_port'])

    def start_database(self):
        cluster = self.data / 'postgres'
        if (cluster / 'PG_VERSION').exists() and (cluster / 'PG_VERSION').read_text().strip() != str(self.database_major):
            raise RuntimeError('PostgreSQL major version mismatch. Preserve this workspace and migrate it explicitly.')
        password_file = self.data / '.pg-password'
        if not (cluster / 'PG_VERSION').exists():
            if cluster.exists() and any(cluster.iterdir()):
                raise RuntimeError('Incomplete database initialization. Preserve data/ and inspect logs before retrying.')
            private_write(password_file, self.config['database_password'] + '\n')
            try:
                self.run([self.pg / ('initdb' + self.suffix), '-D', cluster, '-U', 'moodlia',
                          '--pwfile', password_file, '--auth=scram-sha-256', '--encoding=UTF8', '--locale=C'])
            finally:
                password_file.unlink(missing_ok=True)
        options = f"-h 127.0.0.1 -p {self.config['database_port']}"
        if os.name != 'nt':
            options += " -k ''"
        self.run([self.pg / ('pg_ctl' + self.suffix), '-D', cluster, '-l', self.data / 'logs' / 'postgres.log',
                  '-o', options, '-w', 'start'])
        self.database_started = True
        self.run(self.php_args() + [self.root / 'app' / 'database.php'])

    def install(self):
        fingerprint = hashlib.sha256((self.root / 'runtime-manifest.json').read_bytes()).hexdigest()
        installed = (self.data / 'installed.json').exists()
        if installed and self.config.get('runtime_fingerprint') != fingerprint:
            self.snapshot()
        if not (self.data / 'installed.json').exists():
            print('Preparing Moodle. First launch can take several minutes...', flush=True)
            with (self.data / 'logs' / 'install.log').open('a', encoding='utf-8') as log:
                self.run(self.php_args() + [self.root / 'app' / 'install.php', self.moodle], stdout=log, stderr=log)
        with (self.data / 'logs' / 'bootstrap.log').open('a', encoding='utf-8') as log:
            self.run(self.php_args() + [self.root / 'app' / 'bootstrap.php', self.moodle], stdout=log, stderr=log)
        token = (self.connection / 'token.txt').read_text(encoding='utf-8').strip()
        if not (self.connection / 'credentials.txt').exists():
            private_write(self.connection / 'credentials.txt',
                      f'URL: {self.url}\nUsername: teacher\nPassword: {self.config["password"]}\n'
                      'This account is the local Moodle administrator.\n')
        private_write(self.connection / 'moodle.json', json.dumps({
            'url': self.url, 'mcp_url': self.url + '/local/moodlia/mcp.php' if self.config['plugin_enabled'] else None,
            'username': 'teacher', 'token_file': 'token.txt'}, indent=2) + '\n')
        self.write_client_files()
        self.pending_fingerprint = fingerprint

    def snapshot(self):
        print('Creating a recovery snapshot before updating the runtime...', flush=True)
        backups = self.data / 'backups'
        backups.mkdir(mode=0o700, exist_ok=True)
        name = time.strftime('%Y%m%d-%H%M%S') + '-' + secrets.token_hex(4)
        temporary = backups / (name + '.preparing')
        temporary.mkdir(mode=0o700)
        # A cleanly stopped physical cluster is copied before any new Moodle code runs.
        self.stop_database()
        for source, destination in [(self.data / 'postgres', 'postgres'), (self.moodle, 'site'), (self.data / 'moodledata', 'moodledata'),
                                    (self.connection, 'connection')]:
            shutil.copytree(source, temporary / destination)
        shutil.copy2(self.data / 'config.json', temporary / 'config.json')
        private_write(temporary / 'snapshot.json', json.dumps({
            'schema': 1, 'moodle_version': self.config['moodle_version'],
            'database_major': self.database_major, 'created_at': time.time(),
            'previous_runtime': self.config.get('runtime_fingerprint')}, indent=2) + '\n')
        temporary.rename(backups / name)
        self.start_database()

    def commit_runtime(self):
        self.config['runtime_fingerprint'] = self.pending_fingerprint
        private_write(self.data / 'config.json', json.dumps(self.config, indent=2) + '\n')

    def write_client_files(self):
        endpoint = self.url + '/local/moodlia/mcp.php'
        if self.config['plugin_enabled']:
            private_write(self.connection / 'codex.toml',
                      '[mcp_servers.moodlia]\nurl = "' + endpoint + '"\nbearer_token_env_var = "MOODLE_REST_TOKEN"\n')
            private_write(self.connection / 'claude.mcp.json', json.dumps({'mcpServers': {'moodlia': {
            'type': 'http', 'url': endpoint,
            'headers': {'Authorization': 'Bearer ${MOODLE_REST_TOKEN}'}}}}, indent=2) + '\n')
            private_write(self.connection / 'opencode.json', json.dumps({'$schema': 'https://opencode.ai/config.json',
            'mcp': {'moodlia': {'type': 'remote', 'url': endpoint, 'oauth': False,
                                'headers': {'Authorization': 'Bearer {env:MOODLE_REST_TOKEN}'}}}}, indent=2) + '\n')
        private_write(self.connection / 'load-token.ps1',
                      '$env:MOODLE_REST_TOKEN = (Get-Content -LiteralPath (Join-Path $PSScriptRoot "token.txt") -Raw).Trim()\n'
                      '$env:MOODLE_TOKEN = $env:MOODLE_REST_TOKEN\n'
                      f'$env:MOODLE_BASE_URL = "{self.url}"\n')
        private_write(self.connection / 'load-token.sh',
                      '# Source from the package root: . ./connection/load-token.sh\n'
                      'export MOODLE_REST_TOKEN="$(cat ./connection/token.txt)"\n'
                      'export MOODLE_TOKEN="$MOODLE_REST_TOKEN"\n'
                      f'export MOODLE_BASE_URL="{self.url}"\n')

    def start_web(self):
        log = (self.data / 'logs' / 'php.log').open('a', encoding='utf-8')
        self.logs.append(log)
        environment = os.environ.copy()
        environment['MOODLIA_PRIVATE_CONFIG'] = str(self.data / 'config.json')
        environment['MOODLIA_RUNTIME_ROOT'] = str(self.root)
        environment['OPENSSL_CONF'] = str(self.root / 'app' / 'openssl.cnf')
        environment['PHPRC'] = str(self.root / 'app' / 'php.ini')
        environment['MOODLIA_PHP_EXT'] = str(self.root / 'runtime' / 'php' / 'ext')
        worker_ports = []
        for index in range(3):
            port = free_port()
            worker = subprocess.Popen([str(item) for item in self.php_args() + [
                '-S', '127.0.0.1:' + str(port), '-t', self.docroot,
                self.root / 'app' / 'router.php']], cwd=self.root, env=environment,
                stdin=subprocess.DEVNULL, stdout=log, stderr=log)
            self.php_workers.append(worker)
            worker_ports.append(port)
        self.php_process = self.php_workers[0]
        self.proxy = create_proxy(self.config['http_port'], worker_ports)
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            if any(worker.poll() is not None for worker in self.php_workers):
                raise RuntimeError('PHP stopped. See data/logs/php.log.')
            try:
                self.verify()
                return
            except (OSError, ValueError, RuntimeError):
                time.sleep(0.5)
        raise RuntimeError('Moodle did not become ready. See data/logs/.')

    def verify(self):
        if self.config.get('optional_plugins'):
            self.run(self.php_args() + [self.root / 'app' / 'verify_plugins.php', self.moodle],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        token = (self.connection / 'token.txt').read_text(encoding='utf-8').strip()
        payload = urllib.parse.urlencode({'wstoken': token, 'moodlewsrestformat': 'json',
                                         'wsfunction': 'local_moodlia_get_current_user' if self.config['plugin_enabled'] else 'core_webservice_get_site_info'}).encode()
        request = urllib.request.Request(self.url + '/webservice/rest/server.php', data=payload)
        with urllib.request.urlopen(request, timeout=10) as response:
            identity = json.load(response)
        if identity.get('username') != 'teacher':
            raise RuntimeError('MoodlIA connection did not return the teacher account.')
        if not self.config['plugin_enabled']:
            return
        request = urllib.request.Request(self.url + '/local/moodlia/mcp.php',
            data=json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list', 'params': {}}).encode(),
            headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token,
                     'Accept': 'application/json, text/event-stream'})
        with urllib.request.urlopen(request, timeout=20) as response:
            catalogue = json.load(response)
        if not catalogue.get('result', {}).get('tools'):
            raise RuntimeError('MoodlIA MCP tools are unavailable.')
        request.data = json.dumps({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call',
                                   'params': {'name': 'get_current_user', 'arguments': {}}}).encode()
        with urllib.request.urlopen(request, timeout=20) as response:
            called = json.load(response).get('result', {})
        if called.get('isError') or called.get('structuredContent', {}).get('username') != 'teacher':
            raise RuntimeError('The MCP identity tool did not return the teacher account.')

    def export_course(self, course_id):
        self.run(self.php_args() + [self.moodle / 'admin' / 'cli' / 'backup.php',
                 '--courseid=' + str(course_id), '--destination=' + str(self.workspace / 'exports')])

    def stop(self):
        if self.proxy is not None:
            self.proxy.shutdown()
            self.proxy.server_close()
            self.proxy = None
        for worker in self.php_workers:
            if worker.poll() is None:
                worker.terminate()
                try:
                    worker.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    worker.kill()
                    worker.wait()
        self.php_workers = []
        self.stop_database()
        for log in self.logs:
            log.close()

    def stop_database(self):
        if self.database_started:
            self.run([self.pg / ('pg_ctl' + self.suffix), '-D', self.data / 'postgres', '-m', 'fast', '-w', 'stop'])
            self.database_started = False


def main():
    parser = argparse.ArgumentParser(description='MoodlIA Portable: local Moodle, no Docker.')
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--check', action='store_true', help='Start, verify REST/MCP, and stop.')
    parser.add_argument('--export-course', type=int)
    parser.add_argument('--moodle-version')
    parser.add_argument('--workspace', type=Path)
    parser.add_argument('--desktop', action='store_true')
    parser.add_argument('--without-plugin', action='store_true')
    parser.add_argument('--plugin', action='append', dest='optional_plugins',
                        help='Optional bundled component, for example format_onetopic. Repeat to select several.')
    arguments = parser.parse_args()
    root = bundle_root()
    application = PortableMoodle(root, arguments.workspace)
    if arguments.desktop:
        def read_control():
            for line in sys.stdin:
                if line.strip() == 'stop':
                    break
            application.stop_requested.set()
        threading.Thread(target=read_control, daemon=True).start()
    def interrupt(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupt)
    try:
        with instance_lock(application.data / 'launcher.lock'):
            try:
                application.prepare(arguments.moodle_version, not arguments.without_plugin, arguments.optional_plugins)
                application.start_database()
                application.install()
                application.start_web()
                application.commit_runtime()
                print('Ready: ' + application.url + '\nLogin: connection/credentials.txt\nToken: connection/token.txt', flush=True)
                if arguments.export_course:
                    application.export_course(arguments.export_course)
                elif not arguments.check:
                    if not arguments.no_browser and not arguments.desktop:
                        webbrowser.open(application.url)
                    print('Keep this window open. Press Ctrl+C to stop safely.', flush=True)
                    last_cron = 0
                    while application.php_process.poll() is None and not application.stop_requested.is_set():
                        if time.monotonic() - last_cron >= 60:
                            cron_log = (application.data / 'logs' / 'cron.log')
                            with cron_log.open('a', encoding='utf-8') as stream:
                                try:
                                    application.run(application.php_args() + [application.moodle / 'admin' / 'cli' / 'cron.php', '--keep-alive=0'],
                                                    stdout=stream, stderr=stream, timeout=120)
                                except (subprocess.SubprocessError, OSError):
                                    print('A maintenance task failed; see data/logs/cron.log.', flush=True)
                            last_cron = time.monotonic()
                        time.sleep(1)
            finally:
                application.stop()
    except KeyboardInterrupt:
        print('Stopped.')
    except Exception as error:
        # Child-process errors contain arguments, so never display their repr (passwords).
        print('Unable to run MoodlIA Portable: ' + (str(error) if not isinstance(error, subprocess.SubprocessError)
              else 'A bundled process failed. See data/logs/.'), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
