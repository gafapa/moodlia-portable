"""Maintainer-only lock refresh. Review source URLs and hashes before packaging."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import shutil
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
MOODLE = {
    '4.5.15': '215f44380bdc3ccf852a3a22e34f8423ff64033a',
    '5.0.8': '3087780dc4668773709ee064839a0ea2773cdf30',
    '5.1.8': 'cc0bf17da8b5fbd290faf95b2b14a03d64331923',
    '5.2.4': '2df605b1e093248e8f8d1e2fc081fb3b1f65665f',
    '5.3.0': '42622298fe06f9626d988d60b2bf589bd8f850e8',
}
TARGETS = {'win32-x64': ('windows-amd64', None),
           'darwin-x64': ('darwin-amd64', 'macos-x86_64'),
           'darwin-arm64': ('darwin-arm64v8', 'macos-aarch64'),
           'linux-x64': ('linux-amd64', 'linux-x86_64'),
           'linux-arm64': ('linux-arm64v8', 'linux-aarch64')}


def specifications():
    result = {}
    for version, commit in MOODLE.items():
        major, minor, patch = version.split('.')
        branch = major + minor.zfill(2)
        filename = version if patch != '0' else major + '.' + minor
        # Official release distributions include the production Composer dependencies.
        result['moodle-' + version] = {'url': f'https://download.moodle.org/download.php/direct/stable{branch}/moodle-{filename}.zip',
                                      'release_commit': commit}
    commit = 'bac8761a8d157b830555576e6be23563b7b93db4'
    result['plugin'] = {'url': f'https://codeload.github.com/gafapa/moodle-local_moodlia/zip/{commit}', 'commit': commit}
    for target, (classifier, php_target) in TARGETS.items():
        version = '16.15.0'
        artifact = 'embedded-postgres-binaries-' + classifier
        result['postgres-' + target] = {'url': f'https://repo.maven.apache.org/maven2/io/zonky/test/postgres/{artifact}/{version}/{artifact}-{version}.jar'}
        version = '17.11.0'
        result['postgres17-' + target] = {'url': f'https://repo.maven.apache.org/maven2/io/zonky/test/postgres/{artifact}/{version}/{artifact}-{version}.jar'}
        if php_target:
            result['php-' + target] = {'url': f'https://dl.static-php.dev/static-php-cli/bulk/php-8.3.32-cli-{php_target}.tar.gz'}
        else:
            result['php-' + target] = {'url': 'https://downloads.php.net/~windows/releases/php-8.3.36-nts-Win32-vs16-x64.zip',
                'expected_sha256': '3c9242622c7402b47c38d2ec2ed779cef3a290fd6f2bde6c35f9c482699e7900'}
    return result


def lock_item(item):
    key, spec = item
    cache = ROOT / '.cache'
    cache.mkdir(exist_ok=True)
    source_id = hashlib.sha256(spec['url'].encode()).hexdigest()[:16]
    path = cache / (key + '-' + source_id)
    if not path.exists():
        print('Downloading ' + key, flush=True)
        request = urllib.request.Request(spec['url'], headers={'User-Agent': 'MoodlIA-Portable-Builder/0.1 (+https://moodlia.com)'})
        with urllib.request.urlopen(request, timeout=120) as response, path.with_suffix('.part').open('wb') as output:
            shutil.copyfileobj(response, output)
        path.with_suffix('.part').replace(path)
    digest = hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()
    if spec.get('expected_sha256', digest) != digest:
        raise RuntimeError('Publisher checksum mismatch: ' + key)
    spec['sha256'] = digest
    return key, spec


if __name__ == '__main__':
    with ThreadPoolExecutor(max_workers=5) as executor:
        locked = dict(executor.map(lock_item, specifications().items()))
    (ROOT / 'sources.lock.json').write_text(json.dumps({'schema': 1, 'sources': locked}, indent=2) + '\n', encoding='utf-8')
