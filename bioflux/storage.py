"""Small, inspectable artifact and resource helpers."""
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')
    # Windows file watchers/virus scanners can briefly hold the destination open.
    for attempt in range(6):
        try:
            os.replace(temporary, path)
            break
        except PermissionError:
            if attempt == 5:
                raise
            time.sleep(0.025 * 2 ** attempt)


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def project_bytes():
    total = 0
    for path in ROOT.rglob('*'):
        try:
            if path.is_file():
                total += path.stat().st_size
        except FileNotFoundError:
            # Package installers may atomically move/remove their temporary files.
            continue
    return total


class Budget:
    def __init__(self, hours=6, disk_gb=10):
        self.start = time.monotonic()
        self.seconds = hours * 3600
        self.disk_bytes = disk_gb * 1024 ** 3
        self.last_disk_check = 0

    def check(self):
        elapsed = time.monotonic() - self.start
        if elapsed > self.seconds:
            raise RuntimeError('Compute time budget reached; completed artifacts are preserved.')
        if elapsed - self.last_disk_check > 60 or self.last_disk_check == 0:
            total = project_bytes()
            self.last_disk_check = elapsed
            if total > self.disk_bytes:
                raise RuntimeError('Project disk budget reached; completed artifacts are preserved.')
