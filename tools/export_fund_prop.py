from pathlib import Path
import sys,json,struct,math
sys.path.insert(0,'F:/superstar/shin-h5/tools/unity-libs')
import UnityPy
from PIL import Image
ROOT=Path('F:/superstar');OUT=ROOT/'shin-h5';SCENE=OUT/'assets/scene';BASE=ROOT/'client/SHIN/Bundles/WebGL/DP/29877775'
m=json.loads((BASE/'PackageManifest_DP_29877775.json').read_text(encoding='utf-8'));asset=next(a for a in m['AssetList'] if a['Address']=='piggy_bank_damagedBase');bundle=m['BundleList'][asset['BundleID']];bundles=[bundle]+[m['BundleList'][i] for i in bundle['DependIDs']];env=UnityPy.load(*[str(BASE/(b['FileHash']+'.bundle')) for b in bundles])
def vec(v):return {k:round(float(getattr(v,k)),9) for k in ['x','y','z']}
def quat(v):return {k:round(float(getattr(v,k)),9) for k in ['x','y','z','w']}
def mesh_data(mesh):
 data=mesh.m_VertexData;raw=bytes(data.m_DataSize);count=data.m_VertexCount;channels=data.m_Channels;formats={0:(4,'f'),1:(2,'e'),2:(1,'B'),3:(1,'b'),4:(2,'H'),5:(2,'h'),6:(1,'B'),7:(1,'b'),8:(2,'H'),9:(2,'h'),10:(4,'I'),11:(4,'i')};strides={}
 for c in channels:
  if c.dimension:strides[c.stream]=max(strides.get(c.stream,0),c.offset+formats[c.format][0]*c.dimension)
 bases={};start=0
 for stream in sorted(strides):bases[stream]=start;start=(start+strides[stream]*count+15)//16*16
 def read(c):
  vals=[]
  for i in range(count):
   values=struct.unpack_from('<'+formats[c.format][1]*c.dimension,raw,bases[c.stream]+i*strides[c.stream]+c.offset)
   vals.extend(round(float(v),8) for v in values)
  return vals
 ib=bytes(mesh.m_IndexBuffer);size,fmt=(2,'H') if mesh.m_IndexFormat==0 else (4,'I');indices=list(struct.unpack('<'+fmt*(len(ib)//size),ib));sub=[]
 for i,s in enumerate(mesh.m_SubMeshes):sub.append({'materialSlot':i,'firstByte':s.firstByte,'indexCount':s.indexCount,'baseVertex':s.baseVertex,'indices':indices[s.firstByte//size:s.firstByte//size+s.indexCount]})
 result={'name':mesh.m_Name,'positions':read(channels[0]),'uv':read(channels[4]),'indices':indices,'subMeshes':sub,'vertexCount':count}
 if channels[1].dimension:result['normals']=read(channels[1])
 return result
objects=[];textures=[];issues=[]
for obj in env.objects:
 if obj.type.name!='GameObject':continue
 go=obj.read()
 if go.m_Name!='piggy_bank_damagedBase':continue
 comps={c.component.type.name:c.component.read() for c in go.m_Component};tr=comps['Transform'];mesh=comps['MeshFilter'].m_Mesh.read();renderer=comps['MeshRenderer'];materials=[]
 for ptr in renderer.m_Materials:
  material=ptr.read();props=material.m_SavedProperties;texture=None
  try:shader=material.m_Shader.read().m_Name
  except:shader=None
  for name,texenv in props.m_TexEnvs:
   if name!='_MainTex' or not texenv.m_Texture.path_id:continue
   tex=texenv.m_Texture.read();dest=SCENE/'fund'/f'{tex.m_Name}.png';dest.parent.mkdir(parents=True,exist_ok=True)
   source=ROOT/'client/SHIN/Assets/Art/City/Pig/Textures'/(tex.m_Name+'.tga')
   if source.is_file():
    with Image.open(source) as im:im.convert('RGBA').save(dest)
   else:tex.image.save(dest)
   texture={'name':tex.m_Name,'url':str(dest.relative_to(OUT)).replace('\\','/'),'width':tex.m_Width,'height':tex.m_Height,'source':str(source.relative_to(ROOT)).replace('\\','/') if source.is_file() else 'original bundle Texture2D'};textures.append(texture)
  colors={name:{key:getattr(value,key) for key in ['r','g','b','a']} for name,value in props.m_Colors};floats={name:float(value) for name,value in props.m_Floats}
  materials.append({'name':material.m_Name,'shader':shader,'texture':texture,'colors':colors,'floats':floats,'isShadow':material.m_Name=='PigShadow'})
 objects.append({'name':go.m_Name,'position':vec(tr.m_LocalPosition),'rotation':quat(tr.m_LocalRotation),'scale':vec(tr.m_LocalScale),'mesh':mesh_data(mesh),'materials':materials})
assert len(objects)==1
layout=json.loads((SCENE/'maincity-layout.json').read_text(encoding='utf-8'))
objects[0]['runtimeTransform']={'position':{'x':0,'y':0,'z':0},'rotation':{'x':0,'y':0,'z':0,'w':1},'scale':objects[0]['scale']}
runtime_matrix=layout['nodes']['Fund']['matrixInMainCityRoot'].copy()
for col,axis in enumerate(['x','y','z']):
 for row in range(4):runtime_matrix[col*4+row]*=objects[0]['scale'][axis]
result={'source':asset['AssetPath'],'sourceBundle':bundle['FileHash']+'.bundle','placement':layout['nodes']['Fund'],'objects':objects,'textures':textures,'runtimeMatrixInMainCityRoot':runtime_matrix,'issues':issues,'notes':['Original default Fund prefab, not a money icon.','Mesh has ONE submesh and TWO renderer materials; extra PigShadow material re-renders the last submesh using its shadow shader. Do not apply the pig atlas as a second body pass.','Source root position/rotation are overridden by ChessboardManager.InitFund and RefreshFund: local position zero, rotation identity, original scale10 retained. Use runtimeMatrixInMainCityRoot or placement multiplied by runtimeTransform.','Placement is relative to MainCityRoot, not the scaled/rotated Chessboard subtree.']}
(SCENE/'fund-prop.json').write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
print(json.dumps({'object':objects[0]['name'],'vertices':objects[0]['mesh']['vertexCount'],'subMeshes':len(objects[0]['mesh']['subMeshes']),'materials':[m['name'] for m in objects[0]['materials']],'textures':textures,'rootTRS':{k:objects[0][k] for k in ['position','rotation','scale']},'placement':layout['nodes']['Fund']['local']},ensure_ascii=False))