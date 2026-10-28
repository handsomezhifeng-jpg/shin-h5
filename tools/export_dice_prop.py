from pathlib import Path
import sys,json,struct,math,re,ast
sys.path.insert(0,'F:/superstar/shin-h5/tools/unity-libs')
import UnityPy
from UnityPy.classes.PPtr import PPtr
from PIL import Image
ROOT=Path('F:/superstar');OUT=ROOT/'shin-h5';SCENE=OUT/'assets/scene';BASE=ROOT/'client/SHIN/Bundles/WebGL/DP/29877775'
# Reuse the tested generic mesh decoder without running the pig exporter.
module=ast.parse((OUT/'tools/export_fund_prop.py').read_text(encoding='utf8'))
exec(compile(ast.Module(body=[node for node in module.body if isinstance(node,ast.FunctionDef)],type_ignores=[]),'<mesh decoder>','exec'))
def vertex_colors(mesh):
 data=mesh.m_VertexData;channels=data.m_Channels;c=channels[3]
 if not c.dimension:return [1.0,1.0,1.0,1.0]*data.m_VertexCount
 sizes={0:4,1:2,2:1,3:1,4:2,5:2,6:1,7:1,8:2,9:2,10:4,11:4};fmts={0:'f',1:'e',2:'B',3:'b',4:'H',5:'h',6:'B',7:'b',8:'H',9:'h',10:'I',11:'i'};strides={}
 for ch in channels:
  if ch.dimension:strides[ch.stream]=max(strides.get(ch.stream,0),ch.offset+sizes[ch.format]*ch.dimension)
 start=0;bases={}
 for stream in sorted(strides):bases[stream]=start;start=(start+strides[stream]*data.m_VertexCount+15)//16*16
 raw=bytes(data.m_DataSize);out=[]
 for i in range(data.m_VertexCount):
  vs=list(struct.unpack_from('<'+fmts[c.format]*c.dimension,raw,bases[c.stream]+i*strides[c.stream]+c.offset))
  if c.format in [2,3,4,5]:
   divisor={2:255,3:127,4:65535,5:32767}[c.format];vs=[max(-1,v/divisor) for v in vs]
  out.extend([round(float(v),8) for v in vs]+[1.0]*(4-len(vs)))
 return out
def trs(t):return {'position':vec(t.m_LocalPosition),'rotation':quat(t.m_LocalRotation),'scale':vec(t.m_LocalScale)}
def chain(t):
 a=[]
 while True:
  a.append({'name':t.m_GameObject.read().m_Name,**trs(t)})
  if not t.m_Father.path_id:break
  t=t.m_Father.read()
 return a[::-1]
def pointer(owner,r):return PPtr(m_FileID=r['m_FileID'],m_PathID=r['m_PathID'],assetsfile=owner.assets_file).read()
def numbers(s):return {k:float(v) for k,v in re.findall(r'(\w+):\s*([-+\d.eE]+)',s)}
def val(s):return numbers(s) if s.startswith('{') else float(s)
def qm(a,b):
 x,y,z,w=a;X,Y,Z,W=b
 return [w*X+x*W+y*Z-z*Y,w*Y-x*Z+y*W+z*X,w*Z+x*Y-y*X+z*W,w*W-x*X-y*Y-z*Z]
def eulerq(e):
 x,y,z=[e[k]*math.pi/360 for k in ['x','y','z']]
 q=qm(qm([0,math.sin(y),0,math.cos(y)],[math.sin(x),0,0,math.cos(x)]),[0,0,math.sin(z),math.cos(z)])
 return dict(zip('xyzw',[round(v,9) for v in q]))
