"""Extract verified source archives without accepting path traversal."""
from pathlib import Path
import shutil
import zipfile


def extract_source(archive_path, destination, missing_only=False):
    destination = Path(destination).resolve()
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            name = member.filename.split('/', 1)[-1]
            if not name or member.is_dir():
                continue
            if any(part in ('.github', '.git', 'node_modules') for part in Path(name).parts):
                continue
            target = (destination / name).resolve()
            if not target.is_relative_to(destination):
                raise ValueError('Source archive path escapes destination')
            if missing_only and target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target.open('wb') as output:
                shutil.copyfileobj(source, output)
