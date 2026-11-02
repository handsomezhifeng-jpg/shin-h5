"""APK-matched YooAsset catalog and public read-only bundle fetches.

No credentials, authorization headers, URL tokens, or alternate guessed endpoints.
The original URL roots are read from APK UpdateSetting; no URL is serialized.
"""
from pathlib import Path
import argparse,hashlib,json,os,struct,threading,uuid,zipfile
import requests,UnityPy

DEFAULT_APK=Path(r'C:\Users\zhfzhang\Downloads\梦幻消除战.apk')
ANALYSIS=Path(r'C:\dev\mhxcz-analysis')

class Reader:
 def __init__(self,data):self.data=data;self.pos=0
 def number(self,fmt):
  value=struct.unpack_from(fmt,self.data,self.pos)[0];self.pos+=struct.calcsize(fmt);return value
 def string(self):
  size=self.number('<H');value=self.data[self.pos:self.pos+size].decode('utf8');self.pos+=size;return value
 def strings(self):return[self.string()for _ in range(self.number('<H'))]
 def ints(self):return[self.number('<i')for _ in range(self.number('<H'))]

def parse_catalog(data):
 r=Reader(data)
 if r.number('<I')!=0x594f4f:raise ValueError('unexpected original YooAsset manifest signature')
 result={'fileVersion':r.string(),'enableAddressable':bool(r.number('<B')),'locationToLower':bool(r.number('<B')),'includeAssetGUID':bool(r.number('<B')),'outputNameStyle':r.number('<i'),'buildBundleType':r.number('<i'),'pipeline':r.string(),'packageName':r.string(),'version':r.string(),'note':r.string()}
 count=r.number('<i')
 if not 0<=count<1000000:raise ValueError('invalid original manifest asset count')
 result['assets']=[{'address':r.string(),'path':r.string(),'guid':r.string(),'tags':r.strings(),'bundleId':r.number('<i'),'dependencies':r.ints()}for _ in range(count)]
 count=r.number('<i')
 if not 0<=count<1000000:raise ValueError('invalid original manifest bundle count')
 result['bundles']=[{'name':r.string(),'unityCRC':r.number('<I'),'hash':r.string(),'crc':r.string(),'size':r.number('<q'),'encrypted':bool(r.number('<B')),'tags':r.strings(),'dependencies':r.ints()}for _ in range(count)]
 if r.pos!=len(data):raise ValueError('original manifest tail mismatch')
 result['sha256']=hashlib.sha256(data).hexdigest();return result

def original_roots(apk):
 with zipfile.ZipFile(apk)as z:
  env=UnityPy.Environment();env.load_file(z.read('assets/bin/Data/sharedassets0.assets.split0')+z.read('assets/bin/Data/sharedassets0.assets.split1'),name='sharedassets0.assets')
  raw=next(obj.get_raw_data()for obj in env.objects if obj.type.name=='MonoBehaviour'and b'UpdateSetting'in obj.get_raw_data())
  pos=(32+struct.unpack_from('<I',raw,28)[0]+3)&~3;values=[]
  for _ in range(3):
   length=struct.unpack_from('<I',raw,pos)[0];pos+=4;values.append(raw[pos:pos+length].decode('utf8'));pos=(pos+length+3)&~3
  env=UnityPy.load(z.read('assets/bin/Data/globalgamemanagers'));manager=next(obj for obj in env.objects if obj.type.name=='ResourceManager');ptr=next(ref for name,ref in manager.read_typetree()['m_Container']if name=='version');filename=manager.assets_file.externals[ptr['m_FileID']-1].path
  version_file=UnityPy.load(z.read('assets/bin/Data/'+filename));version=next(obj.read().m_Script for obj in version_file.objects if obj.path_id==ptr['m_PathID']);server=version.split('.')[4]
 # Native evidence: UpdateSetting.GetResDownLoadPath concatenates Server + '/' + Android;
 # RemoteServices.GetRemoteMainURL concatenates host + '/Base/' + original filename.
 return [base.rstrip('/')+'/'+server+'/Android/Base/'for base in values[1:]]