def clipdata(name):
 path=ROOT/'client/SHIN/Assets/Art/City/Chessboard/Dice/Animations'/(name+'.anim');s=path.read_text(encoding='utf-8-sig');tracks={}
 for section,property in [('m_PositionCurves','position'),('m_RotationCurves','rotation'),('m_ScaleCurves','scale')]:
  found=re.search(r'^  '+section+r':[^\n]*\n(.*?)(?=^  \w+:|\Z)',s,re.S|re.M)
  if not found:continue
  for block in re.split(r'^  - curve:\s*\n',found.group(1),flags=re.M)[1:]:
   pathmatch=re.search(r'^    path: (.*)$',block,re.M)
   if not pathmatch:continue
   keys=[]
   for raw in re.split(r'^      - serializedVersion: \d+\s*\n',block,flags=re.M)[1:]:
    row={}
    for k in ['time','value','inSlope','outSlope','weightedMode','inWeight','outWeight']:
     v=re.search(r'^        '+k+r': ([^\n]+)',raw,re.M)
     if v:row[k]=val(v.group(1))
    if row:keys.append(row)
   tracks.setdefault(pathmatch.group(1),{})[property]=keys
 duration=float(re.search(r'^    m_StopTime: ([^\n]+)',s,re.M).group(1))
 return {'name':name,'source':str(path.relative_to(ROOT)).replace('\\','/'),'duration':duration,'speed':2,'effectiveDuration':duration/2,'sampleRate':float(re.search(r'^  m_SampleRate: ([^\n]+)',s,re.M).group(1)),'tracks':tracks}
m=json.loads((BASE/'PackageManifest_DP_29877775.json').read_text(encoding='utf8'));assets=[a for a in m['AssetList'] if a['Address'] in ['Dice_44001','DiceRoot_Runtime']];ids=set()
for a in assets:ids.add(a['BundleID']);ids.update(m['BundleList'][a['BundleID']]['DependIDs'])
env=UnityPy.load(*[str(BASE/(m['BundleList'][i]['FileHash']+'.bundle')) for i in sorted(ids)])
objects=[];textures={};controller=None;controller_obj=None
for obj in env.objects:
 if obj.type.name=='MonoBehaviour':
  try:t=obj.read_typetree()
  except:continue
  if '_DiceAnimRotateDatas' in t:controller=t;controller_obj=obj
 if obj.type.name!='GameObject':continue
 go=obj.read()
 if go.m_Name!='Model':continue
 comps={c.component.type.name:c.component.read() for c in go.m_Component};tr=comps.get('Transform')
 if not tr or not tr.m_Father.path_id or tr.m_Father.read().m_GameObject.read().m_Name!='Dice_44001':continue
 mesh=comps['MeshFilter'].m_Mesh.read();materials=[]
 for p in comps['MeshRenderer'].m_Materials:
  mat=p.read();saved=mat.m_SavedProperties;shader_tree=mat.m_Shader.deref().read_typetree();shader=shader_tree.get('m_ParsedForm',{}).get('m_Name') or shader_tree.get('m_Name');texs={}
  for prop,texenv in saved.m_TexEnvs:
   if not texenv.m_Texture.path_id:continue
   texture=texenv.m_Texture.read();dest=SCENE/'dice'/(texture.m_Name+'.png');dest.parent.mkdir(parents=True,exist_ok=True);source=ROOT/'client/SHIN/Assets/Art/City/Chessboard/Dice/Textures'/(texture.m_Name+'.tga')
   if source.is_file():
    with Image.open(source) as im:im.convert('RGBA').save(dest)
   else:texture.image.save(dest)
   entry={'name':texture.m_Name,'url':str(dest.relative_to(OUT)).replace('\\','/'),'width':texture.m_Width,'height':texture.m_Height,'source':str(source.relative_to(ROOT)).replace('\\','/') if source.is_file() else 'original bundle Texture2D'};textures[entry['name']]=entry;texs[prop]={**entry,'scale':{'x':texenv.m_Scale.x,'y':texenv.m_Scale.y},'offset':{'x':texenv.m_Offset.x,'y':texenv.m_Offset.y}}
  colors={name:{key:float(getattr(value,key)) for key in 'rgba'} for name,value in saved.m_Colors};floats={name:float(value) for name,value in saved.m_Floats}
  materials.append({'name':mat.m_Name,'shader':shader,'shaderSource':'client/SHIN/Assets/ResourcesAssets/Shader/Model/'+('Mobile_Model_ShadowNotBatch.shader' if mat.m_Name.lower()=='shadow' else 'Mobile_Model_CarToon.shader'),'textures':texs,'texture':texs.get('_MainTex'),'colors':colors,'floats':floats,'isShadow':mat.m_Name.lower()=='shadow'})
 decoded=mesh_data(mesh);decoded['colors']=vertex_colors(mesh)
 objects.append({'name':go.m_Name,'parentChain':chain(tr),'local':trs(tr),'mesh':decoded,'materials':materials})
