import hashlib
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from build_thumbnails import build, thumbnail


def pdf(path, pages=1):
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>',
               ('<< /Type /Pages /Kids [' + ' '.join(f'{3+i*2} 0 R' for i in range(pages)) +
                f'] /Count {pages} >>').encode()]
    for i in range(pages):
        objects.append(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 420] /Contents {4+i*2} 0 R >>'.encode())
        content = (b'1 0 0 rg' if i == 0 else b'0 0 1 rg') + b' 20 20 260 380 re f'
        objects.append(f'<< /Length {len(content)} >>\nstream\n'.encode() + content + b'\nendstream')
    data = b'%PDF-1.4\n'; offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(data)); data += f'{i} 0 obj\n'.encode() + obj + b'\nendobj\n'
    start = len(data)
    data += f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode()
    data += b''.join(f'{offset:010} 00000 n \n'.encode() for offset in offsets[1:])
    data += f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF'.encode()
    path.write_bytes(data)


@unittest.skipUnless(shutil.which('pdftoppm'), 'Poppler not installed')
class PreviewTests(unittest.TestCase):
    def test_only_first_page_and_cached_image(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); pdf(root/'one.pdf'); pdf(root/'two.pdf', 2)
            thumbnail(root/'one.pdf', root/'one.jpg'); thumbnail(root/'two.pdf', root/'two.jpg')
            self.assertEqual((root/'one.jpg').read_bytes(), (root/'two.jpg').read_bytes())
            self.assertTrue((root/'one.jpg').read_bytes().startswith(b'\xff\xd8'))
            with patch('build_thumbnails.run', side_effect=AssertionError('Cached file was rerendered')):
                thumbnail(root/'one.pdf', root/'one.jpg')

    def test_failed_preview_retains_resource_and_reports_error(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); (root/'resources').mkdir(); (root/'site').mkdir()
            (root/'resources/broken.pdf').write_bytes(b'not a pdf')
            rows = [{'id': 'keep-me', 'sourcePath': 'resources/broken.pdf'}]
            (root/'site/catalog.json').write_text(json.dumps({'resources': rows}))
            report = build(root)
            self.assertEqual(report['generated'], 0); self.assertEqual(len(report['failed']), 1)
            self.assertEqual(json.loads((root/'site/catalog.json').read_text())['resources'], rows)

    @unittest.skipUnless(shutil.which('soffice') or shutil.which('libreoffice'), 'LibreOffice not installed')
    def test_word_first_page(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); source = root/'exam.docx'
            with zipfile.ZipFile(source, 'w') as z:
                z.writestr('[Content_Types].xml', '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
                z.writestr('_rels/.rels', '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
                z.writestr('word/document.xml', '<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Physics exam first-page preview</w:t></w:r></w:p></w:body></w:document>')
            thumbnail(source, root/'word.jpg')
            self.assertTrue((root/'word.jpg').read_bytes().startswith(b'\xff\xd8'))


if __name__ == '__main__':
    unittest.main()
