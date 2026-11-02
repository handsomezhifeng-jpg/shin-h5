"""Audit construction provenance against every bundle in the source 1.4.93.1 manifest.

This is a local, read-only audit. It never downloads or changes source assets.
APK embedded non-bundle members are verified directly. Bundle files are not
exempt merely because they came from the APK. Every claim retains its JSON path.
"""
from pathlib import Path
import argparse,collections,hashlib,json,re,zipfile
from mhx_public_resources import parse_catalog,DEFAULT_APK,ANALYSIS

ROOT=Path(__file__).resolve().parents[1]
VERSION='1.4.93.1'
MANIFEST_SHA256='37ef8886b6d0cbdc2d860d16f00158e52cab9e7e06a6be5eb55bc75811d8f3d6'
HASH32=re.compile(r'^[a-f0-9]{32}$',re.I)
HASH64=re.compile(r'^[a-f0-9]{64}$',re.I)
SOURCE_PATTERN=re.compile(r'^(?:apk:)?assets/(?:Bundles/|bin/Data/|SettingV2/|Lua/)|(?:^|/)downloaded/[a-f0-9]{2}/[a-f0-9]{32}/__data$',re.I)
# Explicit exceptions, if needed, must name the original APK member and its exact
# SHA256. Ordinary bundles and a broad "shader" name match are never whitelisted.
SHARED_SHADER_EXCEPTIONS={}

def normalized(value):
 value=re.sub('/+','/',str(value).replace('\\','/'))
 if value.startswith('assets/'):value='apk:'+value
 return value

