"""Execute first install and persisted restart against each bundled native Moodle."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--moodle-version', action='append', dest='versions')
options = parser.parse_args()
bundle = ROOT / 'build' / 'portable'
versions = options.versions or json.loads((bundle / 'versions.json').read_text())
executable = bundle / ('moodlia-backend.exe' if os.name == 'nt' else 'moodlia-backend')
results = []
for version in versions:
    for plugin in [True, False]:
        workspace = ROOT / 'test-workspaces' / (version + ('-plugin' if plugin else '-core'))
        workspace.mkdir(parents=True, exist_ok=True)
        arguments = [str(executable), '--moodle-version', version, '--workspace', str(workspace), '--check']
        if not plugin:
            arguments.append('--without-plugin')
        started = time.time()
        for attempt in ['initial', 'restart']:
            with (workspace / (attempt + '.log')).open('w', encoding='utf-8') as output:
                subprocess.run(arguments, stdout=output, stderr=subprocess.STDOUT, timeout=1200, check=True)
            token = (workspace / 'connection' / 'token.txt').read_bytes()
            if attempt == 'initial':
                original_token = token
                original_config = json.loads((workspace / 'data' / 'config.json').read_text())
            elif token != original_token:
                raise RuntimeError('Token changed on restart')
        current_config = json.loads((workspace / 'data' / 'config.json').read_text())
        if current_config['password'] != original_config['password']:
            raise RuntimeError('Password changed on restart')
        results.append({'moodle': version, 'plugin': plugin, 'initial': 'passed', 'restart': 'passed',
                        'token_preserved': True, 'password_preserved': True, 'seconds': round(time.time() - started, 1)})
        (ROOT / 'build' / 'qualification.json').write_text(json.dumps(results, indent=2) + '\n')
        print(f'Qualified {version}, plugin={plugin}', flush=True)
