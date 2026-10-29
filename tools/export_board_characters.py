"""Export only original board friend-rent avatar prop; no invented character art."""
from pathlib import Path
import sys,json,struct,math,re,ast,shutil
sys.path.insert(0,str(Path(__file__).parent/'unity-libs'))
import UnityPy
from PIL import Image
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'shin-h5';SCENE=OUT/'assets/scene';DEST=SCENE/'board-characters';DEST.mkdir(parents=True,exist_ok=True);BASE=ROOT/'client/SHIN/Bundles/WebGL/DP/29877775'
for filename,allowed in [('export_fund_prop.py',None),('export_board_motion.py',{'numeric','curve_list','clip'})]:
 module=ast.parse((OUT/'tools'/filename).read_text(encoding='utf8'));nodes=[n for n in module.body if isinstance(n,ast.FunctionDef)and(allowed is None or n.name in allowed)];exec(compile(ast.Module(body=nodes,type_ignores=[]),filename,'exec'))
ANIMS=ROOT/'client/SHIN/Assets/Art/UI_Effect/EF_Animations'
m=json.loads((BASE/'PackageManifest_DP_29877775.json').read_text(encoding='utf8'));asset=next(a for a in m['AssetList']if a['Address']=='FriendHeadIcon');bundle=m['BundleList'][asset['BundleID']];files=[BASE/(b['FileHash']+'.bundle')for b in [bundle]+[m['BundleList'][i]for i in bundle['DependIDs']]];env=UnityPy.load(*map(str,files))
builtin=Path('C:/Program Files/Unity 2022.3.25f1/Editor/Data/Resources/unity default resources');builtinenv=UnityPy.load(str(builtin));builtinmesh=next(o.read()for o in builtinenv.objects if o.type.name=='Mesh'and o.path_id==10206);assert builtinmesh.m_Name=='Cylinder';mesh=mesh_data(builtinmesh);mesh['source']={'path':str(builtin),'fileID':10206,'note':'Original prefab references engine builtin Cylinder fileID10206. Installed Unity2022.3.25f1 builtin resource supplies the actual mesh; source project version is Tuanjie2022.3.55t4. No generated approximation.'}

def trs(t):return {'position':vec(t.m_LocalPosition),'rotation':quat(t.m_LocalRotation),'scale':vec(t.m_LocalScale)}
def chain(t):
 rows=[]
 while True:
  rows.append({'name':t.m_GameObject.read().m_Name,**trs(t)})
  if not t.m_Father.path_id:break
  t=t.m_Father.read()
 return rows[::-1]
textures={};materials={};objects=[];controller=None
for obj in env.objects:
 if obj.type.name=='MonoBehaviour':
  try:tree=obj.read_typetree()
  except:continue
  if '_RotateSpeed'in tree:controller={key:value for key,value in tree.items()if key.startswith('_')and key not in ['_Renderer','_OutlineRenderer','_Animation','_RootNode','_WebTextureHolder']}
 if obj.type.name!='Material':continue
 mat=obj.read();name=mat.m_Name
 if name not in ['FriendHeadIcon','FriendHeadOutline','FriendHeadShadow']:continue
 props=mat.m_SavedProperties;shadertree=mat.m_Shader.deref().read_typetree();shader=shadertree.get('m_ParsedForm',{}).get('m_Name')or shadertree.get('m_Name');texenvs={}
 for key,tenv in props.m_TexEnvs:
  texture=None
  if tenv.m_Texture.path_id:
   tex=tenv.m_Texture.read();dest=DEST/(tex.m_Name+'.png');source=ROOT/'client/SHIN/Assets/ResourcesAssets/Texture/BlockSet8x8/HeadIcon'/(tex.m_Name+'.png')
   if source.is_file():shutil.copyfile(source,dest)
   else:tex.image.save(dest)
   texture={'url':dest.relative_to(OUT).as_posix(),'name':tex.m_Name,'width':tex.m_Width,'height':tex.m_Height,'source':source.relative_to(ROOT).as_posix()if source.is_file()else 'original bundle Texture2D'};textures[tex.m_Name]=texture
  texenvs[key]={'texture':texture,'scale':{'x':tenv.m_Scale.x,'y':tenv.m_Scale.y},'offset':{'x':tenv.m_Offset.x,'y':tenv.m_Offset.y}}
 shaderfiles=[]
 for path in (ROOT/'client/SHIN/Assets/ResourcesAssets/Shader').rglob('*.shader'):
  if 'Shader "'+shader+'"'in path.read_text(encoding='utf-8-sig',errors='replace'):shaderfiles.append(path.relative_to(ROOT).as_posix())
 materials[name]={'name':name,'shader':shader,'shaderSources':shaderfiles,'customRenderQueue':mat.m_CustomRenderQueue,'floats':{k:float(v)for k,v in props.m_Floats},'colors':{k:{axis:float(getattr(v,axis))for axis in 'rgba'}for k,v in props.m_Colors},'textureEnvs':texenvs}
for obj in env.objects:
 if obj.type.name!='GameObject':continue
 go=obj.read();comps={c.component.type.name:c.component.read()for c in go.m_Component}
 if 'MeshRenderer'not in comps:continue
 tr=comps['Transform'];pointer=comps['MeshFilter'].m_Mesh
 objects.append({'name':go.m_Name,'mesh':'Cylinder','originalMeshRef':{'fileID':pointer.path_id,'externalFileId':pointer.file_id},'transformChain':chain(tr),'materials':[p.read().m_Name for p in comps['MeshRenderer'].m_Materials],'active':bool(go.m_IsActive)})
