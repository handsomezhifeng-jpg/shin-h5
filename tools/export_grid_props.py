"""Export omitted original special-square renderers without changing existing board manifests."""
from pathlib import Path
import ast,hashlib,json,re,struct,math
helper=Path(__file__).with_name('inspect_board_scene.py').read_text(encoding='utf8').split('slots={};issues=[];font_names=set()')[0];exec(compile(helper,'board helpers','exec'))
for filename,names in [('export_fund_prop.py',{'mesh_data'}),('export_dice_prop.py',{'vertex_colors'})]:
 mod=ast.parse(Path(__file__).with_name(filename).read_text(encoding='utf8'));exec(compile(ast.Module(body=[n for n in mod.body if isinstance(n,ast.FunctionDef)and n.name in names],type_ignores=[]),filename,'exec'))
DEST=SCENE/'grid-props';DEST.mkdir(exist_ok=True);meshes={};materials={};textures={};slots={str(i):{'props':[],'rendererInventory':[]}for i in range(1,41)};issues=[]
shader_paths=list((ROOT/'client/SHIN/Assets/ResourcesAssets/Shader').rglob('*.shader'));shader_index={}
for p in shader_paths:
 text=p.read_text(encoding='utf-8-sig',errors='replace');found=re.search(r'\bShader\s+"([^"]+)"',text)
 if found:shader_index[found.group(1)]=p.relative_to(ROOT).as_posix()

def key(name,data):return name+'_'+hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()[:12]
def texture(tex):
 name=tex.m_Name
 if name in textures:return name
 source=None
 for directory in ['client/SHIN/Assets/Art/City/Chessboard/Grid/Textures','client/SHIN/Assets/Art/City/Chessboard/GoldCoin/Textures','client/SHIN/Assets/Art/City/Chessboard/cylinder/Textures']:
  for ext in ['.png','.tga']:
   path=ROOT/directory/(name+ext)
   if path.is_file():source=path;break
  if source:break
 dest=DEST/(name+'.png')
 if source:
  with Image.open(source)as im:im.convert('RGBA').save(dest)
 else:tex.image.save(dest)
 with Image.open(dest)as im:w,h=im.size
 textures[name]={'name':name,'url':dest.relative_to(OUT).as_posix(),'width':w,'height':h,'source':source.relative_to(ROOT).as_posix()if source else 'Original bundle Texture2D','bundleSize':[tex.m_Width,tex.m_Height]};return name

def material(mat):
 saved=mat.m_SavedProperties;sh=mat.m_Shader.deref().read_typetree();shader=sh.get('m_ParsedForm',{}).get('m_Name')or sh.get('m_Name');texs={}
 for prop,envtex in saved.m_TexEnvs:
  texs[prop]={'texture':texture(envtex.m_Texture.read())if envtex.m_Texture.path_id else None,'scale':{'x':envtex.m_Scale.x,'y':envtex.m_Scale.y},'offset':{'x':envtex.m_Offset.x,'y':envtex.m_Offset.y}}
 data={'name':mat.m_Name,'shader':shader,'shaderSource':shader_index.get(shader),'textures':texs,'colors':{n:{k:float(getattr(v,k))for k in 'rgba'}for n,v in saved.m_Colors},'floats':{n:float(v)for n,v in saved.m_Floats},'renderQueue':mat.m_CustomRenderQueue};ident=key(mat.m_Name,data);materials[ident]=data;return ident
