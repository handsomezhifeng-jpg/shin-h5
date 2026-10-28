"""Restore the exact original slot-11 base mesh omitted by the source YAML exporter."""
from pathlib import Path
import ast,json,struct,math
helper=Path(__file__).with_name('inspect_board_scene.py').read_text(encoding='utf8').split('slots={};issues=[];font_names=set()')[0]
exec(compile(helper,'original board bundle helpers','exec'))
for filename,fnames in [('export_fund_prop.py',{'mesh_data'}),('export_dice_prop.py',{'vertex_colors'})]:
 module=ast.parse(Path(__file__).with_name(filename).read_text(encoding='utf8'))
 exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef)and n.name in fnames],type_ignores=[]),filename,'exec'))
name='checkerboard_goldcoin_01'
meshes=[obj.read()for obj in env.objects if obj.type.name=='Mesh'and obj.read().m_Name==name]
assert len(meshes)==1,f'Expected one exact original {name}, found {len(meshes)}'
mesh=meshes[0];data=mesh_data(mesh);data['colors']=vertex_colors(mesh);data['source']='YooAsset NormalChessboard_01 and declared dependency bundles / '+name;data['sourceBundle']=primary['FileHash']+'.bundle'
assert data['name']==name and data['vertexCount']==64
assert len(data['positions'])==64*3 and len(data['normals'])==64*3 and len(data['uv'])==64*2 and len(data['colors'])==64*4
assert min(data['indices'])>=0 and max(data['indices'])<64
assert all(math.isfinite(v)for field in ['positions','normals','uv','colors']for v in data[field])
path=SCENE/'grid-meshes.json';existing=json.loads(path.read_text(encoding='utf8'));before={k:v for k,v in existing.items()if k!=name};existing[name]=data;path.write_text(json.dumps(existing,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n',encoding='utf8')
after=json.loads(path.read_text(encoding='utf8'));assert before=={k:v for k,v in after.items()if k!=name},'Unrelated mesh changed'
print(json.dumps({'restoredMesh':name,'vertices':data['vertexCount'],'triangles':len(data['indices'])//3,'subMeshes':len(data['subMeshes']),'colorsRange':[min(data['colors']),max(data['colors'])],'totalMeshes':len(after),'unrelatedMeshes':'unchanged'},ensure_ascii=False))