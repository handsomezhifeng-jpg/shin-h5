"""Re-export current UI source data through the APK-matched catalog only.

Preserves controller bindings, animation policies and portrait integration.
Does not run the old all-in-one exporter's NPC side effects.
"""
from pathlib import Path
import json,hashlib,math
HERE=Path(__file__).resolve().parent
ns={'__file__':str(HERE/'export_mhx_construction_ui.py')}
exec(compile((HERE/'export_mhx_construction_ui.py').read_text('utf8').split('\nselected = []',1)[0],str(HERE/'export_mhx_construction_ui.py'),'exec'),ns)
path=ns['OUT']/'ui.json';current=json.loads(path.read_text('utf8'));requested={p['assetPath'].lower():name for name,p in current['prefabs'].items()}
selected={ns['source_by_bundle_id'][ns['public_source'].asset(asset)['bundleId']]for asset in requested}
for source in selected:ns['load'](source)
prefabs={}
for source in selected:
    for file in list(ns['environment'].cabs.values()):
        if not isinstance(file,ns['SerializedFile'])or ns['cabinet_sources'].get(file.name.lower())!=source:continue
        for obj in file.objects.values():
            if obj.type.name!='AssetBundle':continue
            for asset,row in ns['read_tree'](obj).get('m_Container',[]):
                if asset.lower()not in requested:continue
                go=ns['resolve'](row['asset'],file)
                if go and go.type.name=='GameObject':
                    node=ns['node'](go);node.update(source=source,assetPath=asset);prefabs[requested[asset.lower()]]=node
assert set(prefabs)==set(current['prefabs']),(set(current['prefabs'])-set(prefabs))
terms=('_uiatlas_task.bytes','_uiatlas_uihomeview.bytes','_uiatlas_common1.bytes','_uiatlas_common2.bytes','_uiatlas_common3.bytes','_uiatlas_mainicon.bytes','_uiatlas_mainicon2.bytes','_uiatlas_mainicon3.bytes')
for source,names,_ in ns['records']:
    if not any(any(term in name for term in terms)for name in names):continue
    ns['load'](source)
    for file in list(ns['environment'].cabs.values()):
        if not isinstance(file,ns['SerializedFile'])or ns['cabinet_sources'].get(file.name.lower())!=source:continue
        for obj in file.objects.values():
            if obj.type.name=='Sprite':ns['export_sprite'](obj)
def clean(v):
    if isinstance(v,float)and not math.isfinite(v):return 'Infinity'if v>0 else '-Infinity'if v<0 else 'NaN'
    if isinstance(v,dict):return{k:clean(x)for k,x in v.items()}
    if isinstance(v,(list,tuple)):return[clean(x)for x in v]
    return v
current['prefabs']=prefabs;current['sprites']=ns['sprites'];current['spritesByName']={s['name']:s for s in ns['sprites'].values()};current['fonts']=ns['fonts'];current['unknowns']=ns['unknowns']
current['provenance']['sources']=ns['loaded_sources'];current['provenance']['originalCatalog']={k:ns['public_source'].catalog[k]for k in ['version','sha256']}
current['visualBindingNotes']=['Original dynamic currencies102/104 resolve through Goods/Currency.photoId and Module/ResourcesPath; task-content exporter merges their standalone original images after this source UI export.','All UI prefab, atlas and font dependencies in provenance.sources are verified against the APK-matched1.4.93.1 catalog.']
story=json.loads((ns['OUT']/'story-ui.json').read_text('utf8'))
for name in prefabs:
    if name in story['animations']:current.setdefault('animations',{})[name]=story['animations'][name]
for role,key in [('currencyCoin','102'),('currencyExp','104'),('experience','104')]:
    pack=json.loads((ns['OUT']/'task-content.json').read_text('utf8'));record=pack['items'][key];sprite=record['sprite']
    current['sprites'][sprite['sourceObject']]=sprite;current['spritesByName'][sprite['name']]=sprite;current['visualBindings'][role]=sprite['name']
path.write_text(json.dumps(clean(current),ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
print(json.dumps({'prefabs':list(prefabs),'sprites':len(current['sprites']),'fonts':len(current['fonts']),'verifiedSourceBundles':len(ns['loaded_sources']),'unknowns':ns['unknowns']}))
