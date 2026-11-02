"""Export source story/reward/experience UI without rewriting construction ui.json.

Reuses only the definitions section of the existing extractor. No game code runs.
"""
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
definitions = (HERE / 'export_mhx_construction_ui.py').read_text(encoding='utf8').split('\nselected = []', 1)[0]
ns = {'__file__': str(HERE / 'export_mhx_construction_ui.py')}
exec(compile(definitions, str(HERE / 'export_mhx_construction_ui.py'), 'exec'), ns)
ns['IMAGES'] = ns['OUT'] / 'images-story'
ns['IMAGES'].mkdir(exist_ok=True)
allowed = {
    'CommonGoodsListLight', 'GoodNode', 'CommonRewardPopWinDialog',
    'CommonRewardPopop', 'CommonTaskRewardPopup', 'CommonTipsRewardGoods',
    'CommonTipsRewardGoods2', 'PersonalLevelPopUp', 'PersonalLevelUpPopUp',
    'FirstDialogueNode', 'LeftRoleDialogueNode', 'RightRoleDialogueNode',
    'StoryDialogueNode', 'PlotCgBgDialog', 'PlotDialog', 'PlotDialogue', 'PlotUI',
    'TransitionNewAreaUnlockPopup', 'TaskFinishPopup', 'PlotSingleRolePopup',
    'TransitionRestDecorSelectPopUp',
    'UITitleBar','UIFX_Goods_Move','UIFX_Goods_Boom2','UIFX_IconMove','UIFX_IconMoveEnd_Boom',
    'TransitionDecorationConfirm',
}
terms = ('_prefabs_plot.bytes', '_prefabs_common.bytes',
         '_prefabs_common_commonrewardpopwindialog', '_prefabs_common_commonrewardpopop',
         '_prefabs_common_commongoodslistlight', '_prefabs_personaldetails_personallevel',
         '_prefabs_transition_transitionnewareaunlockpopup', '_prefabs_task_taskfinishpopup',
         '_prefabs_transition_transitionrestdecorselectpopup',
         '_prefabs_plot_plotsinglerolepopup')
terms += ('_prefabs_common_uititlebar','_uieffect_uifx_goods_move','_uieffect_uifx_goods_boom2','_uieffect_uifx_iconmove')
terms += ('_prefabs_transition_transitiondecorationconfirm',)
selected = sorted({ns['source_by_bundle_id'][a['bundleId']]for a in ns['public_source'].catalog['assets']if Path(a['path']).suffix.lower()=='.prefab'and Path(a['path']).stem.lower()in {n.lower()for n in allowed}})
for source in selected:
    ns['load'](source)
prefabs = {}
for source in selected:
    for f in list(ns['environment'].cabs.values()):
        if not isinstance(f, ns['SerializedFile']) or ns['cabinet_sources'].get(f.name.lower()) != source:
            continue
        for obj in f.objects.values():
            if obj.type.name != 'AssetBundle':
                continue
            for path, value in ns['read_tree'](obj).get('m_Container', []):
                go = ns['resolve'](value['asset'], f)
                if go and go.type.name == 'GameObject' and ns['read_tree'](go)['m_Name'] in allowed:
                    root = ns['node'](go)
                    root.update(source=source, assetPath=path)
                    prefabs[root['name']] = root

def clean(value):
    if isinstance(value, float) and not math.isfinite(value):
        return 'Infinity' if value > 0 else '-Infinity' if value < 0 else 'NaN'
    if isinstance(value, dict):
        return {k:clean(v) for k,v in value.items()}
    if isinstance(value, (tuple,list)):
        return [clean(v) for v in value]
    return value

def walk(n):
    yield n
    for child in n.get('children', []):
        yield from walk(child)

def clip_data(obj, base):
    data = ns['read_tree'](obj)
    curves = []
    for field,kind,attribute in [('m_FloatCurves','float',None),('m_RotationCurves','rotation','m_LocalRotation'),('m_PositionCurves','position','m_LocalPosition'),('m_ScaleCurves','scale','m_LocalScale'),('m_EulerCurves','euler','m_LocalEulerAngles')]:
        for row in data.get(field, []):
            curve = row['curve']
            curves.append(dict(kind=kind,path=base+('/'+row['path'] if row['path'] else ''),relativePath=row['path'],attribute=row.get('attribute',attribute),classID=row.get('classID'),keys=clean(curve['m_Curve']),preInfinity=curve['m_PreInfinity'],postInfinity=curve['m_PostInfinity'],rotationOrder=curve['m_RotationOrder']))
    m = data['m_MuscleClip']
    source = ns['cabinet_sources'].get(obj.assets_file.name.lower())
    return dict(name=data['m_Name'],bindingBase=base,source=source,sourceObject=ns['identity'](obj),duration=m['m_StopTime']-m['m_StartTime'],startTime=m['m_StartTime'],stopTime=m['m_StopTime'],sampleRate=data['m_SampleRate'],wrapMode=data['m_WrapMode'],loop=m['m_LoopTime'],curves=curves,events=clean(data.get('m_Events',[])),pointerCurveCount=len(data.get('m_PPtrCurves',[])))

