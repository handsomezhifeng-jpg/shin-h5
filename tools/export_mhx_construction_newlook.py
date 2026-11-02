"""Extract the separate source construction-completion effect and dependencies."""
from pathlib import Path
import hashlib
import json
import math
import copy
import argparse
import sys
parser=argparse.ArgumentParser();parser.add_argument('--source-term',default='_mapgame_prefab_fx_animation_newlook.bytes');parser.add_argument('--asset-path');parser.add_argument('--output',default='newlook.json');parser.add_argument('--duration',type=float,default=1.75);args=parser.parse_args()

HERE=Path(__file__).resolve().parent
ns={'__file__':str(HERE/'export_mhx_construction_ui.py')}
exec(compile((HERE/'export_mhx_construction_ui.py').read_text(encoding='utf8').split('\nselected = []',1)[0],str(HERE/'export_mhx_construction_ui.py'),'exec'),ns)
catalog_evidence=None
if args.asset_path:
    sys.path.insert(0,r'C:\dev\mhxcz-analysis')
    from public_bundle_source import PublicBundleSource
    public=PublicBundleSource();asset=public.asset(args.asset_path)
    closure=public.closure(asset)
    # The old device cache can contain different builds with identical CAB names.
    # Resolve this export only through the APK-matched catalog dependency closure.
    ns['cabinet_sources'].clear()
    for bundle_id in closure:
        raw_source=public.ensure_bundle(bundle_id);path=raw_source[4:] if raw_source.startswith('apk:') else raw_source
        row=(path,[public.catalog['bundles'][bundle_id]['name']],'apk' if raw_source.startswith('apk:') else 'download')
        if path not in ns['by_source']:ns['records'].append(row)
        ns['by_source'][path]=row
        bundle=ns['UnityPy'].load(ns['source_bytes'](path))
        for outer in bundle.files.values():
            for file in ns['serialized_files'](outer):ns['cabinet_sources'][file.name.lower()]=path
    raw_source=public.ensure_bundle(asset['bundleId']);source=raw_source[4:] if raw_source.startswith('apk:')else raw_source
    catalog_evidence={'version':public.catalog['version'],'sha256':public.catalog['sha256'],'assetPath':asset['path'],'bundles':[{'name':public.catalog['bundles'][i]['name'],'md5':public.catalog['bundles'][i]['hash'],'size':public.catalog['bundles'][i]['size']}for i in closure]}
else:source=next(p for p,names,_ in ns['records'] if any(args.source_term in n for n in names))
ns['load'](source)
prefab=None
for file in list(ns['environment'].cabs.values()):
    if not isinstance(file,ns['SerializedFile']) or ns['cabinet_sources'].get(file.name.lower())!=source:continue
    for obj in file.objects.values():
        if obj.type.name!='AssetBundle':continue
        for path,row in ns['read_tree'](obj).get('m_Container',[]):
            go=ns['resolve'](row['asset'],file)
            if go and go.type.name=='GameObject':
                prefab=ns['node'](go);prefab['assetPath']=path
if prefab is None:raise RuntimeError('Original animation_newlook prefab not found')
clips={};bindings={};particles=[];spritekeys=set()
def walk(n):
    yield n
    for c in n.get('children',[]):yield from walk(c)
for n in walk(prefab):
    for c in n['components']:
        fields=c['fields']
        if c['type']=='Animation':
            cab,pid=c['sourceObject'].rsplit(':',1);file=ns['environment'].get_cab(cab)
            names=[];default=None
            for ref in fields.get('m_Animations',[]):
                obj=ns['resolve'](ref,file)
                if not obj:continue
                t=ns['read_tree'](obj);name=t['m_Name'];names.append(name)
                if ref==fields.get('m_Animation'):default=name
                curves={k:copy.deepcopy(t.get(k,[]))for k in ['m_FloatCurves','m_RotationCurves','m_PositionCurves','m_ScaleCurves','m_EulerCurves','m_PPtrCurves']}
                m=t['m_MuscleClip']
                clips[name]=dict(name=name,duration=m['m_StopTime']-m['m_StartTime'],sampleRate=t['m_SampleRate'],wrapMode=t['m_WrapMode'],curves=curves,sourceObject=ns['identity'](obj))
            bindings[n['path']]=dict(default=default,clips=names,playAutomatically=fields.get('m_PlayAutomatically'))
        elif c['type']=='ParticleSystem':particles.append(dict(path=n['path'],fields=fields,sourceObject=c['sourceObject']))
        if c.get('m_Sprite'):spritekeys.add(c['m_Sprite'])