for i in [0,3,4,6]:
 stem=f'img_avater_player_{i:02}';source=ROOT/'client/SHIN/Assets/ResourcesAssets/Texture/BlockSet8x8/HeadIcon'/(stem+'.png');dest=DEST/(stem+'.png');shutil.copyfile(source,dest)
 with Image.open(dest)as im:w,h=im.size
 textures[stem]={'name':stem,'url':dest.relative_to(OUT).as_posix(),'width':w,'height':h,'source':source.relative_to(ROOT).as_posix()}
source=ROOT/'client/SHIN/Assets/ResourcesAssets/Prefabs/Model/City/FriendHeadIcon.prefab';shutil.copyfile(source,DEST/source.name);shutil.copyfile(ANIMS/'ani_FriendHeadIcon.anim',DEST/'ani_FriendHeadIcon.anim')
hooks=json.loads((SCENE/'grid-hooks.json').read_text(encoding='utf8'));slots={sid:{'center':slot['center'],'propRoot':slot.get('propRoot')}for sid,slot in hooks['slots'].items()}
result={'localOpponentTextures':[{'name':'风间','url':'assets/scene/avatar-3.png'},{'name':'阿呆','url':'assets/scene/avatar-4.png'},{'name':'正男','url':'assets/scene/avatar-6.png'}],'kind':'originalRotatingAvatarToken','source':asset['AssetPath'],'sourceBundle':bundle['FileHash']+'.bundle','matrixLayout':'column-major','meshes':{'Cylinder':mesh},'objects':objects,'materials':materials,'textures':textures,'controller':controller,'rentAnimation':clip('ani_FriendHeadIcon'),'slots':slots,'placement':{'parent':'square.PropRoot','worldPosition':'square.Center.position','worldRotation':{'x':0,'y':0,'z':0,'w':1},'worldScaleAtFirstSpawn':{'x':1,'y':1,'z':1},'rootNodeResetLocalPosition':{'x':0,'y':0,'z':0},'prefabRootPositionOverridden':True,'note':'Transform.SetParent(parent) uses worldPositionStays=true, then SetPositionAndRotation(world center, identity). Do not inherit board Root R45 in world rotation and do not apply root scale.9 again to token scale.'},'eventTimeline':{'source':'SquareBase.cs FRIEND_EVENT','steps':[{'time':0,'action':'moveFriend','direction':'-center.right','distance':0.3,'duration':0.1},{'time':1.6,'action':'movePiece','direction':'+center.right','distance':0.23,'duration':0.3},{'time':2.0,'action':'playFriendRentBoardAnimation'},{'time':2.1,'action':'playAniFriendHeadIcon'},{'time':2.25,'action':'movePieceToCenter','duration':0.25}]},'runtime':{'imageSelection':'decoration.socialIcon when nonempty, otherwise decoration.icon; ResUtils.SetHeadIconRenderer loads _MainTex','idleRotation':{'axis':'Y','degreesPerSecond':20,'node':'Root'},'goThrough':'PlayGoThroughAnimation sets countdown to _GoThroughDuration; speed scale evaluates _GoThroughCurve at 1-countdown/duration','rent':'Chessboard.PlayChessboardFriendRentAnimation starts corresponding FriendRent_line board animation, then waits0.1s and plays ani_FriendHeadIcon'},'evidence':['client/SHIN/Assets/Script/Game/moduls/Chessboard/Square/Chessboard.cs:1439-1487','client/SHIN/Assets/Script/Game/moduls/Chessboard/Prop/FriendHeadIcon.cs:56-101'],'notes':['Original rent display is not a Spine character. Icon and Outline are real thick builtin cylinder meshes, rotated90deg aroundX.','Slot matrices are relative to NormalChessboard_01 and include Root45deg but exclude outer root scale.9, matching grid-hooks. At runtime use board center world position and identity token rotation.','Outline renderer has two material passes; second FriendHeadShadow is a projected shadow, not a second white body.','Do not add prefab root y.26: original runtime explicitly overwrites root world position with Center. Child Icon/Outline retain y.3.']}
materials['FriendHeadIcon']['states']={'zTest':'LEqual','zWrite':True,'blend':'Off','cull':'Back','nullMainTexDefault':'white','nullMaskTexDefault':'black','nullCubeDefault':'native shader empty cubemap default; no resource supplied'}
materials['FriendHeadOutline']['states']=dict(materials['FriendHeadIcon']['states'])
materials['FriendHeadShadow']['states']={'zTest':'Less','zWrite':False,'blend':['One','OneMinusSrcAlpha'],'stencil':{'ref':2,'comp':'NotEqual','pass':'Replace'}}
assert len(mesh['positions'])==mesh['vertexCount']*3 and len(mesh['uv'])==mesh['vertexCount']*2 and max(mesh['indices'])<mesh['vertexCount']
assert len(slots)==40 and result['rentAnimation']['tracks']['Root']['position']['keys']
(SCENE/'board-characters.json').write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf8')
print(json.dumps({'objects':objects,'materials':{k:{kk:v[kk]for kk in ['shader','shaderSources','customRenderQueue','colors','floats']}for k,v in materials.items()},'controller':controller,'meshVertices':mesh['vertexCount'],'animation':result['rentAnimation'],'textures':list(textures)},ensure_ascii=False))