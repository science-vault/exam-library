"""Index PDF and Word exams with conservative marking-key pairing."""
import json,re,hashlib,shutil,subprocess
from pathlib import Path
from urllib.parse import urlsplit,quote
from datetime import date
def https(value):
 try:
  u=urlsplit(value);return u.scheme=='https' and bool(u.hostname) and not u.username and not u.password
 except (ValueError,TypeError):return False
def validate(b):
 for k in ['title','subject','url']:
  if not isinstance(b.get(k),str) or not b[k].strip():raise ValueError('Missing '+k)
 for k in ['url','previewUrl','markingKeyUrl','markingKeyPreviewUrl']:
  if b.get(k) and not https(b[k]):raise ValueError('Invalid HTTPS link: '+k)
 if not isinstance(b.get('years'),list) or any(type(y) is not int or not 1<=y<=12 for y in b['years']):raise ValueError('Invalid school year level')
 if b.get('examYear') is not None and (type(b['examYear']) is not int or not 1900<=b['examYear']<=2100):raise ValueError('Invalid exam year')
 for k in ['school','examType','topic','author','description','subjectGroup','documentRole']:
  if k in b and not isinstance(b[k],str):raise ValueError(k+' must be text')
 return b
SUBJECTS={x.casefold():x for x in ['Physics','Chemistry','Human Biology','Biology','Psychology','Science','Mathematics Methods','Mathematics Applications','Mathematics Specialist','English','Geography','History','Economics']}
KEY_WORDS=r'marking[ _-]*(?:guide|key|scheme)|mark[ _-]*(?:key|scheme)|answer(?:s)?|solutions?|solns?|\bmk\b|\bans\b|\bkeys?\b'
def is_key(path):
 name=path.stem.replace('_',' ')
 return not re.search(r'(?:no|without|with|and)\s+(?:answers|solutions)',name,re.I) and bool(re.search(KEY_WORDS,name,re.I))
def pair_name(path):
 return re.sub(r'[^a-z0-9]','',re.sub(KEY_WORDS,'',path.stem.lower().replace('_',' ')))
def usable(path):
 return path.suffix.lower() in ['.pdf','.doc','.docx'] and not any(part.startswith(('._','~$','-$')) or part=='.DS_Store' for part in path.parts)
def infer(path):
 parts=path.parts;b=dict(title=path.stem,subject='Uncategorised',years=[],school='',examType='',topic='',description='',author='')
 for i,part in enumerate(parts[:-1]):
  m=re.fullmatch(r'Year[ _-]*(\d{1,2})',part,re.I)
  if not m:continue
  b['years']=[int(m[1])];before=parts[i-1] if i else 'Uncategorised';tail=list(parts[i+1:-1])
  # Support both Subject/Year and Science/Year/Subject upload layouts.
  after=SUBJECTS.get(tail[0].casefold()) if tail else None
  if before.casefold() in ['science','mathematics','humanities'] and after and after.casefold()!=before.casefold():
   b['subject']=after;tail=tail[1:]
  else:b['subject']=SUBJECTS.get(before.casefold(),before)
  year=next((int(x) for x in tail if re.fullmatch(r'(19|20)\d{2}',x)),None)
  if year:b['examYear']=year
  non_school=r'^(?:(?:19|20)\d{2}|semester|stage|sample|practice exams|exam \d|a level physics|hsc trials|british columbia|\[other\]|11 physics)'
  source=next((x for x in tail if not re.search(non_school,x,re.I)),None)
  if source:b['school']=re.sub(r'\s+(?:19|20)\d{2}.*$','',source).strip()
  text=' '.join(tail+[path.stem]).replace('_',' ')
  if 'examYear' not in b:
   y=re.search(r'(?<!\d)((?:19|20)\d{2})(?!\d)',path.stem)
   if y:b['examYear']=int(y[1])
  semester=re.search(r'\bsem(?:ester)?[ ._-]*(1|2|one|two)\b',text,re.I)
  if semester:b['examType']='Semester '+{'one':'1','two':'2'}.get(semester[1].lower(),semester[1])
  elif re.search(r'\btrial',text,re.I):b['examType']='Trial exam'
  elif re.search(r'practice exam',text,re.I):b['examType']='Practice exam'
  elif re.search(r'\bwace\b',text,re.I):b['examType']='WACE'
  break
 b['documentRole']='Marking key' if is_key(path) else 'Exam paper'
 if b['documentRole']=='Marking key' and not b['examType']:b['examType']='Marking key'
 if path.stem.lower() in ['paper','exam','questionpaper','question paper']:
  b['title']=' — '.join(str(x) for x in [b['subject'],('Year '+str(b['years'][0])) if b['years'] else '',b['school'],b.get('examYear'),b['examType']] if x)
 return b
