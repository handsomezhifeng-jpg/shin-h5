#!/usr/bin/env python3
"""Export only the original two board reward coin particle effects."""
from pathlib import Path
import sys,json,ast,struct,math,re,hashlib,shutil
sys.path.insert(0,'F:/superstar/shin-h5/tools/unity-libs')
import UnityPy
from PIL import Image
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parents[1];SCENE=OUT/'assets/scene';BASE=ROOT/'client/SHIN/Bundles/WebGL/DP/29877775'
manifest=json.loads((BASE/'PackageManifest_DP_29877775.json').read_text(encoding='utf8'));wanted=['sfx_xiao_jinbi','sfx_zhong_jinbi'];assets={a['Address']:a for a in manifest['AssetList']if a['Address']in wanted};ids=set()
for a in assets.values():ids.add(a['BundleID']);ids.update(manifest['BundleList'][a['BundleID']]['DependIDs'])
files=[]
for i in sorted(ids):
 b=manifest['BundleList'][i];path=BASE/(b['FileHash']+'.bundle')
 if not path.is_file():path=ROOT/'client/SHIN/Assets/StreamingAssets/yoo/DP'/(b['FileHash']+'.bundle')
 assert path.is_file(),str(path)
 files.append(str(path))
env=UnityPy.load(*files)
for filename,fnames in [('export_fund_prop.py',{'mesh_data'}),('export_dice_prop.py',{'vertex_colors'})]:
 module=ast.parse(Path(__file__).with_name(filename).read_text(encoding='utf8'))
 exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef)and n.name in fnames],type_ignores=[]),filename,'exec'))
def vec(v):return {k:float(getattr(v,k))for k in 'xyz'}
def trs(t):return {'position':vec(t.m_LocalPosition),'rotation':{k:float(getattr(t.m_LocalRotation,k))for k in 'xyzw'},'scale':vec(t.m_LocalScale)}
def chain(t):
 a=[]
 while True:
  a.append({'name':t.m_GameObject.read().m_Name,**trs(t)})
  if not t.m_Father.path_id:break
  t=t.m_Father.read()
 return a[::-1]
def clean(v):
 if isinstance(v,float)and not math.isfinite(v):return str(v)
 if isinstance(v,dict):return {k:clean(x)for k,x in v.items()}
 if isinstance(v,(list,tuple)):return [clean(x)for x in v]
 return v
meshes={};materials={};textures={};effects={};sources=[]
def tex_export(tex):
 key=tex.m_Name
 if key in textures:return key
 source=ROOT/'client/SHIN/Assets/Art/UI_Effect/EF_TexRepeat'/(key+'.png');dest=SCENE/'coin-fx'/(key+'.png');dest.parent.mkdir(parents=True,exist_ok=True)
 if source.is_file():shutil.copy2(source,dest);provenance=source.relative_to(ROOT).as_posix()
 else:tex.image.save(dest);provenance='original bound bundle Texture2D'
 with Image.open(dest)as im:width,height=im.size;alpha=im.convert('RGBA').getchannel('A').getextrema()
 textures[key]={'url':dest.relative_to(OUT).as_posix(),'width':width,'height':height,'source':provenance,'alphaRange':list(alpha),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()};return key

def material_export(mat):
 key=mat.m_Name
 if key in materials:return key
 props=mat.m_SavedProperties;st=mat.m_Shader.deref().read_typetree();shader=st.get('m_ParsedForm',{}).get('m_Name')or st.get('m_Name');texs={}
 for name,te in props.m_TexEnvs:
  if te.m_Texture.path_id:texs[name]={'texture':tex_export(te.m_Texture.read()),'scale':{'x':te.m_Scale.x,'y':te.m_Scale.y},'offset':{'x':te.m_Offset.x,'y':te.m_Offset.y}}
 materials[key]={'name':key,'source':'client/SHIN/Assets/Art/UI_Effect/EF_Materials/'+key+'.mat','shader':shader,'shaderSource':'client/SHIN/Assets/ResourcesAssets/Shader/Model/Mobile_NPR_Metallic.shader','renderQueue':mat.m_CustomRenderQueue,'effectiveRenderQueue':3000,'colors':{name:{k:float(getattr(value,k))for k in 'rgba'}for name,value in props.m_Colors},'floats':{name:float(v)for name,v in props.m_Floats},'textures':texs,'renderState':{'blendSrc':'SRC_ALPHA','blendDst':'ONE_MINUS_SRC_ALPHA','depthWrite':False,'depthTest':'LEQUAL','cull':'BACK'}}
 return key
