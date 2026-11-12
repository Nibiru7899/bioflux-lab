"""Hash the delivered source and link its recorded experiment evidence."""
import importlib.metadata
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bioflux.storage import ROOT, sha256, utc_now, write_json


if __name__ == '__main__':
    selected = [ROOT / name for name in ['app.py', 'README.md', 'PRODUCT.md', 'DESIGN.md', 'WORK_LOG.md',
                'pyproject.toml', '.gitignore', 'requirements.lock.txt', 'start-lab.ps1',
                'requirements-torch-cpu.txt', 'requirements-torch-cuda.txt',
                '.streamlit/config.toml', '.impeccable/design.json']]
    for folder in ['bioflux', 'scripts', 'tests', 'configs', 'docs', '.impeccable/surface-briefs']:
        selected.extend(p for p in (ROOT / folder).rglob('*')
                        if p.is_file() and '__pycache__' not in p.parts)
    selected.extend(ROOT / 'frontend' / name for name in ['package.json', 'package-lock.json',
                    'tsconfig.json', 'vite.config.ts', 'index.html'])
    for folder in ['frontend/src', 'frontend/public']:
        selected.extend(p for p in (ROOT / folder).rglob('*') if p.is_file())
    files = {str(p.relative_to(ROOT)): sha256(p) for p in sorted(set(selected)) if p.is_file()}
    evidence = {}
    for model in ['e_coli_core', 'iML1515']:
        paths = [ROOT / 'data/models' / f'{model}.manifest.json', ROOT / 'data' / model / 'manifest.json']
        paths.extend(ROOT / 'runs' / model / path for path in [
            'training/manifest.json', 'search/manifest.json', 'report/artifact_manifest.json', 'audit.json'])
        for path in paths:
            if path.exists():
                evidence[str(path.relative_to(ROOT))] = sha256(path)
    write_json(ROOT / 'SOURCE_MANIFEST.json', dict(generated_at=utc_now(), source_files=files,
               evidence_manifests=evidence, python=sys.version.split()[0],
               installed_torch=importlib.metadata.version('torch'),
               note='Relative paths and hashes identify this delivery; execution/device evidence is in individual run records.'))
    print(f'Source manifest: {len(files)} source files; {len(evidence)} evidence manifests.')
