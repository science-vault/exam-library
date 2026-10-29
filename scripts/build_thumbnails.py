"""Generate cached first-page JPEGs from the original PDF and Word documents."""
import hashlib
import json
import os
import shutil
import signal
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def run(command, timeout=90):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               start_new_session=True)
    try:
        output, errors = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        raise RuntimeError('Document preview conversion timed out')
    if process.returncode:
        raise RuntimeError(errors.decode(errors='replace')[-300:] or 'Conversion failed')
    return output


def thumbnail(source, destination):
    """Render page one; never replace a failed conversion with a fake preview."""
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if destination.exists() and destination.stat().st_size:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='exam-preview-') as folder:
        work = Path(folder)
        pdf = source
        if source.suffix.lower() in ['.doc', '.docx']:
            office = shutil.which('soffice') or shutil.which('libreoffice')
            if not office:
                raise RuntimeError('LibreOffice is required for Word previews')
            run([office, '-env:UserInstallation=' + (work / 'profile').as_uri(),
                 '--headless', '--convert-to',
                 'pdf:writer_pdf_Export:{"PageRange":{"type":"string","value":"1"}}',
                 '--outdir', str(work), str(source)])
            pdf = work / (source.stem + '.pdf')
            if not pdf.exists():
                raise RuntimeError('Word document could not be converted')
        elif source.suffix.lower() != '.pdf':
            raise RuntimeError('Unsupported document format')
        run(['pdftoppm', '-f', '1', '-singlefile', '-scale-to', '900',
             '-jpeg', '-jpegopt', 'quality=82', str(pdf), str(work / 'page')], timeout=45)
        image = work / 'page.jpg'
        if not image.exists() or image.stat().st_size < 100:
            raise RuntimeError('First page could not be rendered')
        shutil.copyfile(image, destination)


def build(root):
    root = Path(root).resolve()
    site = root / 'site'
    catalog_path = site / 'catalog.json'
    catalog = json.loads(catalog_path.read_text())
    documents = {}
    failed = []
    for row in catalog['resources']:
        # Respect explicitly supplied thumbnails for external resources.
        if row.get('thumbnail'):
            continue
        source = (root / row.get('sourcePath', '')).resolve()
        if not source.is_relative_to(root / 'resources') or not source.is_file():
            continue
        if source.suffix.lower() not in ['.pdf', '.doc', '.docx']:
            continue
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        documents.setdefault(digest, {'source': source, 'rows': []})['rows'].append(row)

    def render(entry):
        digest, document = entry
        relative = 'assets/thumbnails/' + digest + '.jpg'
        try:
            thumbnail(document['source'], site / relative)
            return document, relative, None
        except (RuntimeError, OSError) as error:
            return document, None, str(error)

    with ThreadPoolExecutor(max_workers=4) as pool:
        for document, relative, error in pool.map(render, documents.items()):
            for row in document['rows']:
                if relative:
                    row['thumbnail'] = relative
                else:
                    failed.append({'sourcePath': row['sourcePath'], 'reason': error})
    catalog_path.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + '\n')
    report = {'generated': sum(bool(row.get('thumbnail')) for row in catalog['resources']),
              'total': len(catalog['resources']), 'failed': failed}
    (site / 'thumbnail-report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f"First-page previews: {report['generated']}/{report['total']}; failed: {len(failed)}", flush=True)
    return report


if __name__ == '__main__':
    build(Path(__file__).resolve().parents[1])
