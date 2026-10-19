"""Restore a synthetic native course backup into a separate plugin-free Moodle."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from portable import PortableMoodle, instance_lock

application = PortableMoodle(ROOT / 'build' / 'portable', Path(sys.argv[1]))
backup = Path(sys.argv[2]).resolve()
with instance_lock(application.data / 'launcher.lock'):
    try:
        application.prepare()
        application.start_database()
        application.start_web()
        application.run(application.php_args() + [application.moodle / 'admin' / 'cli' / 'restore_backup.php',
                        '--file=' + str(backup), '--categoryid=1'])
        result = application.run(application.php_args() + [ROOT / 'tests' / 'import_fixture.php', application.moodle],
                                 capture_output=True, text=True)
        evidence = json.loads(result.stdout.strip().splitlines()[-1])
        evidence.update({'source_moodle': '4.5.15', 'destination_moodle': application.config['moodle_version']})
        (ROOT / 'build' / 'restore-evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
        print(json.dumps(evidence, indent=2))
    finally:
        application.stop()
