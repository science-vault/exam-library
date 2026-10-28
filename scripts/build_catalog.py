"""Index PDF exams and paired marking keys. Python standard library only."""
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
 for k in ['school','examType','topic','author','description','subjectGroup']:
  if k in b and not isinstance(b[k],str):raise ValueError(k+' must be text')
 return b
def infer(path):
 parts=path.parts;b=dict(title=path.stem,subject='Uncategorised',years=[],school='',examType='',topic='',description='',author='')
 for i,p in enumerate(parts[:-1]):
  m=re.fullmatch(r'Year[ _-]*(\d{1,2})',p,re.I)
  if m:
   b['years']=[int(m[1])];b['subject']=parts[i-1] if i else 'Uncategorised'
   tail=parts[i+1:-1]
   if tail:b['school']=tail[0]
   if len(tail)>1 and re.fullmatch(r'(19|20)\d{2}',tail[1]):b['examYear']=int(tail[1])
   if len(tail)>2:b['examType']=tail[2]
 if path.stem.lower() in ['paper','exam','questionpaper','question paper']:
  b['title']=' — '.join(str(x) for x in [b['subject'],('Year '+str(b['years'][0])) if b['years'] else '',b['school'],b.get('examYear'),b['examType']] if x)
 return b
def build(root):
 root=Path(root);site=root/'site';assets=site/'assets';assets.mkdir(parents=True,exist_ok=True);resource=root/'resources';files=sorted(p for p in resource.rglob('*') if p.is_file());rows=[];seen={};consumed=set()
 repo='science-vault/exam-library';raw='https://raw.githubusercontent.com/'+repo+'/main/';base='https://science-vault.github.io/exam-library/'
 def finish(b,p,identity):
  b.setdefault('years',[]);b.setdefault('school','');b.setdefault('examType','');b.setdefault('topic','');b.setdefault('author','');b.setdefault('description','');b.setdefault('format','PDF')
  b.setdefault('subjectGroup','Science' if b['subject'].lower() in ['physics','chemistry','biology','human biology','science'] else 'Humanities' if b['subject'].lower() in ['history','geography','economics','humanities'] else b['subject']);b['sourcePath']=p.relative_to(root).as_posix();b['id']='exam-'+hashlib.sha256(identity.encode()).hexdigest()[:16]
  if not b.get('added'):
   try:dates=subprocess.check_output(['git','log','--diff-filter=A','--format=%aI','--',b['sourcePath']],cwd=root,stderr=subprocess.DEVNULL,text=True).strip().splitlines();b['added']=dates[-1][:10] if dates else date.today().isoformat()
   except (subprocess.CalledProcessError,FileNotFoundError):b['added']=date.today().isoformat()
  validate(b)
  if identity in seen:seen[identity].setdefault('alternateSourcePaths',[]).append(b['sourcePath'])
  else:seen[identity]=b;rows.append(b)
 def copy(p):
  sha=hashlib.sha256(p.read_bytes()).hexdigest();dest='assets/'+sha+'.pdf';shutil.copyfile(p,site/dest);return sha,base+dest
 # Pair only the documented canonical filenames inside a single exam folder.
 pairs={}
 for folder in sorted({p.parent for p in files}):
  lookup={p.name.lower():p for p in files if p.parent==folder}
  paper=next((lookup[n] for n in ['paper.pdf','exam.pdf','questionpaper.pdf','question paper.pdf'] if n in lookup),None)
  key=next((lookup[n] for n in ['markingkey.pdf','marking key.pdf','marking_key.pdf','answers.pdf','solutions.pdf'] if n in lookup),None)
  if paper and key:pairs[paper]=key;consumed.add(key)
 for p in files:
  if p.suffix.lower()!='.pdf' or p in consumed:continue
  b=infer(p.relative_to(root));sha,preview=copy(p);b.update(url=raw+quote(p.relative_to(root).as_posix()),previewUrl=preview)
  identity=sha
  if p in pairs:
   key=pairs[p];ks,kpreview=copy(key);b.update(markingKeyUrl=raw+quote(key.relative_to(root).as_posix()),markingKeyPreviewUrl=kpreview);identity+=':'+ks
  for side in [p.parent/'exam.json',p.with_suffix('.json')]:
   if side.exists():
    value=json.loads(side.read_text())
    if 'url' not in value:b.update(value);consumed.add(side)
  if re.search(r'marking|answers|solutions',p.stem,re.I) and not b['examType']:b['examType']='Marking key'
  finish(b,p,'file:'+identity)
 for p in files:
  if p.suffix.lower()!='.json' or p in consumed:continue
  value=json.loads(p.read_text());b=infer(p.relative_to(root));b.update(value);validate(b);finish(b,p,'url:'+b['url']+'|'+b.get('markingKeyUrl',''))
 rows.sort(key=lambda b:b['title'].casefold());out={'version':1,'resources':rows};(site/'catalog.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n');print(len(rows),'exams indexed');return out
if __name__=='__main__':build(Path(__file__).resolve().parents[1])
