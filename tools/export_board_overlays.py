from pathlib import Path
import ast,hashlib,json,struct,math
helper=Path(__file__).with_name('inspect_board_scene.py').read_text(encoding='utf8').split('slots={};issues=[];font_names=set()')[0]
exec(compile(helper,'board helpers','exec'))
for filename,fnames in [('export_fund_prop.py',{'mesh_data'}),('export_dice_prop.py',{'vertex_colors'})]:
 module=ast.parse(Path(__file__).with_name(filename).read_text(encoding='utf8'))
 exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef)and n.name in fnames],type_ignores=[]),filename,'exec'))
meshes={};materials={};textures={};slots={};issues=[]
def ident(data):return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()[:12]
def tex_data(tex):
 name=tex.m_Name
 if name in textures:return name
 dest=SCENE/'board-overlays'/(name+'.png');dest.parent.mkdir(parents=True,exist_ok=True)
 source=None
 for directory in ['client/SHIN/Assets/Art/City/Chessboard/Grid/Textures','client/SHIN/Assets/Art/UI_Effect/EF_TexRepeat']:
  for ext in ['.png','.tga']:
   candidate=ROOT/directory/(name+ext)
   if candidate.is_file():source=candidate;break
  if source:break
 if source:
  with Image.open(source)as im:
   original=im.convert('RGBA');existing=SCENE/(name+'.png')
   if existing.is_file():
    with Image.open(existing)as other:matches=other.convert('RGBA').tobytes()==original.tobytes()and other.size==original.size
    if matches:dest=existing
    else:original.save(dest)
   else:original.save(dest)
 else:tex.image.save(dest)
 textures[name]={'name':name,'url':str(dest.relative_to(OUT)).replace('\\','/'),'width':tex.m_Width,'height':tex.m_Height,'source':str(source.relative_to(ROOT)).replace('\\','/')if source else 'original bundle Texture2D'}
 return name

def material_data(mat):
 saved=mat.m_SavedProperties;shader_tree=mat.m_Shader.deref().read_typetree();shader=shader_tree.get('m_ParsedForm',{}).get('m_Name')or shader_tree.get('m_Name');texs={}
 for prop,texenv in saved.m_TexEnvs:
  if texenv.m_Texture.path_id:texs[prop]={'texture':tex_data(texenv.m_Texture.read()),'scale':{'x':texenv.m_Scale.x,'y':texenv.m_Scale.y},'offset':{'x':texenv.m_Offset.x,'y':texenv.m_Offset.y}}
 data={'name':mat.m_Name,'shader':shader,'shaderSource':'client/SHIN/Assets/ResourcesAssets/Shader/SFX/SFX_Mesh_Additive.shader','source':'client/SHIN/Assets/Art/City/Chessboard/Grid/Materials/mat_ChessboardSquare.mat','textures':texs,'colors':{name:{key:float(getattr(v,key))for key in 'rgba'}for name,v in saved.m_Colors},'floats':{name:float(v)for name,v in saved.m_Floats},'renderQueue':mat.m_CustomRenderQueue,'renderState':{'blendSrc':'SRC_ALPHA','blendDst':'ONE','cull':'OFF','depthTest':'LEQUAL','depthWrite':False,'stencil':{'ref':0,'comp':'ALWAYS','pass':'KEEP','readMask':255,'writeMask':255}}}
 key=mat.m_Name+'_'+ident(data);materials[key]=data;return key
for obj in env.objects:
 if obj.type.name!='GameObject':continue
 go=obj.read()
 if go.m_Name!='model (1)':continue
 chain=chain_of(obj)
 if chain[0]['name']!='NormalChessboard_01':continue
 instances=[(i,r)for i,r in enumerate(chain)if r['name'].isdigit()and 1<=int(r['name'])<=40]
 if not instances:continue
 ii,instance=instances[0];sid=instance['name'];relative='/'.join(r['name']for r in chain[ii+1:])
 if relative!='Root/Root_model/model (1)':continue
 comps={c.component.type.name:c.component.read()for c in go.m_Component};tr=comps['Transform'];mesh=comps['MeshFilter'].m_Mesh.read();data=mesh_data(mesh);data['colors']=vertex_colors(mesh);key=mesh.m_Name+'_'+ident(data);meshes[key]=data
 mids=[material_data(p.read())for p in comps['MeshRenderer'].m_Materials]
 slots[sid]={'path':relative,'active':bool(go.m_IsActive),'mesh':key,'materials':mids,'local':trs(tr),'parentChain':chain[ii+1:-1],'matrixInInstance':combined(chain[ii+1:]),'matrixInNormalPrefab':combined(chain[1:]),'positionInNormalPrefab':{axis:combined(chain[1:])[12+n]for n,axis in enumerate('xyz')}}
assert len(slots)==40
motion=json.loads((SCENE/'board-motion.json').read_text(encoding='utf8'))
attrs={name:[{'path':row['path'],'attribute':row.get('attribute'),'classID':row.get('classID')}for row in clip['floatCurves']]for name,clip in motion['clips'].items()if clip['floatCurves']}
result={'source':a['AssetPath'],'sourceBundle':primary['FileHash']+'.bundle','matrixLayout':'column-major','slots':dict(sorted(slots.items(),key=lambda kv:int(kv[0]))),'meshes':meshes,'materials':materials,'textures':textures,'clipFloatAttributes':attrs,'notes':['Original per-slot Root/Root_model/model (1) additive overlay; original meshes, UVs and colors are deduplicated by content.','Local transforms are exact, not forced to a common scale or rotation. Follow animated Root and Root_model ancestors from board-motion.json.','matrixInNormalPrefab includes Root Y45, excludes NormalChessboard_01 root scale0.9; same space as grid-hooks.json.','m_IsActive and material._Color.r/g/b/a are animated by the source clips. Use board-motion clips floatCurves for exact times.','Shader SFX/Mesh_Additive uses Blend SrcAlpha One, Cull Off, ZTest LEqual, ZWrite Off. Material serialized _ZWrite=1 is unused by this shader.','Shader vertex output color = vertexColor * _Color * 2. Fragment rgb = MainTex.rgb * color.rgb; alpha = MainTex.a * color.a * MaskTex.r * _FGUIAlpha. No model lighting.','Renderer material list is preserved exactly, including duplicates. Match submesh to material index; only repeat the last submesh if there are more materials than submeshes, as Unity does.'],'issues':issues}
dest=SCENE/'board-overlays.json';dest.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n',encoding='utf8')
print(json.dumps({'output':str(dest),'bytes':dest.stat().st_size,'slots':len(slots),'meshes':[(k,m['vertexCount'],len(m['subMeshes']))for k,m in meshes.items()],'materials':list(materials),'textures':textures,'localScales':list({json.dumps(s['local']['scale'],sort_keys=True)for s in slots.values()}),'initiallyActive':sum(s['active']for s in slots.values())},ensure_ascii=False))