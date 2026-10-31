"""Export only original prison cage prop and four original cage/tea-house clips."""
from pathlib import Path
import sys,json,ast,struct,math,re,hashlib
sys.path.insert(0,str(Path(__file__).parent/'unity-libs'))
import UnityPy
from PIL import Image
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'shin-h5';SCENE=OUT/'assets/scene';DEST=SCENE/'prison-prop';DEST.mkdir(exist_ok=True);BASE=ROOT/'client/SHIN/Bundles/WebGL/DP/29877775';ANIMS=ROOT/'client/SHIN/Assets/Art/UI_Effect/EF_Animations'
for filename,names in [('inspect_board_scene.py',{'vec','quat','trs','mat','mul','combined'}),('export_fund_prop.py',{'mesh_data'}),('export_dice_prop.py',{'vertex_colors'}),('export_board_motion.py',{'numeric','curve_list','clip'})]:
 module=ast.parse((OUT/'tools'/filename).read_text(encoding='utf8'));exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef)and n.name in names],type_ignores=[]),filename,'exec'))
manifest=json.loads((BASE/'PackageManifest_DP_29877775.json').read_text(encoding='utf8'));asset=next(a for a in manifest['AssetList']if a['Address']=='mesh_cage_01');bundle=manifest['BundleList'][asset['BundleID']];bundles=[bundle]+[manifest['BundleList'][i]for i in bundle['DependIDs']];env=UnityPy.load(*[str(BASE/(b['FileHash']+'.bundle'))for b in bundles])
meshes={};materials={};textures={};objects=[];nodes={};issues=[]
def chain(tr):
 rows=[]
 while True:
  go=tr.m_GameObject.read();rows.append({'name':go.m_Name,'active':bool(go.m_IsActive),**trs(tr)})
  if not tr.m_Father.path_id:break
  tr=tr.m_Father.read()
 return rows[::-1]
def meshkey(mesh):
 data=mesh_data(mesh);data['colors']=vertex_colors(mesh);key=mesh.m_Name+'_'+hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()[:10];meshes[key]=data;return key
shader_index={}
for p in (ROOT/'client/SHIN/Assets/ResourcesAssets/Shader').rglob('*.shader'):
 text=p.read_text(encoding='utf-8-sig',errors='replace');match=re.search(r'\bShader\s+"([^"]+)"',text)
 if match:shader_index[match.group(1)]=(p,text)
def texture(tex):
 name=tex.m_Name
 if name in textures:return name
 source=None
 for folder in ['client/SHIN/Assets/Art/City/Chessboard/Grid/Textures','client/SHIN/Assets/Art/UI_Effect/EF_TexRepeat','client/SHIN/Assets/Art/UI_Effect/EF_Texture']:
  for ext in ['.png','.tga','.jpg']:
   p=ROOT/folder/(name+ext)
   if p.is_file():source=p;break
  if source:break
 target=DEST/(name+'.png')
 if source:
  with Image.open(source)as im:im.convert('RGBA').save(target)
 else:tex.image.save(target)
 with Image.open(target)as im:w,h=im.size
 textures[name]={'name':name,'url':target.relative_to(OUT).as_posix(),'width':w,'height':h,'source':source.relative_to(ROOT).as_posix()if source else 'original bundle Texture2D'};return name

def material(data):
 name=data.m_Name
 if name in materials:return name
 saved=data.m_SavedProperties;tree=data.m_Shader.deref().read_typetree();shader=tree.get('m_ParsedForm',{}).get('m_Name')or tree.get('m_Name');props={}
 for prop,tenv in saved.m_TexEnvs:props[prop]={'texture':texture(tenv.m_Texture.read())if tenv.m_Texture.path_id else None,'scale':{'x':tenv.m_Scale.x,'y':tenv.m_Scale.y},'offset':{'x':tenv.m_Offset.x,'y':tenv.m_Offset.y}}
 path,text=shader_index.get(shader,(None,''));materials[name]={'name':name,'shader':shader,'shaderSource':path.relative_to(ROOT).as_posix()if path else None,'shaderStateSourceLines':[line.strip()for line in text.splitlines()if re.match(r'^\s*(Blend|ZWrite|ZTest|Cull|Stencil|Ref|Comp|Pass|Tags)\b',line)and not line.lstrip().startswith('//')],'textures':props,'colors':{k:{a:float(getattr(v,a))for a in 'rgba'}for k,v in saved.m_Colors},'floats':{k:float(v)for k,v in saved.m_Floats},'renderQueue':data.m_CustomRenderQueue,'keywords':getattr(data,'m_ShaderKeywords','')};return name