for obj in env.objects:
 if obj.type.name!='GameObject':continue
 go=obj.read();components={c.component.type.name:c.component.deref()for c in go.m_Component}
 if 'ParticleSystem'not in components:continue
 tr=components['Transform'].read();path=chain(tr);name=path[0]['name']
 if name not in wanted:continue
 p=components['ParticleSystem'].read_typetree();r=components['ParticleSystemRenderer'].read();rt=components['ParticleSystemRenderer'].read_typetree();mesh=r.m_Mesh.read();mname=mesh.m_Name
 if mname not in meshes:
  decoded=mesh_data(mesh);decoded['colors']=vertex_colors(mesh);meshes[mname]=decoded
 assert r.m_RenderMode==4 and not p['UVModule']['enabled'],'Unexpected original effect representation'
 source=ROOT/'client/SHIN'/assets[name]['AssetPath'];bundle=manifest['BundleList'][assets[name]['BundleID']]
 effect=effects.setdefault(name,{'source':source.relative_to(ROOT).as_posix(),'sourceSHA256':hashlib.sha256(source.read_bytes()).hexdigest(),'sourceBundle':bundle['FileHash']+'.bundle','root':path[0],'systems':[]})
 attrs={k:rt[k]for k in ['m_RenderMode','m_RenderAlignment','m_SortMode','m_SortingOrder','m_SortingLayerID','m_SortingFudge','m_MinParticleSize','m_MaxParticleSize','m_Pivot','m_Flip','m_NormalDirection','m_EnableGPUInstancing','m_ApplyActiveColorSpace','m_AllowRoll','m_VertexStreams']if k in rt}
 initial=p['InitialModule'];emit=p['EmissionModule']
 effect['systems'].append({'name':go.m_Name,'path':[n['name']for n in path],'local':trs(tr),'parentChain':path,'active':bool(go.m_IsActive),'mesh':mname,'materials':[material_export(ptr.read())for ptr in r.m_Materials],'renderer':attrs,'particleSystem':p,'summary':{'representation':'mesh','duration':p['lengthInSec'],'simulationSpeed':p['simulationSpeed'],'looping':p['looping'],'simulationSpace':'world'if p['moveWithTransform']==0 else 'local','maxParticles':initial['maxNumParticles'],'burstRequestedCount':emit['m_Bursts'][0]['countCurve']['scalar'],'burstEffectiveInitialCount':min(initial['maxNumParticles'],int(emit['m_Bursts'][0]['countCurve']['scalar'])),'lifetime':[initial['startLifetime']['minScalar'],initial['startLifetime']['scalar']],'speed':[initial['startSpeed']['minScalar'],initial['startSpeed']['scalar']],'startSize':[initial['startSize']['minScalar'],initial['startSize']['scalar']],'enabledModules':[k for k,v in p.items()if isinstance(v,dict)and v.get('enabled')],'textureSheetEnabled':False}})
assert set(effects)==set(wanted)and all(len(e['systems'])==1 for e in effects.values())

# The published material has a null cubemap pointer. Its shader default is white.
# Preserve the source reference image separately for diagnosis; it is NOT bound at runtime.
cube_source=ROOT/'client/SHIN/Assets/Art/UI_Effect/EF_TexRepeat/cube09.psd';cube_output=SCENE/'coin-fx/cube09-source-reference.png'
with Image.open(cube_source)as original_cube:original_cube.convert('RGBA').save(cube_output)
materials['tex_coin_jinbi_d']['cubeMapEvidence']={'bundleBinding':None,'shaderDefault':'white','effectiveDefaultSampleRGBA':[1,1,1,1],'reflectionStillApplied':True,'sourceMaterialDeclaredGUID':'27a9aa5cb4c216949ad82145a99e29ba','sourceMaterialDeclaredFileID':8900000,'dependencyTextureName':'cube09','dependencyType':'Texture2D','dependencyDimensions':[384,512],'dependencyTextureDimension':2,'dependencyImageCount':1,'sourceImporterTextureShape':1,'originalReferenceImage':{'url':cube_output.relative_to(OUT).as_posix(),'source':cube_source.relative_to(ROOT).as_posix(),'width':384,'height':512,'runtimeBound':False},'sixFacesExported':False,'reason':'No Cubemap object in the declared effect bundles. Published material _CubeMap PPtr is zero. cube09 exists only as a 2D dependency texture, not six published cubemap faces.'}

