"""Data-only downloads from named official sources; no executable deserialization."""
import importlib.metadata
import json
import shutil
from urllib.parse import urlparse

import cobra
import requests

from bioflux.storage import ROOT, sha256, utc_now, write_json

ALLOWED_HOSTS = {'bigg.bio', 'bigg.ucsd.edu', 'biggdata.ucsd.edu'}


def fetch(url, maximum=25 * 1024 ** 2):
    # Check each redirect before requesting its target, not after receiving it.
    session = requests.Session()
    for _ in range(5):
        parsed = urlparse(url)
        if parsed.scheme != 'https' or parsed.hostname not in ALLOWED_HOSTS:
            raise ValueError(f'Download source is not allowlisted: {url}')
        response = session.get(url, timeout=(15, 60), stream=True, allow_redirects=False)
        if response.is_redirect:
            from urllib.parse import urljoin
            url = urljoin(url, response.headers['Location'])
            response.close()
            continue
        response.raise_for_status()
        blocks, size = [], 0
        for block in response.iter_content(1024 ** 2):
            size += len(block)
            if size > maximum:
                raise ValueError('Download exceeds data size limit.')
            blocks.append(block)
        response.close()
        return b''.join(blocks), url
    raise ValueError('Too many redirects.')


def download(model_id):
    if model_id not in {'e_coli_core', 'iML1515'}:
        raise ValueError('Only the two reviewed E. coli models are supported.')
    directory = ROOT / 'data' / 'models'
    directory.mkdir(parents=True, exist_ok=True)
    notice = directory / 'BIGG_NOTICE.txt'
    shutil.copyfile(ROOT / 'docs/third_party/BIGG_NOTICE.txt', notice)
    terms = dict(license='BiGG educational, research and non-profit permission; retain publisher notice',
                 license_url='https://bigg.ucsd.edu/about',
                 license_notice='data/models/BIGG_NOTICE.txt', license_notice_sha256=sha256(notice))
    destination = directory / f'{model_id}.json'
    manifest_path = directory / f'{model_id}.manifest.json'
    if destination.exists() and manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if sha256(destination) != manifest['sha256']:
            raise ValueError('Existing model checksum differs from its manifest.')
        raw = directory / f'{model_id}.source.json'
        if manifest.get('source_sha256') and (not raw.exists() or sha256(raw) != manifest['source_sha256']):
            raise ValueError('Original model response checksum differs from its manifest.')
        manifest.update(terms)
        write_json(manifest_path, manifest)
        return manifest
    failures = []
    for url in [f'https://bigg.bio/static/models/{model_id}.json',
                f'https://bigg.ucsd.edu/static/models/{model_id}.json']:
        try:
            content, source = fetch(url)
            payload = json.loads(content)
            if payload.get('id') != model_id or not payload.get('reactions'):
                raise ValueError('Downloaded model identity does not match request.')
            temporary = directory / f'{model_id}.download.json'
            temporary.write_bytes(content)
            model = cobra.io.load_json_model(str(temporary))
            temporary.unlink()
            (directory / f'{model_id}.source.json').write_bytes(content)
            break
        except (requests.RequestException, ValueError) as error:
            failures.append(f'{url}: {type(error).__name__}: {error}')
    else:
        if model_id != 'e_coli_core':
            raise RuntimeError('Official model download failed: ' + '; '.join(failures))
        # COBRApy distributes the core model as tutorial data, without a network call.
        model = cobra.io.load_model('textbook')
        source = f'COBRApy {importlib.metadata.version("cobra")} bundled textbook model'
    cobra.io.save_json_model(model, str(destination), pretty=True)
    manifest = dict(model_id=model_id, model_internal_id=model.id, source=source,
                    official_model_page=f'https://bigg.bio/models/{model_id}/',
                    retrieved_at=utc_now(), sha256=sha256(destination),
                    bytes=destination.stat().st_size, genes=len(model.genes),
                    metabolites=len(model.metabolites), reactions=len(model.reactions),
                    **terms,
                    failed_sources=failures, format='COBRA JSON (data only)')
    raw = directory / f'{model_id}.source.json'
    if raw.exists():
        manifest['source_sha256'] = sha256(raw)
    write_json(manifest_path, manifest)
    return manifest
