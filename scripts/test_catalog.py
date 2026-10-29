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
class UploadedFormats(unittest.TestCase):
 def test_key_suffix_and_semester_words(self):
  b=infer(Path('resources/Secondary/Science/Year 11/Human Biology/2021/2021_AEHBY_Semester_Two_Exam_KEY.pdf'))
  self.assertEqual((b['documentRole'],b['examType']),('Marking key','Semester 2'))
 def test_alternative_folder_and_year(self):
  b=infer(Path('resources/Secondary/Science/Year 11/Chemistry/2017/Yr11 Chem Exam Sem 1.docx'))
  self.assertEqual((b['subject'],b['years'],b['school'],b['examYear'],b['examType']),('Chemistry',[11],'',2017,'Semester 1'))
  b=infer(Path('resources/Secondary/Science/Year 12/Physics/2011/Churchlands 2011 sem 1/Paper.pdf'))
  self.assertEqual((b['subject'],b['school'],b['examType']),('Physics','Churchlands','Semester 1'))
 def test_word_pair_duplicates_and_temporary_files(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);p=r/'resources/Secondary/Science/Year 11/Human Biology/2016';p.mkdir(parents=True)
   (p/'Human biology final.docx').write_bytes(b'word-paper')
   (p/'Human biology marking guide final.doc').write_bytes(b'word-key')
   (p/'Copy of another exam.docx').write_bytes(b'word-other')
   (p/'Another exam.docx').write_bytes(b'word-other')
   (p/'._MacExam.pdf').write_bytes(b'metadata');(p/'~$exam.docx').write_bytes(b'lock');(p/'-$exam.doc').write_bytes(b'lock')
   out=build(r)['resources'];self.assertEqual(len(out),2)
   paper=next(b for b in out if 'markingKeyUrl' in b)
   self.assertEqual((paper['subject'],paper['format']),('Human Biology','DOCX'));self.assertIn('officeapps.live.com',paper['previewUrl']);self.assertIn('officeapps.live.com',paper['markingKeyPreviewUrl'])
   report=json.loads((r/'site/import-report.json').read_text());self.assertEqual(report['sourceDocuments'],4);self.assertEqual(report['unaccountedDocuments'],[]);self.assertEqual(len(report['ignoredMetadataFiles']),3)
 def test_ambiguous_keys_remain_separate(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);p=r/'resources/Secondary/Science/Year 12/Physics/2020';p.mkdir(parents=True)
   for n,b in [('Exam A.docx',b'one'),('Exam A answers.docx',b'two'),('Exam A solutions.pdf',b'three')]: (p/n).write_bytes(b)
   out=build(r)['resources'];self.assertEqual(len(out),3);self.assertTrue(all('markingKeyUrl' not in b for b in out))
 def test_complete_paired_duplicate_provenance(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d)
   for school in ['A School','B School']:
    p=r/'resources/Secondary/Physics/Year 12'/school/'2026';p.mkdir(parents=True)
    (p/'Paper.pdf').write_bytes(b'paper');(p/'MarkingKey.pdf').write_bytes(b'key')
   self.assertEqual(len(build(r)['resources']),1)
   report=json.loads((r/'site/import-report.json').read_text());self.assertEqual(report['unaccountedDocuments'],[])
if __name__=='__main__':unittest.main()
