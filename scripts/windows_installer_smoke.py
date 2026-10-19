"""Exercise the real Windows installer in an isolated installation directory."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import secrets
import sys
import time
import winreg

ROOT = Path(__file__).resolve().parents[1]
workspace = ROOT / 'test-workspaces' / '4.5.15-plugin'
target = ROOT / 'build' / 'installed-smoke'
installer = ROOT / 'dist' / 'MoodlIA-Setup-0.1.0-x64.exe'
backend_path = ROOT / 'build' / 'portable' / 'moodlia-backend.exe'
resume = '--resume' in sys.argv
if os.name != 'nt' or (target.exists() and not resume):
    raise RuntimeError('Use Windows and a fresh build/installed-smoke directory.')


def installed_entries():
    entries = []
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Uninstall') as parent:
        for index in range(winreg.QueryInfoKey(parent)[0]):
            with winreg.OpenKey(parent, winreg.EnumKey(parent, index)) as key:
                try:
                    display_name = winreg.QueryValueEx(key, 'DisplayName')[0]
                    if display_name == 'MoodlIA' or display_name.startswith('MoodlIA '):
                        try:
                            location = winreg.QueryValueEx(key, 'InstallLocation')[0]
                        except FileNotFoundError:
                            location = ''
                        if not location:
                            command = winreg.QueryValueEx(key, 'UninstallString')[0]
                            executable = command.split('"')[1] if command.startswith('"') else command.split(' /')[0]
                            location = str(Path(executable).parent)
                        entries.append(location)
                except FileNotFoundError:
                    pass
    return entries


existing = installed_entries()
if existing and (not resume or not all(Path(entry).resolve() == target for entry in existing)):
    raise RuntimeError('An existing MoodlIA installation was found; refusing to replace it for a test.')
if resume and (not existing or not (target / 'MoodlIA.exe').is_file()):
    raise RuntimeError('Resume is allowed only for this exact isolated test installation.')
previous_executable = hashlib.sha256((target / 'MoodlIA.exe').read_bytes()).hexdigest() if resume else None
protected = [workspace / 'connection' / 'token.txt', workspace / 'connection' / 'credentials.txt',
             workspace / 'data' / 'config.json']
original = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in protected}
sentinel = Path(os.environ['APPDATA']) / 'MoodlIA' / 'workspace' / ('.installer-test-' + secrets.token_hex(8))
sentinel.parent.mkdir(parents=True, exist_ok=True)
sentinel.write_text('Synthetic default-workspace preservation evidence.', encoding='utf-8')
original[str(sentinel)] = hashlib.sha256(sentinel.read_bytes()).hexdigest()
protected.append(sentinel)
arguments = [str(installer), '/S', '/D=' + str(target)]
log_path = ROOT / 'build' / 'installer-guard-backend.log'
with log_path.open('w', encoding='utf-8') as log:
    backend = subprocess.Popen([str(backend_path), '--desktop', '--workspace', str(workspace)],
                               stdin=subprocess.PIPE, stdout=log, stderr=log, text=True)
    try:
        deadline = time.monotonic() + 180
        while 'Ready: ' not in log_path.read_text(encoding='utf-8', errors='replace'):
            if backend.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError('Backend did not become ready for installer guard test')
            time.sleep(0.2)
        result = subprocess.run(arguments, timeout=120)
        executable_preserved = (hashlib.sha256((target / 'MoodlIA.exe').read_bytes()).hexdigest() == previous_executable
                                if resume else not (target / 'MoodlIA.exe').exists())
        if result.returncode != 2 or not executable_preserved:
            raise RuntimeError('Installer did not refuse an active backend')
        print('Installer refused an active database backend.', flush=True)
    finally:
        if backend.poll() is None:
            backend.stdin.write('stop\n')
            backend.stdin.flush()
            backend.wait(timeout=180)

if not resume:
    subprocess.run(arguments, timeout=1800, check=True)
if not (target / 'MoodlIA.exe').is_file() or not any(Path(entry).resolve() == target for entry in installed_entries()):
    raise RuntimeError('Application files or Installed Apps registration missing')
print('Installed and registered in Windows.', flush=True)
subprocess.run(['node', str(ROOT / 'scripts' / 'desktop-smoke.cjs'), str(workspace), str(target / 'MoodlIA.exe')],
               cwd=ROOT, timeout=900, check=True)
print('Installed application login and graceful shutdown passed.', flush=True)
subprocess.run(arguments, timeout=1800, check=True)
print('Installer update completed.', flush=True)
uninstaller = target / 'Uninstall MoodlIA.exe'
subprocess.run([str(uninstaller), '/S', '_?=' + str(target)], timeout=300, check=True)
for path in protected:
    if hashlib.sha256(path.read_bytes()).hexdigest() != original[str(path)]:
        raise RuntimeError('Workspace credential/configuration changed during install/update/uninstall')
if installed_entries():
    raise RuntimeError('Uninstall registration still exists')
subprocess.run([sys.executable, str(ROOT / 'scripts' / 'smoke_course.py'), str(workspace)],
               cwd=ROOT, timeout=300, check=True)
sentinel.unlink()
evidence = {'guard_when_running': 'passed', 'system_registration': 'passed', 'installed_app_login': 'passed',
            'update': 'passed', 'uninstall': 'passed', 'workspace_credentials_and_configuration': 'preserved',
            'course_after_uninstall': 'preserved'}
(ROOT / 'build' / 'installer-evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
print(json.dumps(evidence, indent=2), flush=True)
