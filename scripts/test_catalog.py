import unittest,tempfile,json
from pathlib import Path
from build_catalog import build,validate,infer
class Exams(unittest.TestCase):
 def test_folder_fields(self):
  b=infer(Path('resources/Secondary/Physics/Year 12/A School/2026/Semester 1/Paper.pdf'));self.assertEqual((b['subject'],b['years'],b['school'],b['examYear'],b['examType']),('Physics',[12],'A School',2026,'Semester 1'))
 def test_pair_and_deduplicate(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);p=r/'resources/Secondary/Physics/Year 12/A School/2026/Semester 1';p.mkdir(parents=True)
   (p/'Paper.pdf').write_bytes(b'%PDF-paper');(p/'MarkingKey.pdf').write_bytes(b'%PDF-key');(p/'exam.json').write_text('{"title":"Test exam"}')
   out=build(r)['resources'];self.assertEqual(len(out),1);self.assertEqual(out[0]['title'],'Test exam');self.assertIn('markingKeyUrl',out[0]);self.assertEqual(len(list((r/'site/assets').glob('*.pdf'))),2)
 def test_external_and_invalid(self):
  b={'title':'Exam','subject':'Physics','years':[12],'url':'https://example.com/exam.pdf'};validate(b)
  for change in [{'url':'javascript:alert(1)'},{'markingKeyUrl':'https://user:secret@example.com/key'},{'years':[True]},{'examYear':12}]:
   with self.assertRaises(ValueError):validate({**b,**change})
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);(r/'resources').mkdir();self.assertEqual(build(r)['resources'],[])
   for n in ['one','two']:(r/'resources'/f'{n}.json').write_text(json.dumps(b))
   self.assertEqual(len(build(r)['resources']),1)
if __name__=='__main__':unittest.main()