for obj in env.objects:
 if obj.type.name not in ['MeshRenderer','SpriteRenderer','SkinnedMeshRenderer']:continue
 try:chain=chain_of(obj)
 except:continue
 if chain[0]['name']!='NormalChessboard_01':continue
 indexes=[(i,r)for i,r in enumerate(chain)if r['name'].isdigit()and 1<=int(r['name'])<=40]
 if not indexes:continue
 ii,instance=indexes[0];sid=instance['name'];path='/'.join(r['name']for r in chain[ii+1:]);renderer=obj.read();go=renderer.m_GameObject.read();comps={c.component.type.name:c.component.read()for c in go.m_Component};mf=comps.get('MeshFilter');mesh=mf.m_Mesh.read()if mf else None
 inventory={'path':path,'type':obj.type.name,'activeSelf':bool(go.m_IsActive),'activeInHierarchy':all(r['active']for r in chain),'rendererEnabled':bool(renderer.m_Enabled),'meshName':mesh.m_Name if mesh else None,'materialNames':[p.read().m_Name if p.path_id else None for p in renderer.m_Materials]};slots[sid]['rendererInventory'].append(inventory)
 # Existing bases, TMP, overlays and transient particle subtrees are already exported separately.
 relevant=('/model_01_ef/'in'/'+path or '/luckyCoin/'in'/'+path)
 if not relevant:continue
 if mesh is None:issues.append({'id':sid,'path':path,'reason':'Relevant renderer lacks readable MeshFilter mesh'});continue
 data=mesh_data(mesh);data['colors']=vertex_colors(mesh);mkey=key(mesh.m_Name,data);meshes[mkey]=data;tr=comps['Transform'];mids=[material(p.read())if p.path_id else None for p in renderer.m_Materials];instance_matrix=combined(chain[ii+1:]);normal_matrix=combined(chain[1:]);root_model_index=next((i for i in range(ii+1,len(chain))if chain[i]['name']=='Root_model'),None)
 row={**inventory,'mesh':mkey,'materials':mids,'local':trs(tr),'transformChain':chain,'parentChain':chain[ii+1:-1],'matrixInInstance':instance_matrix,'matrixInNormalPrefab':normal_matrix,'matrixRelativeToRootModel':combined(chain[root_model_index+1:])if root_model_index is not None else None,'positionInNormalPrefab':dict(zip('xyz',normal_matrix[12:15])),'isShadow':any(name and'Shadow'in name for name in inventory['materialNames']),'runtimeCondition':'LuckyCoin feature visibility controlled by SquareLuckyCoin'if '/luckyCoin/'in'/'+path else 'Default active prefab subtree; no generic _ModelObjects runtime switch.'};slots[sid]['props'].append(row)
for sid,slot in slots.items():slot['props'].sort(key=lambda p:p['path']);slot['rendererInventory'].sort(key=lambda p:p['path'])
evidence=[{'source':'client/SHIN/Assets/Script/Game/moduls/Chessboard/Square/SquareBase.cs:418-434','finding':'_ModelObjects runtime traversal is only commented-out friend highlight; it does not toggle corner building visibility.'},{'source':'client/SHIN/Assets/Script/Game/moduls/Chessboard/Square/Chessboard.cs:437','finding':'Gacha initialization searches Root/Root_model/model_01_ef on square11; current bundle square11 has no such subtree.'},{'source':'client/SHIN/Assets/Script/Game/moduls/Chessboard/Square/Chessboard.cs:1403-1427','finding':'Legacy GachaIsShow/SetGachaActive uses different Root/model_01_ef path; do not use this as evidence to hide active 1/21/31 building subtrees.'}]
result={'source':a['AssetPath'],'sourceBundle':primary['FileHash']+'.bundle','matrixLayout':'column-major','slots':slots,'meshes':meshes,'materials':materials,'textures':textures,'runtimeEvidence':evidence,'notes':['All MeshRenderer/SpriteRenderer/SkinnedMeshRenderer descendants of original40 slots are inventoried, not just first mesh. props exports the static special-square model_01_ef children and LuckyCoin subtree only.','matrixInNormalPrefab includes NormalChessboard_01/Root Y45 and numeric instance but excludes NormalChessboard_01 root scale.9, matching existing grid-hooks. Do not duplicate these transforms.','matrixRelativeToRootModel excludes animated Root/Root_model ancestors; multiply with current animated Root_model matrix to follow original board-motion.','Renderer material list matches Unity slots, including shadow passes; projected shadow is not another textured body.','1/21/31 model_01_ef/model_01 default active=true, no runtime assembly needed. Square21 omitted building is checkerboard_17_1.','Square11 LuckyCoin default source active=true may be disabled by runtime feature state. Keep its explicit condition separate from default corner building props.'],'issues':issues}