class Audit:
 def __init__(self,args):
  self.args=args;self.archive=zipfile.ZipFile(args.apk);self.names=set(self.archive.namelist())
  with args.apk.open('rb')as file:self.apk_sha256=hashlib.file_digest(file,'sha256').hexdigest()
  self.catalog=parse_catalog(args.manifest.read_bytes())
  if self.catalog['version']!=VERSION or self.catalog['sha256']!=MANIFEST_SHA256:raise ValueError('The verified source-matched manifest is required')
  self.by_hash={b['hash']:b for b in self.catalog['bundles']};self.by_name={b['name']:b for b in self.catalog['bundles']}
  self.other={}
  if args.compare_manifest.exists():
   comparison=parse_catalog(args.compare_manifest.read_bytes())
   self.other={b['hash']:{'version':comparison['version'],'name':b['name']}for b in comparison['bundles']}
  self.refs=collections.defaultdict(list);self.claims=[];self.metadata=[];self.parse_errors=[];self.records=[];self.excluded_diagnostics=[]

 def source(self,value,file,path,claim=None):
  if not isinstance(value,str):return False
  value=normalized(value)
  if not SOURCE_PATTERN.search(value.removeprefix('apk:')):return False
  ref={'file':file,'jsonPath':path}
  if claim is not None:
   if isinstance(claim,str)and HASH64.fullmatch(claim):ref['claimedSha256']=claim.lower()
   else:self.claims.append({'kind':'invalid-source-sha256-claim','file':file,'jsonPath':path,'claimed':claim})
  self.refs[value].append(ref);return True

 def walk(self,value,file,path=''):
  if isinstance(value,dict):
   for key,child in value.items():
    pointer=path+'/'+key.replace('~','~0').replace('/','~1')
    if file.endswith('/source-version-audit.json')and key=='excludedBundles':
     self.excluded_diagnostics.append({'file':file,'jsonPath':pointer,'count':len(child),'reason':'Explicitly excluded cache entries from a previous audit; not an exported asset dependency'})
     continue
    keyed_claim=child.get('sha256')if isinstance(child,dict)else(child if isinstance(child,str)and HASH64.fullmatch(child)else None)
    if self.source(key,file,pointer,keyed_claim):pass
    if isinstance(child,str):
     claim=value.get('sourceSha256',value.get('sourceSHA256'))
     if not claim and key in ('source','bundle')and 'url'not in value and 'kind'not in value:claim=value.get('sha256')
     self.source(child,file,pointer,claim)
     if key in ('originalCatalogVersion','catalogVersion')and child!=VERSION:self.claims.append({'kind':'catalog-version-mismatch','file':file,'jsonPath':pointer,'claimed':child,'expected':VERSION})
     if key in ('catalogSHA256',)and child!=MANIFEST_SHA256:self.claims.append({'kind':'catalog-sha256-mismatch','file':file,'jsonPath':pointer,'claimed':child,'expected':MANIFEST_SHA256})
     if key.lower()=='apksha256'and child!=self.apk_sha256:self.claims.append({'kind':'apk-sha256-mismatch','file':file,'jsonPath':pointer,'claimed':child,'expected':self.apk_sha256})
    if key in ('catalog','originalCatalog')and isinstance(child,dict):
     if child.get('version')!=VERSION:self.claims.append({'kind':'catalog-version-mismatch','file':file,'jsonPath':pointer+'/version','claimed':child.get('version'),'expected':VERSION})
     if child.get('sha256')!=MANIFEST_SHA256:self.claims.append({'kind':'catalog-sha256-mismatch','file':file,'jsonPath':pointer+'/sha256','claimed':child.get('sha256'),'expected':MANIFEST_SHA256})
    self.walk(child,file,pointer)
   if '/bundles/'in path and isinstance(value.get('name'),str)and('md5'in value or 'hash'in value):
    expected=self.by_name.get(value['name']);claimed=value.get('md5',value.get('hash'))
    for field,actual,wanted in [('md5',claimed,expected['hash']if expected else None),('size',value.get('size'),expected['size']if expected else None)]:
     if actual!=wanted:self.claims.append({'kind':'catalog-bundle-'+field+'-mismatch','file':file,'jsonPath':path,'name':value['name'],'claimed':actual,'expected':wanted})
    if expected:
     member='assets/Bundles/Android/Base/'+expected['hash']+Path(expected['name']).suffix
     source='apk:'+member if member in self.names else str(self.args.cache/expected['hash'][:2]/expected['hash']/'__data')
     self.source(source,file,path+'/catalogBundle')
  elif isinstance(value,list):
   for index,child in enumerate(value):
    if isinstance(child,str):self.source(child,file,path+'/'+str(index))
    else:self.walk(child,file,path+'/'+str(index))

 def scan(self):
  targets=[self.args.assets/name for name in self.args.metadata]if getattr(self.args,'metadata',None)else self.args.assets.rglob('*.json')
  for path in sorted(targets):
   file=path.relative_to(ROOT).as_posix()if path.is_relative_to(ROOT)else str(path)
   try:raw=path.read_bytes();value=json.loads(raw.decode('utf8'))
   except Exception as error:self.parse_errors.append({'file':file,'error':str(error)});continue
   self.metadata.append({'file':file,'sha256':hashlib.sha256(raw).hexdigest()});self.walk(value,file)

 def verify(self,source,refs):
  result={'source':source,'references':refs,'issues':[]}
  member=source.removeprefix('apk:')if source.startswith('apk:')else None
  try:raw=self.archive.read(member)if member else Path(source).read_bytes()
  except(KeyError,FileNotFoundError):result['issues'].append('source-file-missing');return result
  md5=hashlib.md5(raw).hexdigest();sha=hashlib.sha256(raw).hexdigest();result.update(size=len(raw),md5=md5,sha256=sha)
  claims=sorted({r['claimedSha256']for r in refs if 'claimedSha256'in r})
  if any(claim!=sha for claim in claims):result['issues'].append('source-sha256-claim-mismatch');result['claimedSha256']=claims
  embedded=member is not None and not member.startswith('assets/Bundles/')
  if embedded:result.update(status='apk-embedded-non-bundle',exception='Exact original APK member; outside the bundle catalog');return result
  expected=self.by_hash.get(md5)
  if expected:
   result.update(status='source-version',catalogVersion=VERSION,bundleName=expected['name'],expectedSize=expected['size'])
   if len(raw)!=expected['size']:result['issues'].append('catalog-size-mismatch')
  elif member in SHARED_SHADER_EXCEPTIONS and sha==SHARED_SHADER_EXCEPTIONS[member]:result.update(status='official-shared-shader-exception',exception='Exact original APK member and explicit SHA256')
  else:
   result['status']='version-mismatch';result['issues'].append('bundle-not-in-source-manifest')
   if md5 in self.other:
    result['foundInVersion']=self.other[md5]['version'];result['bundleName']=self.other[md5]['name']
    replacement=self.by_name.get(result['bundleName'])
    if replacement:result['expectedReplacement']={'md5':replacement['hash'],'size':replacement['size']}
  filename_hash=Path(member or source).stem if member else Path(source).parent.name
  if HASH32.fullmatch(filename_hash)and filename_hash.lower()!=md5:result['issues'].append('filename-content-md5-mismatch')
  return result

 def run(self):
  self.scan()
  for source,refs in sorted(self.refs.items()):self.records.append(self.verify(source,refs))
  for snapshot in self.metadata:
   path=ROOT/snapshot['file']
   try:unchanged=hashlib.sha256(path.read_bytes()).hexdigest()==snapshot['sha256']
   except FileNotFoundError:unchanged=False
   if not unchanged:self.claims.append({'kind':'metadata-changed-during-audit','file':snapshot['file'],'expected':snapshot['sha256']})
  failures=[r for r in self.records if r['issues']]
  return {'ok':not(failures or self.claims or self.parse_errors),'catalog':{'version':VERSION,'sha256':MANIFEST_SHA256,'bundles':len(self.catalog['bundles']),'assets':len(self.catalog['assets'])},'scope':'All JSON recursively under construction assets; direct bundle paths, source/sourceSha256, keyed sources/particleSources, catalog bundle records, and embedded APK members. Explicitly excluded diagnostic cache records are recorded separately. No files are modified or fetched.','summary':{'metadataFiles':len(self.metadata),'references':sum(len(v)for v in self.refs.values()),'uniqueSources':len(self.records),'verifiedSourceVersion':sum(r.get('status')=='source-version'for r in self.records),'embeddedNonBundle':sum(r.get('status')=='apk-embedded-non-bundle'for r in self.records),'sharedShaderExceptions':sum(r.get('status')=='official-shared-shader-exception'for r in self.records),'bundleFailures':len(failures),'metadataClaimFailures':len(self.claims),'parseFailures':len(self.parse_errors)},'failures':[{'source':r['source'],'issues':r['issues'],'foundInVersion':r.get('foundInVersion'),'bundleName':r.get('bundleName'),'expectedReplacement':r.get('expectedReplacement'),'metadata':sorted({ref['file']for ref in r['references']})}for r in failures],'metadataClaimFailures':self.claims,'parseFailures':self.parse_errors,'excludedDiagnosticRecords':self.excluded_diagnostics,'metadataSnapshots':self.metadata,'sources':self.records}

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--apk',type=Path,default=DEFAULT_APK)
 parser.add_argument('--assets',type=Path,default=ROOT/'assets/construction')
 parser.add_argument('--cache',type=Path,default=ANALYSIS/'downloaded')
 parser.add_argument('--manifest',type=Path,default=ANALYSIS/'remote-Base_1.4.93.1.bytes')
 parser.add_argument('--compare-manifest',type=Path,default=ANALYSIS/'remote-Base_1.4.93.9.bytes')
 parser.add_argument('--metadata',nargs='+',help='Optional metadata paths relative to construction assets; omitted for the full audit')
 parser.add_argument('--output',type=Path,default=ROOT/'outputs/construction-audit/bundle-version-audit.json')
 args=parser.parse_args();audit=Audit(args);report=audit.run();report['apkSha256']=audit.apk_sha256
 if args.metadata:report['scope']='Selected metadata only: '+', '.join(args.metadata)
 args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'ok':report['ok'],**report['summary'],'output':str(args.output)},ensure_ascii=False));raise SystemExit(0 if report['ok']else 1)

if __name__=='__main__':main()
