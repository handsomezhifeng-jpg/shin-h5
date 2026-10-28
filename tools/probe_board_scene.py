from pathlib import Path
import sys,json
sys.path.insert(0,'F:/superstar/shin-h5/tools/unity-libs');import UnityPy
ROOT=Path('F:/superstar');base=ROOT/'client/SHIN/Bundles/WebGL/DP/29877775';m=json.loads((base/'PackageManifest_DP_29877775.json').read_text(encoding='utf-8'));a=next(a for a in m['AssetList'] if a['Address']=='NormalChessboard_01');primary=m['BundleList'][a['BundleID']];bundles=[primary]+[m['BundleList'][i] for i in primary['DependIDs']];env=UnityPy.load(*[str(base/(b['FileHash']+'.bundle')) for b in bundles])
print('Mono sample',flush=True)
for obj in env.objects:
 if obj.type.name=='MonoBehaviour':
  try:
   tree=obj.read_typetree()
   if '_Center' in tree:
    print(obj.path_id,list(tree),flush=True);print(str(tree)[:3500],flush=True);break
  except:pass
print('Id11 nodes',flush=True)
for obj in env.objects:
 if obj.type.name!='GameObject':continue
 go=obj.read();trans=next((c.component.read() for c in go.m_Component if c.component.type.name=='Transform'),None)
 if not trans:continue
 path=[go.m_Name];cur=trans;active=bool(go.m_IsActive)
 while cur.m_Father.path_id:
  cur=cur.m_Father.read();g=cur.m_GameObject.read();path.append(g.m_Name);active=active and bool(g.m_IsActive)
 path.reverse()
 if len(path)>2 and path[0]=='NormalChessboard_01' and path[2]=='11':
  meshes=[]
  for c in go.m_Component:
   if c.component.type.name=='MeshFilter':
    meshes.append(c.component.read().m_Mesh.read().m_Name)
  if meshes or go.m_Name in ['center','prop_root','luckyCoin','Root_model']:
   print(path,'active',active,'mesh',meshes,'pos',trans.m_LocalPosition,'rot',trans.m_LocalRotation,'scale',trans.m_LocalScale,flush=True)