"""Build a self-contained native backend for the current platform."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from portable import PortableMoodle


def safe_target(root, name):
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('Archive path escapes destination: ' + name)
    return path


def extract_tar(stream, destination):
    with tarfile.open(fileobj=stream, mode='r:*') as archive:
        # PostgreSQL bundles contain internal links. Python's data filter rejects escaping links.
        archive.extractall(destination, filter='data')


def extract_zip(path, destination, strip_root=False):
    with zipfile.ZipFile(path) as archive:
        for member in archive.infolist():
            name = member.filename.split('/', 1)[-1] if strip_root else member.filename
            if not name or member.is_dir():
                continue
            target = safe_target(destination, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target.open('wb') as output:
                shutil.copyfileobj(source, output)


def download(key, sources):
    spec = sources[key]
    cache = ROOT / '.cache' / key
    cache.parent.mkdir(exist_ok=True)
    if not cache.exists():
        temporary = cache.with_suffix('.part')
        request = urllib.request.Request(spec['url'], headers={'User-Agent': 'MoodlIA-Portable-Builder/0.1 (+https://moodlia.com)'})
        with urllib.request.urlopen(request, timeout=120) as response, temporary.open('wb') as output:
            shutil.copyfileobj(response, output)
        temporary.replace(cache)
    with cache.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest != spec['sha256']:
        raise RuntimeError('SHA-256 mismatch: ' + key)
    return cache


def build(versions):
    architecture = 'arm64' if platform.machine().lower() in ('arm64', 'aarch64') else 'x64'
    target = sys.platform + '-' + architecture
    sources = json.loads((ROOT / 'sources.lock.json').read_text(encoding='utf-8'))['sources']
    output = ROOT / 'build' / 'portable'
    if output.exists():
        raise RuntimeError('build/portable already exists. Preserve any test data, then remove this exact build folder before rebuilding.')
    output.mkdir(parents=True)
    app = output / 'app'
    app.mkdir()
    for source in (ROOT / 'src').glob('*'):
        if source.suffix in ('.php', '.ini', '.cnf', '.txt'):
            shutil.copyfile(source, app / source.name)
    for version in versions:
        print('Preparing Moodle ' + version, flush=True)
        (app / 'versions').mkdir(exist_ok=True)
        shutil.copy2(download('moodle-' + version, sources), app / 'versions' / (version + '.zip'))
    extract_zip(download('plugin', sources), app / 'plugin', strip_root=True)
    php_root = output / 'runtime' / 'php'
    php_root.mkdir(parents=True)
    php_archive = download('php-' + target, sources)
    if os.name == 'nt':
        extract_zip(php_archive, php_root)
        with (app / 'php.ini').open('a', encoding='utf-8') as configuration:
            configuration.write('extension_dir="${MOODLIA_PHP_EXT}"\n')
            for extension in ['curl', 'fileinfo', 'gd', 'intl', 'mbstring', 'openssl', 'pgsql', 'soap', 'sodium', 'zip']:
                configuration.write('extension=' + extension + '\n')
    else:
        extract_tar(php_archive.open('rb'), php_root)
        candidates = list(php_root.rglob('php'))
        if not candidates:
            raise RuntimeError('PHP executable missing from archive')
        if candidates[0] != php_root / 'php':
            shutil.copy2(candidates[0], php_root / 'php')
        (php_root / 'php').chmod(0o755)
    for database in ['postgres', 'postgres17']:
        pg_root = output / 'runtime' / database
        with zipfile.ZipFile(download(database + '-' + target, sources)) as jar:
            names = [name for name in jar.namelist() if name.endswith('.txz')]
            if len(names) != 1:
                raise RuntimeError('Unexpected PostgreSQL archive layout')
            extract_tar(io.BytesIO(jar.read(names[0])), pg_root)
    if os.name == 'nt':
        # Microsoft permits app-local distribution of these Visual C++ runtime DLLs.
        for name in ['vcruntime140.dll', 'vcruntime140_1.dll', 'msvcp140.dll']:
            source = Path(os.environ['SystemRoot']) / 'System32' / name
            for destination in [php_root, output / 'runtime' / 'postgres' / 'bin', output / 'runtime' / 'postgres17' / 'bin']:
                shutil.copy2(source, destination / name)
    finalize(output, versions, target)


def finalize(output, versions, target):
    app = output / 'app'
    for source in (ROOT / 'src').glob('*'):
        if source.suffix in ('.php', '.ini', '.cnf', '.txt') and source.name != 'php.ini':
            shutil.copyfile(source, app / source.name)
    (output / 'versions.json').write_text(json.dumps(versions) + '\n', encoding='utf-8')
    (output / 'runtime-manifest.json').write_text(json.dumps({
        'app_version': json.loads((ROOT / 'package.json').read_text())['version'],
        'target': target, 'postgres_majors': [16, 17], 'versions': versions,
        'source_lock_sha256': hashlib.sha256((ROOT / 'sources.lock.json').read_bytes()).hexdigest(),
        'launcher_sha256': hashlib.sha256((ROOT / 'src' / 'portable.py').read_bytes()).hexdigest()
        , 'source_payload_sha256': hashlib.sha256(b''.join(path.read_bytes() for path in sorted((ROOT / 'src').glob('*')) if path.is_file())).hexdigest()
    }, sort_keys=True) + '\n', encoding='utf-8')
    shutil.copy2(ROOT / 'sources.lock.json', output)
    for filename in ['README.md', 'LICENSE']:
        shutil.copy2(ROOT / filename, output)
    shutil.copytree(ROOT / 'docs', output / 'docs', dirs_exist_ok=True)
    backend = PortableMoodle(output)
    environment = os.environ.copy()
    environment['OPENSSL_CONF'] = str(app / 'openssl.cnf')
    subprocess.run([str(item) for item in backend.php_args() + [app / 'check.php']], env=environment, check=True)
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onefile',
                    '--name', 'moodlia-backend', '--distpath', str(output),
                    '--workpath', str(ROOT / 'build' / 'pyinstaller'),
                    '--specpath', str(ROOT / 'build'), str(ROOT / 'src' / 'portable.py')], check=True)
    print('Native backend: ' + str(output), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--moodle-version', action='append', dest='versions',
                        help='Repeat for multiple versions. Default: every locked stable version.')
    parser.add_argument('--refresh-backend', action='store_true', help='Refresh launcher/docs only; preserve downloaded runtimes.')
    options = parser.parse_args()
    sources = json.loads((ROOT / 'sources.lock.json').read_text(encoding='utf-8'))['sources']
    versions = options.versions or [name.removeprefix('moodle-') for name in sources if name.startswith('moodle-')]
    if not versions or any('moodle-' + version not in sources for version in versions):
        parser.error('Choose a version from sources.lock.json, starting at Moodle 4.5.')
    if options.refresh_backend:
        output = ROOT / 'build' / 'portable'
        versions = json.loads((output / 'versions.json').read_text())
        architecture = 'arm64' if platform.machine().lower() in ('arm64', 'aarch64') else 'x64'
        finalize(output, versions, sys.platform + '-' + architecture)
    else:
        build(versions)