def safe(v):
    if isinstance(v,float) and not math.isfinite(v):return str(v)
    if isinstance(v,dict):return{k:safe(x)for k,x in v.items()}
    if isinstance(v,(tuple,list)):return[safe(x)for x in v]
    return v
data=dict(source=source,sourceSha256=hashlib.sha256(ns['source_bytes'](source)).hexdigest(),prefab=prefab,clips=clips,animationBindings=bindings,sprites={k:ns['sprites'][k]for k in spritekeys},particleSettings=particles,duration=args.duration,durationEvidence='Original source caller lifetime: PerformScripts.PlayUnitsUnlockByUnlockVo newlook1.75; GameUtils fly goods terminal boom0.5; fly icon terminal boom0.2.',limitations=[])
if args.output.startswith('unitfx-'):
    data['durationEvidence']='Game/MapGame/Scripts/Perform/PerformScripts.lua: NormalStar showFXFunction returns after2 game seconds; hideFunction Dust/FireClean/WindClean/StarClean returns pooled FX after1.5 without awaiting it; construction-leader DustClean plays2 game seconds before the same reload/NewLook sequence.'
if catalog_evidence:data['originalCatalog']=catalog_evidence
(ns['OUT']/args.output).write_text(json.dumps(safe(data),ensure_ascii=False,indent=2),encoding='utf8')
deps=(HERE/'export_mhx_hammer_particles.py').read_text(encoding='utf8').replace("HAMMER=OUT/'hammer.json'",'HAMMER=OUT/'+repr(args.output))
exec(compile(deps,str(HERE/'export_mhx_hammer_particles.py'),'exec'),{'__file__':str(HERE/'export_mhx_hammer_particles.py'),'additional_source_records':ns['records'],'additional_cabinet_sources':ns['cabinet_sources']})
p=ns['OUT']/args.output;data=json.loads(p.read_text(encoding='utf8'))
data['particleReplay']['systemCount']=len(particles)
data['particleReplay']['implementedModules']=sorted({k for row in particles for k,v in row['fields'].items()if isinstance(v,dict)and v.get('enabled')})
data['particleReplay']['shaderEvidence']=[p['url']for s in data['particleShaders'].values()for p in s['programs']if p['url'].endswith('-9-0.glsl' if 'Universal'in s['name']else'-9-2.glsl')]
data['particleReplay']['shaderFormula']='The original unmasked GLES fragment body is compiled after WebGL1 declaration adaptation. Universal preserves original dual texture, panning, polar, mask, dissolve and color algebra; UI_add preserves original alpha-premultiplied RGB output.'
data['particleReplay']['remainingDifferences']=['Original source parameters, source texture pixels and fragment shader bodies are retained. Unity native RNG, shape distribution and velocity-limit integration are not bit-identical.','The H5 trail uses120Hz tessellation. Orbital integration and procedural noise follow original parameters but use H5 numerical/procedural functions rather than Unity native internals.','The birth subemitters in goods-boom are co-located at the parent birth at0; the current0.5s source caller lifetime has no later parent births.','Native Unity camera/color-space/depth and UiParticles-to-canvas projection are not reproduced bit for bit. The DOM additive overlay keeps alpha0 while preserving additive RGB.','TimeParameters.x global shader phase is exposed as shaderTimeOrigin; an offline replay cannot recover the source runtime clock.']
data['limitations']=data['particleReplay']['remainingDifferences']
p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(source=source,particles=len(particles),sprites=len(spritekeys),bindings=bindings,clips={k:c['duration']for k,c in clips.items()},shapeTypes=[(p['path'],p['fields'].get('ShapeModule',{}).get('type'))for p in particles]),ensure_ascii=True))
