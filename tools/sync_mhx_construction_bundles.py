"""Fetch only original catalog assets used by construction and their dependencies.

The read-only public fetcher derives original endpoints from APK UpdateSetting;
URLs and credentials are never serialized in the project.
"""
import argparse,concurrent.futures,hashlib,json,re,sys,zipfile,threading
import requests
from pathlib import Path
from mhx_public_resources import PublicBundleSource
from export_mhx_construction_scene import OUT,CACHE,APK,package_bytes,write_json
import UnityPy

class PooledPublicBundleSource(PublicBundleSource):
    def __init__(self,*args,**kwargs):self._sessions=threading.local();super().__init__(*args,**kwargs)
    def get_public(self,filename):
        if '/'in filename or '\\'in filename or '?'in filename or '..'in filename:raise ValueError('only original manifest filenames may be fetched')
        session=getattr(self._sessions,'session',None)
        if session is None:session=self._sessions.session=requests.Session()
        statuses=[]
        for index,root in enumerate(self.roots):
            response=session.get(root+filename,timeout=(8,45))
            if response.status_code in (401,403):raise PermissionError('original public resource endpoint denied access; no authorization retry')
            if response.status_code==200:return response.content
            statuses.append((index,response.status_code))
        raise FileNotFoundError('original public resource unavailable: '+filename+' '+str(statuses))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--download',action='store_true');parser.add_argument('--workers',type=int,default=8);args=parser.parse_args();source=PooledPublicBundleSource();scene=json.loads((OUT/'scene.json').read_text('utf8'))
    normalize=lambda n:re.sub(r'_skin\d+','_skin',n.lower());required={'assets/bundleresources/'+u['prefabPath'].lower()for u in scene['units'].values()};stems={normalize(n)for n in required};assets=[r for r in source.catalog['assets']if normalize(r['path'])in stems];present={r['path'].lower()for r in assets};missing=sorted(required-present)
    coverage=json.loads((OUT/'npc-resource-coverage.json').read_text('utf8'));qroles=set(coverage['all47Stages']['neededQRoles']);portrait_data=json.loads((OUT/'portraits/npc-animations.json').read_text('utf8'));portraits={int(k.removeprefix('npc_'))for k in portrait_data['roles']}
    def character_asset(path):
        match=re.search(r'/spines/role/q_npc_(\d+)/',path.lower())
        if match:return int(match[1])in qroles
        match=re.search(r'/spines/bustrole(?:prefab/npc_(\d+)\.prefab|/npc_(\d+)/)',path.lower())
        return bool(match and int(match[1]or match[2])in portraits)
    character_assets=[r for r in source.catalog['assets']if character_asset(r['path'])]
    bundles=sorted({i for r in [*assets,*character_assets]for i in source.closure(r)});apk_names=source._apk_names;network=[]
    for i in bundles:
        b=source.catalog['bundles'][i];p=source.destination/b['hash'][:2]/b['hash']/'__data';filename=b['hash']+Path(b['name']).suffix
        if 'assets/Bundles/Android/Base/'+filename not in apk_names and not p.exists():network.append(i)
    report={'catalogVersion':source.version,'catalogSHA256':source.catalog['sha256'],'units':len(scene['units']),'defaultPrefabPaths':len(required),'matchingVariantAssets':len(assets),'characterAssets':len(character_assets),'requiredBundles':len(bundles),'requiredBytes':sum(source.catalog['bundles'][i]['size']for i in bundles),'newBundles':len(network),'newBytes':sum(source.catalog['bundles'][i]['size']for i in network),'absentDefaultAssets':missing,'downloaded':False};write_json(OUT/'bundle-sync.json',report);print(json.dumps({k:v for k,v in report.items()if k!='absentDefaultAssets'}),flush=True)
    if not args.download:return
    paths=[];failures=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers)as pool:
        futures={pool.submit(source.ensure_bundle,i):i for i in bundles}
        for count,f in enumerate(concurrent.futures.as_completed(futures),1):
            i=futures[f]
            try:paths.append(f.result())
            except Exception as e:failures.append({'hash':source.catalog['bundles'][i]['hash'],'errorType':type(e).__name__,'error':str(e)if isinstance(e,(ValueError,FileNotFoundError,PermissionError))else'network request failed'})
            if count%100==0:print(json.dumps({'checked':count,'total':len(bundles),'failures':len(failures)}),flush=True)
    extra=Path(r'C:\dev\mhxcz-analysis\story-cdn-assets.json')
    if extra.exists():paths.extend(s for a in json.loads(extra.read_text('utf8'))['assets']for s in a.get('sources',[]))
    known=json.loads(CACHE.read_text('utf8'));by_source={r['source']:r for r in known};added=[]
    with zipfile.ZipFile(APK)as archive:
        for path in set(paths):
            if path in by_source:continue
            env=UnityPy.load(package_bytes(path,archive));record={'source':path,'assets':[{'name':a.name,'external':[e.path.rsplit('/',1)[-1]for e in a.externals]}for a in env.assets],'containers':[]}
            for obj in env.objects:
                if obj.type.name=='AssetBundle':record['containers']+=[n for n,_ in obj.read().m_Container]
            by_source[path]=record;added.append(record)
    # Re-read immediately before the atomic replace to retain a sibling's additions.
    for record in json.loads(CACHE.read_text('utf8')):by_source[record['source']]=record
    write_json(CACHE,list(by_source.values()));report.update(downloaded=True,verifiedBundles=len(paths),addedIndexRecords=len(added),failures=failures);write_json(OUT/'bundle-sync.json',report);print(json.dumps({'downloaded':True,'verifiedBundles':len(paths),'addedIndexRecords':len(added),'failures':failures}),flush=True)

if __name__=='__main__':main()