physics=ROOT/'client/SHIN/ProjectSettings/DynamicsManager.asset';physics_text=physics.read_text(encoding='utf-8-sig');gravity={k:float(v)for k,v in re.findall(r'(\w+):\s*([-+\d.eE]+)',re.search(r'm_Gravity: (\{[^}]+\})',physics_text).group(1))}
result={'effects':effects,'meshes':meshes,'materials':materials,'textures':textures,'physics':{'source':physics.relative_to(ROOT).as_posix(),'gravity':gravity},'runtimePlacement':{'source':'client/SHIN/Assets/Script/Game/moduls/Chessboard/Square/SquareBase.cs:317-327','position':'Center.position + worldUp * 0.1521','rotation':'Quaternion.LookRotation((mainCamera.position-worldPos).normalized, mainCamera.up)','scale':{'x':1,'y':1,'z':1},'recycleAfterSeconds':2,'chooseMediumEffectWhen':'resultData.endPos == 1','poolSource':'client/SHIN/Assets/Script/Game/moduls/Common/Effect/SceneEffectManager.cs:47-53'},'notes':['Original effects are ParticleSystem mesh particles using Cylinder002; not billboard sprites or texture-sheet animation. No artwork or trajectories have been generated.','Exact original serialized ParticleSystem fields/modules, Hermite curves and gradients are preserved under each systems[].particleSystem. Inactive modules are retained with enabled:false, not applied.','MinMaxCurve modes: 0 Constant (scalar), 1 Curve (maxCurve multiplied by scalar), 2 TwoCurves, 3 TwoConstants (minScalar..scalar). Curve times use normalized particle lifetime for lifetime modules; emission burst time is seconds.','UVModule is disabled with 1x1 tiles. No coin atlas frame animation should be introduced.','Burst requested count is 65 for both originals, but InitialModule.maxNumParticles caps initial spawn at 12 (small) or 25 (medium).','InitialModule.size3D=false means startSizeY/Z do not apply. Initial rotation3D=false; RotationModule and RotationBySpeedModule still contain their own separate-axis data.','ShapeModule.type=4 is the original serialized cone type. Its cone axis is emitter local +Z. Respect local child rotation (-13 degrees X), and the runtime root LookRotation toward the camera.','Gravity modifier is an authored curve; use ProjectSettings gravity (0,-9.81,0) and its scalar. ClampVelocityModule is enabled with magnitude1 and dampen.05, so motion is not an unconstrained ballistic parabola.','Particle material is metallic NPR shading with original colors/roughness/specular settings. Its shader returns lit RGB with alpha1 multiplied by particle vertex color, not texture alpha. Do not substitute the ordinary tile Unlit or add a flat coin icon.','Published material _CubeMap is null. Mobile_NPR_Metallic.shader declares the Cube property default white, so use RGBA(1,1,1,1) for its sample, multiplied by CubeMapIntensity0.8 and Metallic0.4; do not drop the reflection or replace it with black. Source cube09 PSD is exported only as an unbound reference image, not invented six-face runtime data.','Serialized source prefab SHA256 and bound bundle hash are included. Sources are read-only; no other scene resource or FGUI manifest is rebuilt.']}
dest=SCENE/'coin-fx.json';dest.write_text(json.dumps(clean(result),ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n',encoding='utf8')
print(json.dumps({'output':dest.relative_to(OUT).as_posix(),'bytes':dest.stat().st_size,'effects':{name:e['systems'][0]['summary']for name,e in effects.items()},'meshes':{name:{'vertices':m['vertexCount'],'triangles':len(m['indices'])//3}for name,m in meshes.items()},'materials':list(materials),'textures':textures},ensure_ascii=False))