def finalize(result):
 for sid,slot in result['slots'].items():
  slot['conditionalProps']=[p for p in slot['props']if '/luckyCoin/'in'/'+p['path']]
  slot['props']=[p for p in slot['props']if '/luckyCoin/'not in'/'+p['path']]
  for row in slot['conditionalProps']:row['runtimeCondition']='BlankSquare.RefreshLuckyCoinShow: map>=UNLOCK_LUCKY_COIN_MAP, AlbumInfo non-null, lucky_coin config exists for current AlbumSeason. During CurrentSequence, preserve current visibility.'
 for data in result['materials'].values():
  if data['name']=='GridBuildShadow':data['renderState']={'blendSrc':'ONE','blendDst':'ONE_MINUS_SRC_ALPHA','depthTest':'LESS','depthWrite':False,'cull':'BACK','stencil':{'ref':2,'comp':'NOT_EQUAL','pass':'REPLACE'},'evidence':data['shaderSource']}
  data['shaderStateSourceLines']=[]
  if data.get('shaderSource'):
   text=(ROOT/data['shaderSource']).read_text(encoding='utf-8-sig',errors='replace')
   data['shaderStateSourceLines']=[line.strip()for line in text.splitlines()if re.match(r'^\s*(Blend|ZWrite|ZTest|Cull|Stencil|Ref|Comp|Pass|Tags)\b',line)and not line.lstrip().startswith('//')]
 for name,source in {'checkerboard_goldcoin_01_d':'client/SHIN/Assets/Art/City/Chessboard/LuckyCoin/Textures/checkerboard_goldcoin_01_d.tga','tex_MatCap_Gold':'client/SHIN/Assets/Art/City/Chessboard/Dice/Textures/tex_MatCap_Gold.jpg','img_com_Round':'client/SHIN/Assets/ResourcesAssets/Texture/Block8x8/MileStoneIcon/img_com_Round.png'}.items():
  if name not in result['textures']:continue
  row=result['textures'][name]
  with Image.open(ROOT/source)as im:
   original=im.convert('RGBA');original.save(OUT/row['url']);row['width'],row['height']=original.size;row['source']=source
 result['luckyCoinRuntime']={'source':'client/SHIN/Assets/Script/Game/moduls/Chessboard/Square/BlankSquare.cs:127-156','animationRoot':'Root/Root_model/luckyCoin','objectRoot':'Root/Root_model/luckyCoin/goldcoin_01','staticBaseMesh':'checkerboard_goldcoin_01','note':'luckyCoinAnim and luckyCoinObj reference the same conditional hierarchy, not separate static/activity coins. Only checkerboard_goldcoin_01 base is unconditionally present.'}
 result['notes']=[n for n in result['notes']if not n.startswith('Square11 LuckyCoin')]+['Square11 luckyCoin subtree is exported only in conditionalProps; never draw unconditionally from prefab active=true. Its static base checkerboard_goldcoin_01 remains in existing grid-prefabs.','Slot16 active checkerboard_04 node uses checkerboard_05 and is the existing exported base, not another omitted prop.']
 return result

finalize(result)
(SCENE/'grid-props.json').write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n',encoding='utf8')
assert len(slots)==40
for m in meshes.values():assert len(m['positions'])==m['vertexCount']*3 and max(m['indices'])<m['vertexCount']
print(json.dumps({'props':{sid:[{'path':p['path'],'mesh':p['mesh'],'active':p['activeInHierarchy']}for p in s['props']]for sid,s in slots.items()if s['props']},'meshes':[(k,v['vertexCount'])for k,v in meshes.items()],'materials':materials,'textures':textures,'rendererCount':sum(len(s['rendererInventory'])for s in slots.values()),'issues':issues},ensure_ascii=False))