assert len(objects)==1 and controller
parents={}
for i in range(1,4):
 tr=pointer(controller_obj,controller['_DiceParent'+str(i)]);parents['Dice'+str(i)]={'local':trs(tr),'parentChain':chain(tr)}
facepath=ROOT/'client/SHIN/Assets/ResourcesAssets/OtherConfig/Dice/DiceFacePoseConfig.asset';facesection=facepath.read_text(encoding='utf8').split('SixFaceEulers:')[1].split('TwelveFaceEulers:')[0];faces=[numbers(row) for row in re.findall(r'\{[^}]+\}',facesection)]
assert len(faces)==6
clips=[clipdata(controller['_DiceVerticalAniDatas'][0]['AniName']),clipdata(controller['_DiceHorizontalAniDatas'][0]['AniName'])]
for c in clips:
 c['authoredLandingFaces']=next([d['Dice1Num'],d['Dice2Num'],d['Dice3Num']] for d in controller['_DiceVerticalAniDatas']+controller['_DiceHorizontalAniDatas'] if d['AniName']==c['name'])
result={'id':44001,'name':'Dice_44001','defaultEvidence':{'file':'client/SHIN/Assets/Script/Game/GlobalValues.cs','definition':'DefaultDiceSkin = 44001'},'defaultConfig':{'dice_skin':{'id':44001,'dice_anim':1,'animationType':'Horizontal','scale':1},'evidence':'Default/dice_skin.bytes: field2=1; GameEnum.DiceAniType.Horizontal=1'},'source':next(a['AssetPath'] for a in assets if a['Address']=='Dice_44001'),'objects':objects,'textures':list(textures.values()),'facePoses':{'source':str(facepath.relative_to(ROOT)).replace('\\','/'),'eulerOrder':'Unity Quaternion.Euler: qY * qX * qZ; degrees','upAxis':'+Y','poses':[{'point':i+1,'euler':e,'quaternion':eulerq(e)} for i,e in enumerate(faces)]},'controller':{'source':'client/SHIN/Assets/ResourcesAssets/Prefabs/Scene/City/DiceRoot_Runtime.prefab','speed':controller['_AnimSpeed'],'parents':parents,'correctionEulers':[row['DiceRotation'] for row in controller['_DiceAnimRotateDatas']],'horizontalVariants':controller['_DiceHorizontalAniDatas'],'verticalVariants':controller['_DiceVerticalAniDatas']},'clips':clips,'notes':['Only the physical default ordinary six-sided dice Model is exported; prefab FX are omitted.','One physical mesh submesh with two renderer materials. shadow is an additional shadow pass, not another body texture.','At runtime DiceController resets the Dice_44001 root local position/rotation/scale to zero/identity/one before applying result correction rotation. Keep Model local transform.','Original playback: animate Dice1/2/3 parent local TRS from clip tracks, then multiply Quaternion.Euler(correctionEulers[authoredLandingFaces[die]-1][wantedPoint-1]), then Model local transform. The third die is hidden if no third result.','Original position and quaternion curves include times, values, and slopes. Translation uses cubic Hermite; quaternion curves use Unity normalized quaternion interpolation. No physics simulation or invented keyframes included.','facePoses are the serialized UI standstill mapping; full throw playback must instead use correctionEulers for its authored landing face.','Two original throw variants are exported (one vertical, one horizontal), each containing all three authored die tracks. All other normal variant names remain in controller lists for provenance.']}
(SCENE/'dice-prop.json').write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf8')
print(json.dumps({'output':'assets/scene/dice-prop.json','vertices':objects[0]['mesh']['vertexCount'],'triangles':len(objects[0]['mesh']['indices'])//3,'materials':[(a['name'],a['shader']) for a in objects[0]['materials']],'textures':list(textures.values()),'modelLocal':objects[0]['local'],'parents':parents,'clips':[{'name':c['name'],'duration':c['duration'],'tracks':{p:{key:len(rows) for key,rows in t.items()} for p,t in c['tracks'].items()}} for c in clips]},ensure_ascii=False))