animations = {}
raw_images = {}
lua_bindings = {}
for name, root in prefabs.items():
    clips, bindings, defaults = {}, [], []
    paths_by_go = {n['sourceObject']: n['path'] for n in walk(root)}
    prefab_bindings = {}
    for node in walk(root):
        for comp in node.get('components', []):
            cab, pid = comp['sourceObject'].split(':')
            file = ns['environment'].get_cab(cab)
            if comp.get('script') == 'UISwitchImage':
                comp['switchSprites'] = []
                for item in comp['fields'].get('spriteConfigs', []):
                    target = ns['resolve'](item.get('sprite'), file)
                    comp['switchSprites'].append(ns['export_sprite'](target) if target and target.type.name == 'Sprite' else None)
            if comp.get('script') == 'LuaOutlet':
                resolved = {}
                for outlet in comp['fields'].get('outletInfos', []):
                    target = ns['resolve'](outlet['TargetObject'], file)
                    if target:
                        go = target if target.type.name == 'GameObject' else ns['resolve'](ns['read_tree'](target).get('m_GameObject'), target.assets_file)
                        resolved[outlet['Name']] = dict(path=paths_by_go.get(ns['identity'](go)) if go else None,componentType=outlet['ComponentType'],sourceObject=ns['identity'](target))
                prefab_bindings[node['path']] = resolved
            if comp['type'] == 'Animation':
                fields = comp['fields']
                bindings.append(dict(path=node['path'],sourceObject=comp['sourceObject'],fields=fields))
                for ref in fields.get('m_Animations', []):
                    obj = ns['resolve'](ref, file)
                    if obj and obj.type.name == 'AnimationClip':
                        c = clip_data(obj,node['path'])
                        clips[c['name']] = c
                default = ns['resolve'](fields.get('m_Animation'), file)
                if default:
                    defaults.append(dict(path=node['path'],clip=ns['read_tree'](default)['m_Name'],playAutomatically=fields.get('m_PlayAutomatically')))
            if comp.get('script') in ('RawImage','CustomRawImage'):
                obj = ns['resolve'](comp['fields'].get('m_Texture'),file)
                if obj and obj.type.name == 'Texture2D':
                    key = ns['identity'](obj)
                    data = obj.read()
                    filename = 'raw-'+hashlib.sha256(key.encode()).hexdigest()[:12]+'.png'
                    image = data.image
                    image.save(ns['IMAGES']/filename)
                    raw_images[key] = dict(name=data.m_Name,url='assets/construction/images-story/'+filename,width=image.width,height=image.height,sourceObject=key)
                    comp['texture'] = key
    animations[name] = dict(clips=clips,animationBindings=bindings,defaults=defaults,open=[n for n in clips if n.endswith('_Entry') and 'DownGroup' not in n and 'BtnSkip' not in n],close=[n for n in clips if n.endswith('_Out') and 'DownGroup' not in n])
    lua_bindings[name] = prefab_bindings

for sprite in ns['sprites'].values():
    sprite['url'] = sprite['url'].replace('/images-ui/','/images-story/')
    sprite['sha256'] = hashlib.sha256((ns['ROOT']/sprite['url']).read_bytes()).hexdigest()
for row in raw_images.values():
    row['sha256'] = hashlib.sha256((ns['ROOT']/row['url']).read_bytes()).hexdigest()
pack = dict(formatVersion=1,prefabs=prefabs,sprites=ns['sprites'],spritesByName={s['name']:s for s in ns['sprites'].values()},fonts=ns['fonts'],textures=raw_images,animations=animations,luaBindings=lua_bindings,sources=ns['loaded_sources'],unresolved=ns['unknowns'],missingRequestedPrefabs=sorted(allowed-set(prefabs)),notes=['Original prefab active states are authoring data. Lua applies dialogue/state-specific changes.','RenderTexture/camera capture references are preserved as fields; they are not static images.','No ui.json, controller, progress or NPC data was rewritten.'])
target = ns['OUT']/'story-ui.json'
target.write_text(json.dumps(clean(pack),ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
import sys
if '--merge-choice-animation' in sys.argv:
    target_ui=ns['OUT']/'ui.json'
    existing=json.loads(target_ui.read_text(encoding='utf8'))
    existing.setdefault('animations',{})['TransitionRestDecorSelectPopUp']=animations['TransitionRestDecorSelectPopUp']
    target_ui.write_text(json.dumps(clean(existing),ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
print(json.dumps(dict(file=str(target),prefabs={n:len(list(walk(p))) for n,p in prefabs.items()},sprites=len(ns['sprites']),clips={n:len(a['clips']) for n,a in animations.items()},missing=pack['missingRequestedPrefabs'],unknowns=ns['unknowns']),ensure_ascii=False))
