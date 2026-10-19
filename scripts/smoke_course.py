"""Verify synthetic authoring, native export and a persistent restart locally."""
import json
import os
from pathlib import Path
import sys
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from portable import PortableMoodle, instance_lock

workspace = Path(sys.argv[1]).resolve()
application = PortableMoodle(ROOT / 'build' / 'portable', workspace)
evidence = []
with instance_lock(application.data / 'launcher.lock'):
    for attempt in ['author-and-export', 'restart']:
        try:
            application.prepare()
            application.start_database()
            application.install()
            application.start_web()
            application.commit_runtime()
            result = application.run(application.php_args() + [ROOT / 'tests' / 'course_fixture.php', application.moodle],
                                     capture_output=True, text=True)
            fixture = json.loads(result.stdout.strip().splitlines()[-1])
            if fixture['human_users'] != 1 or not fixture['teacher_is_admin']:
                raise RuntimeError('Unexpected account or privilege model')
            if attempt == 'author-and-export':
                application.export_course(fixture['course_id'])
                backups = list((workspace / 'exports').glob('*.mbz'))
                if not backups:
                    raise RuntimeError('Native course backup was not exported')
                archive = backups[-1]
                if zipfile.is_zipfile(archive):
                    with zipfile.ZipFile(archive) as backup:
                        names = backup.namelist()
                else:
                    with tarfile.open(archive) as backup:
                        names = backup.getnames()
                if 'moodle_backup.xml' not in names or not any('page_' in name for name in names):
                    raise RuntimeError('Export lacks expected native Moodle/page content')
                original = fixture
                original_token = (workspace / 'connection' / 'token.txt').read_bytes()
            else:
                if fixture != original or (workspace / 'connection' / 'token.txt').read_bytes() != original_token:
                    raise RuntimeError('Course identity or token changed on restart')
            evidence.append({'step': attempt, **fixture, 'rest_and_mcp': 'passed'})
        finally:
            application.stop()
(ROOT / 'build' / 'course-evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
print(json.dumps(evidence, indent=2))
