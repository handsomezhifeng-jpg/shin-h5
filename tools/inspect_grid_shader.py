from pathlib import Path
import sys,json,struct
sys.path.insert(0,'F:/superstar/shin-h5/tools/unity-libs');import UnityPy
r=Path('F:/superstar');base=r/'client/SHIN/Bundles/WebGL/DP/29877775';m=json.loads((base/'PackageManifest_DP_29877775.json').read_text(encoding='utf-8'));asset=next(a for a in m['AssetList'] if a['Address']=='NormalChessboard_01');b=m['BundleList'][asset['BundleID']];bs=[b]+[m['BundleList'][i] for i in b['DependIDs']];env=UnityPy.load(*[str(base/(x['FileHash']+'.bundle')) for x in bs]);proof=[];color_export={}
for o in env.objects:
 if o.type.name=='Material':
  v=o.read()
  if v.m_Name in ['ChessboardSquare','ChessboardSquare_01']:
   shader=v.m_Shader.deref().read_typetree();parsed=shader.get('m_ParsedForm',{});print('SHADER',v.m_Name,shader.get('m_Name'),parsed.get('m_Name'));proof.append({'material':v.m_Name,'shader':parsed.get('m_Name') or shader.get('m_Name')})
 if o.type.name!='Mesh':continue
 mesh=o.read()
 if not mesh.m_Name.startswith('checkerboard'):continue
 vd=mesh.m_VertexData;cs=vd.m_Channels;c=cs[3]
 if not c.dimension:
  color_export[mesh.m_Name]=[1.0,1.0,1.0,1.0]*vd.m_VertexCount
  print(mesh.m_Name,'no color');continue
 sizes={0:4,1:2,2:1,3:1,4:2,5:2,6:1,7:1,8:2,9:2,10:4,11:4};stride=max(x.offset+sizes[x.format]*x.dimension for x in cs if x.dimension and x.stream==c.stream);raw=bytes(vd.m_DataSize)
 vals=[]
 for i in range(vd.m_VertexCount):
  if c.format==0:vals+=list(struct.unpack_from('<'+'f'*c.dimension,raw,i*stride+c.offset))
  elif c.format==2:vals+=[v/255 for v in struct.unpack_from('<'+'B'*c.dimension,raw,i*stride+c.offset)]
 color_export[mesh.m_Name]=[round(float(v),8) for v in vals]
 print(mesh.m_Name,'colorformat',c.format,'dim',c.dimension,'minmax',min(vals),max(vals),'unique',len(set(vals)))
mesh_path=r/'shin-h5/assets/scene/grid-meshes.json';meshes=json.loads(mesh_path.read_text(encoding='utf-8'))
written=0
for name,colors in color_export.items():
 if name in meshes:
  assert len(colors)==meshes[name]['vertexCount']*4,(name,len(colors),meshes[name]['vertexCount'])
  meshes[name]['colors']=colors;written+=1
temp=mesh_path.with_suffix('.tmp');temp.write_text(json.dumps(meshes,separators=(',',':'))+'\n',encoding='utf-8');temp.replace(mesh_path)
print('WROTE original RGBA vertex colors to',written,'meshes',flush=True)
# Resolve original pig shader from actual material, then locate current source.
pa=next(a for a in m['AssetList'] if a['Address']=='piggy_bank_damagedBase');pb=m['BundleList'][pa['BundleID']];pbs=[pb]+[m['BundleList'][i] for i in pb['DependIDs']];pe=UnityPy.load(*[str(base/(x['FileHash']+'.bundle')) for x in pbs]);pig_shader=None
for obj in pe.objects:
 if obj.type.name=='Material':
  mat=obj.read()
  if mat.m_Name=='mat_CarToonPig':
   st=mat.m_Shader.deref().read_typetree();pig_shader=st.get('m_ParsedForm',{}).get('m_Name') or st.get('m_Name');print('PIG_SHADER',pig_shader,flush=True)
if pig_shader:
 for path in (r/'client/SHIN/Assets/ResourcesAssets/Shader').rglob('*.shader'):
  if ('Shader "'+pig_shader+'"') in path.read_text(encoding='utf-8-sig',errors='replace')[:2500]:print('PIG_SHADER_SOURCE',str(path),flush=True)