def build(root):
 root=Path(root);site=root/'site';assets=site/'assets';assets.mkdir(parents=True,exist_ok=True);resource=root/'resources';files=sorted(p for p in resource.rglob('*') if p.is_file());rows=[];seen={};consumed=set();ignored=[p.relative_to(root).as_posix() for p in files if p.suffix.lower() in ['.pdf','.doc','.docx','.pages'] and not usable(p)]
 repo='science-vault/exam-library';raw='https://raw.githubusercontent.com/'+repo+'/main/';base='https://science-vault.github.io/exam-library/'
 def finish(b,p,identity):
  b.setdefault('years',[]);b.setdefault('school','');b.setdefault('examType','');b.setdefault('topic','');b.setdefault('author','');b.setdefault('description','');b.setdefault('format','PDF')
  b.setdefault('subjectGroup','Science' if b['subject'].lower() in ['physics','chemistry','biology','human biology','science'] else 'Humanities' if b['subject'].lower() in ['history','geography','economics','humanities'] else b['subject']);b['sourcePath']=p.relative_to(root).as_posix();b['id']='exam-'+hashlib.sha256(identity.encode()).hexdigest()[:16]
  if not b.get('added'):
   try:dates=subprocess.check_output(['git','log','--diff-filter=A','--format=%aI','--',b['sourcePath']],cwd=root,stderr=subprocess.DEVNULL,text=True).strip().splitlines();b['added']=dates[-1][:10] if dates else date.today().isoformat()
   except (subprocess.CalledProcessError,FileNotFoundError):b['added']=date.today().isoformat()
  validate(b)
  if identity in seen:
   seen[identity].setdefault('alternateSourcePaths',[]).append(b['sourcePath'])
   if b.get('markingKeySourcePath'):seen[identity].setdefault('alternateMarkingKeySourcePaths',[]).append(b['markingKeySourcePath'])
  else:seen[identity]=b;rows.append(b)
 def copy(p):
  sha=hashlib.sha256(p.read_bytes()).hexdigest();dest='assets/'+sha+'.pdf';shutil.copyfile(p,site/dest);return sha,base+dest
 # Pair canonical names, or one exact normalised paper/key name in the same folder.
 pairs={}
 for folder in sorted({p.parent for p in files if usable(p)}):
  documents=[p for p in files if p.parent==folder and usable(p)]
  lookup={p.name.lower():p for p in documents}
  paper=next((lookup[n+ext] for n in ['paper','exam','questionpaper','question paper'] for ext in ['.pdf','.docx','.doc'] if n+ext in lookup),None)
  key=next((lookup[n+ext] for n in ['markingkey','marking key','marking_key','answers','solutions'] for ext in ['.pdf','.docx','.doc'] if n+ext in lookup),None)
  if paper and key:pairs[paper]=key;consumed.add(key)
  candidates={pair_name(p) for p in documents if is_key(p) and p not in consumed}
  for name in candidates:
   papers=[p for p in documents if not is_key(p) and p not in pairs and pair_name(p)==name]
   keys=[p for p in documents if is_key(p) and p not in consumed and pair_name(p)==name]
   if len(papers)==1 and len(keys)==1:pairs[papers[0]]=keys[0];consumed.add(keys[0])
 def preview(p):
  if p.suffix.lower()=='.pdf':return copy(p)
  sha=hashlib.sha256(p.read_bytes()).hexdigest();url=raw+quote(p.relative_to(root).as_posix())
  return sha,'https://view.officeapps.live.com/op/embed.aspx?src='+quote(url,safe='')
 for p in files:
  if not usable(p) or p in consumed:continue
  b=infer(p.relative_to(root));sha,preview_url=preview(p);b.update(url=raw+quote(p.relative_to(root).as_posix()),previewUrl=preview_url,format=p.suffix[1:].upper())
  identity=sha
  if p in pairs:
   key=pairs[p];ks,kpreview=preview(key);b.update(markingKeyUrl=raw+quote(key.relative_to(root).as_posix()),markingKeyPreviewUrl=kpreview,markingKeySourcePath=key.relative_to(root).as_posix());identity+=':'+ks
  for side in [p.parent/'exam.json',p.with_suffix('.json')]:
   if side.exists():
    value=json.loads(side.read_text())
    if 'url' not in value:b.update(value);consumed.add(side)
  finish(b,p,'file:'+identity)
 for p in files:
  if p.suffix.lower()!='.json' or p in consumed:continue
  value=json.loads(p.read_text());b=infer(p.relative_to(root));b.update(value);validate(b);finish(b,p,'url:'+b['url']+'|'+b.get('markingKeyUrl',''))
 accounted=set()
 for b in rows:accounted.update([b['sourcePath'],*b.get('alternateSourcePaths',[]),*b.get('alternateMarkingKeySourcePaths',[])]);accounted.update([b['markingKeySourcePath']] if b.get('markingKeySourcePath') else [])
 missing=[p.relative_to(root).as_posix() for p in files if usable(p) and p.relative_to(root).as_posix() not in accounted]
 if missing:raise ValueError('Documents missing from catalogue: '+str(missing))
 report={'unaccountedDocuments':missing,'sourceDocuments':sum(usable(p) for p in files),'indexedRecords':len(rows),'pairedKeys':sum('markingKeyUrl' in b for b in rows),'exactDuplicateSources':sum(len(b.get('alternateSourcePaths',[])) for b in rows),'formats':{f:sum(b['format']==f for b in rows) for f in ['PDF','DOC','DOCX']},'subjects':{subject:sum(b['subject']==subject for b in rows) for subject in sorted({b['subject'] for b in rows})},'ignoredMetadataFiles':ignored};(site/'import-report.json').write_text(json.dumps(report,indent=2)+'\n')
 rows.sort(key=lambda b:b['title'].casefold());out={'version':1,'resources':rows};(site/'catalog.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n');print(len(rows),'exams indexed');return out
if __name__=='__main__':build(Path(__file__).resolve().parents[1])