for obj in env.objects:
 if obj.type.name!='GameObject':continue
 go=obj.read();components={c.component.type.name:c.component.read()for c in go.m_Component};tr=components.get('Transform')
 if tr is None:continue
 rows=chain(tr)
 if rows[0]['name']!='mesh_cage_01':continue
 top=tr
 while top.m_Father.path_id:top=top.m_Father.read()
 if not any(c.component.type.name=='Animation'for c in top.m_GameObject.read().m_Component):continue
 path='/'.join(r['name']for r in rows[1:]);matrix=combined(rows);nodes[path]={'local':trs(tr),'chain':rows,'matrixInPrefab':matrix,'matrixRelativeToAnimationRoot':combined(rows[1:]),'active':all(r['active']for r in rows)}
 renderer=components.get('MeshRenderer');mf=components.get('MeshFilter')
 if renderer is None or mf is None:continue
 item={'path':path,'name':go.m_Name,'mesh':meshkey(mf.m_Mesh.read()),'materials':[material(p.read())if p.path_id else None for p in renderer.m_Materials],'local':trs(tr),'transformChain':rows,'matrixInPrefab':matrix,'matrixRelativeToAnimationRoot':combined(rows[1:]),'activeSelf':bool(go.m_IsActive),'activeInHierarchy':all(r['active']for r in rows),'rendererEnabled':bool(renderer.m_Enabled),'sortingOrder':renderer.m_SortingOrder};objects.append(item)
# Deduplicate repeated prefab dependencies by exact authored path/data, preserving front/back pieces.
objects=list({json.dumps(o,sort_keys=True):o for o in objects}.values());assert len(objects)==2
# Unity GetComponentsInChildren traverses the serialized child order, not bundle object order.
def hierarchy_order(tr,path=''):
 paths=[];go=tr.m_GameObject.read()
 if any(c.component.type.name=='MeshRenderer'for c in go.m_Component):paths.append(path)
 for pointer in tr.m_Children:
  child=pointer.read();name=child.m_GameObject.read().m_Name;paths.extend(hierarchy_order(child,path+'/'+name if path else name))
 return paths
renderer_order=hierarchy_order(top)
for obj in objects:
 index=renderer_order.index(obj['path']);obj['rendererHierarchyIndex']=index;obj['runtimeSortingOrderRelativeToPiece']=1 if index==0 else -1