class PublicBundleSource:
 def __init__(self,apk=DEFAULT_APK,version='1.4.93.1',destination=ANALYSIS/'downloaded',manifest_directory=ANALYSIS):
  self.apk=Path(apk);self.version=version;self.destination=Path(destination);self.roots=original_roots(self.apk)
  self.manifest_path=Path(manifest_directory)/('remote-Base_'+version+'.bytes');self.manifest_path.parent.mkdir(parents=True,exist_ok=True)
  if not self.manifest_path.exists():self.manifest_path.write_bytes(self.get_public('Base_'+version+'.bytes'))
  self.catalog=parse_catalog(self.manifest_path.read_bytes())
  if self.catalog['version']!=version:raise ValueError('original catalog version differs')
  self.assets={row['path'].lower():row for row in self.catalog['assets']}
  self._apk_names=set(zipfile.ZipFile(self.apk).namelist())
  self._verified={};self._lock=threading.Lock()
 def get_public(self,filename):
  if '/'in filename or '\\'in filename or '?'in filename or '..'in filename:raise ValueError('only original manifest filenames may be fetched')
  statuses=[]
  for index,root in enumerate(self.roots):
   response=requests.get(root+filename,timeout=(8,45))
   if response.status_code in (401,403):raise PermissionError('original public resource endpoint denied access; no authorization retry')
   if response.status_code==200:return response.content
   statuses.append((index,response.status_code))
  raise FileNotFoundError('original public resource unavailable: '+filename+' '+str(statuses))
 def asset(self,path):
  path=str(path).replace('\\','/')
  if not path.lower().startswith('assets/'):path='Assets/BundleResources/'+path
  try:return self.assets[path.lower()]
  except KeyError:raise KeyError('original '+self.version+' asset absent: '+path)from None
 def closure(self,asset):
  ordered=[];seen=set()
  def visit(bundle_id):
   if bundle_id in seen:return
   seen.add(bundle_id)
   for dep in self.catalog['bundles'][bundle_id]['dependencies']:visit(dep)
   ordered.append(bundle_id)
  for bundle_id in [*asset['dependencies'],asset['bundleId']]:visit(bundle_id)
  return ordered
 def ensure_bundle(self,bundle_id):
  bundle=self.catalog['bundles'][bundle_id];key=bundle['hash'];size=bundle['size']
  with self._lock:
   if key in self._verified:return self._verified[key]
  if self.catalog['outputNameStyle']!=0:raise ValueError('unsupported original file naming style')
  filename=key+Path(bundle['name']).suffix
  apk_path='assets/Bundles/Android/Base/'+filename
  if apk_path in self._apk_names:
   with zipfile.ZipFile(self.apk)as z:raw=z.read(apk_path)
   source='apk:'+apk_path
  else:
   target=self.destination/key[:2]/key/'__data'
   if target.exists():raw=target.read_bytes()
   else:
    raw=self.get_public(filename)
    if len(raw)!=size or hashlib.md5(raw).hexdigest()!=key:raise ValueError('original downloaded bundle hash/size mismatch: '+key)
    target.parent.mkdir(parents=True,exist_ok=True);temporary=target.with_name('__data.'+uuid.uuid4().hex+'.tmp');temporary.write_bytes(raw);os.replace(temporary,target)
   source=str(target)
  if len(raw)!=size or hashlib.md5(raw).hexdigest()!=key:raise ValueError('cached bundle differs from original '+self.version+': '+key)
  with self._lock:self._verified[key]=source
  return source
 def ensure_asset(self,path):return[self.ensure_bundle(bundle_id)for bundle_id in self.closure(self.asset(path))]
 def asset_bytes(self,path):
  asset=self.asset(path);source=self.ensure_bundle(asset['bundleId'])
  if source.startswith('apk:'):
   with zipfile.ZipFile(self.apk)as z:return z.read(source[4:])
  return Path(source).read_bytes()

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--apk',type=Path,default=DEFAULT_APK)
 parser.add_argument('--version',default='1.4.93.1')
 parser.add_argument('--destination',type=Path,default=ANALYSIS/'downloaded')
 parser.add_argument('--manifest-directory',type=Path,default=ANALYSIS)
 parser.add_argument('assets',nargs='*',help='Original catalog asset paths to fetch with their dependencies')
 args=parser.parse_args();source=PublicBundleSource(args.apk,args.version,args.destination,args.manifest_directory)
 result={'version':source.version,'assets':len(source.catalog['assets']),'bundles':len(source.catalog['bundles']),'sha256':source.catalog['sha256']}
 if args.assets:result['fetched']=[{'path':path,'sources':source.ensure_asset(path)}for path in args.assets]
 print(json.dumps(result,ensure_ascii=False))