objects.sort(key=lambda o:o['rendererHierarchyIndex'])
hooks=json.loads((SCENE/'grid-hooks.json').read_text(encoding='utf8'));slot=hooks['slots']['31'];normal_matrix=combined(slot['parentChain'][1:]+[slot['instance']]);world_matrix=combined(slot['parentChain']+[slot['instance']]);world_matrix[12]+=.06
boardmotion=json.loads((SCENE/'board-motion.json').read_text(encoding='utf8'));gridprops=json.loads((SCENE/'grid-props.json').read_text(encoding='utf8'));bindings=dict(boardmotion['slots']['31']['bindingNodes'])
for row in gridprops['slots']['31']['props']:bindings[row['path']]={'local':row['local'],'matrixInNormalPrefab':row['matrixInNormalPrefab'],'matrixInInstance':row['matrixInInstance'],'active':row['activeInHierarchy']}
clips={name:clip(name)for name in ['ani_mesh_cage_01_into','ani_mesh_cage_01_out','ani_caju_into','ani_caju_out']};building_refs={name:{'url':'assets/scene/board-motion.json','clip':name}for name in ['ani_caju_into','ani_caju_out']if name in boardmotion['clips']}
result={'source':asset['AssetPath'],'sourceBundle':bundle['FileHash']+'.bundle','matrixLayout':'column-major','objects':objects,'meshes':meshes,'materials':materials,'textures':textures,'bindingNodes':nodes,'clips':clips,'building':{'slotId':31,'animationRoot':'NormalChessboard_01/Root/31','animationPath':'Root/Root_model/model_01_ef','shadowPath':'Root/Root_model/model_01_ef/model_01_shadow','bindingNodes':bindings,'clipReferences':building_refs,'propsURL':'assets/scene/grid-props.json'},'placement':{'slotId':31,'runtimeAnchor':'PrisonSquare.transform (numeric slot31), not square.Center','parent':None,'slotParentChain':slot['parentChain'],'slotLocal':slot['instance'],'slotMatrixInNormalPrefab':normal_matrix,'runtimeWorldMatrix':world_matrix,'worldOffset':{'x':.06,'y':0,'z':0},'worldPosition':dict(zip('xyz',world_matrix[12:15])),'normalPrefabRootScaleIncludedInPositionOnly':True,'worldMatrixNote':'Runtime world position includes original NormalChessboard root scale.9; world rotation includes Root Y45. Cage is spawned unparented with rotation of square31; its own prefab scale1 remains1, so root .9 affects POSITION only, NOT cage geometry SCALE. Use runtimeTransform below.'},'runtimeEvidence':[{'source':'client/SHIN/Assets/Script/Game/moduls/Chessboard/Square/PrisonSquare.cs:105-127','action':'ShowEffectFromPool(transform.position,transform.rotation,mesh_cage_01); worldX+=.06; play ani_mesh_cage_01_into and square ani_caju_out; after1s show PrisonCageWindow.'},{'source':'client/SHIN/Assets/Script/Game/moduls/Chessboard/Square/PrisonSquare.cs:132-145','action':'OnHidePrisonCage plays ani_mesh_cage_01_out and square ani_caju_into; after.5s pool cage and release StaySquareAnimation lock.'},{'source':'client/SHIN/Assets/Script/Game/moduls/Chessboard/Square/PrisonSquare.cs:155-162','action':'Cage renderer0 sortingOrder=piece+1; renderer1 sortingOrder=piece-1, separating front/back around player.'}],'notes':['Cage clip paths are relative to prefab Animation component at mesh_cage_01 root; literal lower-case root is a child rotatedY180. Retain its base rotation.','Building/tea-house clips are relative to numeric slot31 Animation root. They are separate from cage root clips and must run simultaneously as specified.','Do not add Center.y=.26 to cage placement; anchor is square transform. Do not apply board R45 or scale.9 twice.','Material and source shader states are exported as authored, including texture transforms.','Animation curves retain native Hermite tangents and key times, including float material shadow-color tracks.'],'issues':issues}
# Runtime uses world position/rotation only. Remove inherited uniform board scaling from cage root basis.
runtime=list(world_matrix)
for col in range(3):
 length=math.sqrt(sum(runtime[col*4+r]**2 for r in range(3)))
 for r in range(3):runtime[col*4+r]/=length
result['placement']['runtimeTransform']={'position':result['placement']['worldPosition'],'rotation':slot['parentChain'][1]['rotation'],'scale':{'x':1,'y':1,'z':1},'matrix':runtime}
result['placement']['runtimeWorldMatrix']=runtime
for material in materials.values():material['renderState']={'blendSrc':'ONE','blendDst':'ZERO','depthWrite':bool(material['floats']['_ZWrite']),'depthTest':'LESS'if material['floats']['_ZTestMode']==2 else 'LEQUAL','cull':'BACK'}
for name,c in clips.items():
 valid=nodes if name.startswith('ani_mesh')else bindings;missing=[p for p in c['tracks']if p not in valid]
 if missing:issues.append({'clip':name,'missingTransformPaths':missing})
for mesh in meshes.values():assert len(mesh['positions'])==mesh['vertexCount']*3 and max(mesh['indices'])<mesh['vertexCount']
(SCENE/'prison-prop.json').write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n',encoding='utf8')
print(json.dumps({'objects':objects,'meshes':[(k,v['vertexCount'])for k,v in meshes.items()],'materials':materials,'textures':textures,'clips':{k:{'duration':c['duration'],'paths':list(c['tracks']),'floatPaths':list({r['path']for r in c['floatCurves']})}for k,c in clips.items()},'placement':result['placement'],'issues':issues},ensure_ascii=False))