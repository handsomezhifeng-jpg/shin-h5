from pathlib import Path
import sys,json,re,struct,math,shutil
sys.path.insert(0,'F:/superstar/shin-h5/tools/unity-libs')
import UnityPy
from UnityPy.classes.PPtr import PPtr
from PIL import Image
ROOT=Path('F:/superstar');OUT=ROOT/'shin-h5';SCENE=OUT/'assets/scene';BASE=ROOT/'client/SHIN/Bundles/WebGL/DP/29877775'
manifest=json.loads((BASE/'PackageManifest_DP_29877775.json').read_text(encoding='utf-8'))
a=next(a for a in manifest['AssetList'] if a['Address']=='NormalChessboard_01');primary=manifest['BundleList'][a['BundleID']];bundle_rows=[primary]+[manifest['BundleList'][i] for i in primary['DependIDs']]
env=UnityPy.load(*[str(BASE/(b['FileHash']+'.bundle')) for b in bundle_rows])

def vec(v):return {k:round(float(getattr(v,k)),9) for k in ['x','y','z']}
def quat(q):return {k:round(float(getattr(q,k)),9) for k in ['x','y','z','w']}
def trs(tr):return {'position':vec(tr.m_LocalPosition),'rotation':quat(tr.m_LocalRotation),'scale':vec(tr.m_LocalScale)}
def mat(t):
 p=t['position'];q=t['rotation'];s=t['scale'];x,y,z,w=[q[k] for k in ['x','y','z','w']];sx,sy,sz=[s[k] for k in ['x','y','z']]
 return [[(1-2*y*y-2*z*z)*sx,(2*x*y-2*z*w)*sy,(2*x*z+2*y*w)*sz,p['x']],[(2*x*y+2*z*w)*sx,(1-2*x*x-2*z*z)*sy,(2*y*z-2*x*w)*sz,p['y']],[(2*x*z-2*y*w)*sx,(2*y*z+2*x*w)*sy,(1-2*x*x-2*y*y)*sz,p['z']],[0,0,0,1]]
def mul(a,b):return [[sum(a[i][k]*b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]
def combined(rows):
 value=[[int(i==j) for j in range(4)] for i in range(4)]
 for row in rows:value=mul(value,mat(row))
 return [round(value[row][col],9) for col in range(4) for row in range(4)]
def raw_pointer(owner,ref):
 if not ref or not ref.get('m_PathID'):return None
 return PPtr(m_FileID=ref['m_FileID'],m_PathID=ref['m_PathID'],assetsfile=owner.assets_file).deref()
def transform_of(obj):
 data=obj.read()
 if obj.type.name in ['Transform','RectTransform']:return data
 go=data if obj.type.name=='GameObject' else data.m_GameObject.read()
 return next(c.component.read() for c in go.m_Component if c.component.type.name in ['Transform','RectTransform'])
def chain_of(obj):
 tr=transform_of(obj);go=tr.m_GameObject.read();rows=[{'name':go.m_Name,'active':bool(go.m_IsActive),**trs(tr)}]
 while tr.m_Father.path_id:
  tr=tr.m_Father.read();go=tr.m_GameObject.read();rows.append({'name':go.m_Name,'active':bool(go.m_IsActive),**trs(tr)})
 return list(reversed(rows))
def hook(owner,ref,instance_index):
 obj=raw_pointer(owner,ref)
 if not obj:return None
 chain=chain_of(obj);local=chain[-1]
 matrix=combined(chain[instance_index+1:]);normal=combined(chain[1:])
 result={'name':local['name'],'path':[r['name'] for r in chain],'local':{k:local[k] for k in ['position','rotation','scale']},'matrixInInstance':matrix,'matrixInNormalPrefab':normal,'positionInInstance':{'x':matrix[12],'y':matrix[13],'z':matrix[14]},'positionInNormalPrefab':{'x':normal[12],'y':normal[13],'z':normal[14]}}
 tr=transform_of(obj)
 if hasattr(tr,'m_SizeDelta'):result['rect']={'sizeDelta':{'x':tr.m_SizeDelta.x,'y':tr.m_SizeDelta.y},'pivot':{'x':tr.m_Pivot.x,'y':tr.m_Pivot.y}}
 return result

slots={};issues=[];font_names=set()
for obj in env.objects:
 if obj.type.name!='MonoBehaviour':continue
 try:tree=obj.read_typetree()
 except:continue
 if '_Center' not in tree:continue
 go=raw_pointer(obj,tree['m_GameObject'])
 chain=chain_of(go)
 if chain[0]['name']!='NormalChessboard_01':continue
 instances=[(i,row) for i,row in enumerate(chain) if row['name'].isdigit() and 1<=int(row['name'])<=40]
 if not instances:continue
 ii,instance=instances[0];sid=instance['name']
 row={'id':int(sid),'instance':{k:instance[k] for k in ['position','rotation','scale']},'parentChain':chain[:ii], 'center':hook(obj,tree.get('_Center'),ii),'propRoot':hook(obj,tree.get('_PropRoot'),ii),'text':hook(obj,tree.get('_TextMeshPro'),ii),'modelObjects':[],'dicePositions':[hook(obj,ref,ii) for ref in tree.get('_DicePositionList',[]) if ref.get('m_PathID')]}
 for ref in tree.get('_ModelObjects',[]):
  item=hook(obj,ref,ii)
  if item:row['modelObjects'].append(item)
 if row['text']:
  textobj=raw_pointer(obj,tree['_TextMeshPro']);text=textobj.read_typetree()
  keys=['m_text','m_fontSize','m_fontSizeBase','m_fontWeight','m_fontStyle','m_fontColor','m_fontColor32','m_HorizontalAlignment','m_VerticalAlignment','m_textAlignment','m_enableAutoSizing','m_fontSizeMin','m_fontSizeMax','m_isOrthographic','m_isRightToLeft','m_characterSpacing','m_lineSpacing','m_paragraphSpacing']
  row['text']['settings']={k:text[k] for k in keys if k in text}
  font=raw_pointer(textobj,text.get('m_fontAsset'))
  if font:
   ft=font.read_typetree();row['text']['fontName']=ft.get('m_Name');font_names.add(ft.get('m_Name'))
  material=raw_pointer(textobj,text.get('m_sharedMaterial'))
  if material:
   mt=material.read_typetree();saved=mt.get('m_SavedProperties',{});row['text']['material']={'name':mt.get('m_Name'),'colors':saved.get('m_Colors'),'floats':saved.get('m_Floats')}
 for field in ['luckyCoinAnim','luckyCoinObj']:
  if tree.get(field):row[field]=hook(obj,tree[field],ii)
 slots[sid]=row
assert set(slots)==set(map(str,range(1,41))),f'Incomplete hooks: {len(slots)}'
slots={key:slots[key] for key in sorted(slots,key=int)}
font_source=ROOT/'client/SHIN/Assets/Art/Font/NotoSansSCBold_num.ttf'
if font_source.is_file():shutil.copy2(font_source,SCENE/'NotoSansSCBold_num.ttf')
hooks={'source':a['AssetPath'],'sourceBundle':primary['FileHash']+'.bundle','matrixLayout':'column-major','notes':['matrixInInstance includes all nested transforms after numeric slot root; matrixInNormalPrefab includes NormalChessboard_01/Root but excludes prefab root itself.','MainCityRoot/Chessboard parent scale0.9 is not included in these matrices.','dicePositions is the original _DicePositionList in serialized order; each uses the same matrix/position space as center, including Root Y45 but excluding parent scale0.9.','LuckyCoin on/off toggles the luckyCoinAnim subtree, not the separate base model.'],'fonts':sorted(font_names),'fontURL':'assets/scene/NotoSansSCBold_num.ttf','slots':slots}
(SCENE/'grid-hooks.json').write_text(json.dumps(hooks,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

# Parse the CURRENT source prefab, which may be newer than the saved bundle.
def inline_numbers(value):return {k:float(v) for k,v in re.findall(r'(\w+):\s*([-+\d.eE]+)',value)}
def source_objects(path):
 text=path.read_text(encoding='utf-8-sig');parts=re.split(r'^--- !u!(\d+) &(-?\d+).*\n',text,flags=re.M);records={}
 for i in range(1,len(parts),3):
  typ=int(parts[i]);ident=int(parts[i+1]);body=parts[i+2];record={'type':typ,'raw':body}
  if typ==1:
   record['name']=re.search(r'^  m_Name: ?(.*)$',body,re.M).group(1);record['active']=bool(int(re.search(r'^  m_IsActive: (\d+)',body,re.M).group(1)))
  elif typ in [4,224]:
   record['go']=int(re.search(r'm_GameObject: \{fileID: (-?\d+)',body).group(1));record['parent']=int(re.search(r'm_Father: \{fileID: (-?\d+)',body).group(1))
   for prop,field in [('position','m_LocalPosition'),('rotation','m_LocalRotation'),('scale','m_LocalScale')]:record[prop]=inline_numbers(re.search(field+r': (\{[^}]+\})',body).group(1))
  elif typ==33:
   record['go']=int(re.search(r'm_GameObject: \{fileID: (-?\d+)',body).group(1));record['meshGuid']=re.search(r'm_Mesh: \{[^}]*guid: ([0-9a-f]+)',body).group(1)
  records[ident]=record
 return records
source_path=ROOT/'client/SHIN/Assets/ResourcesAssets/Prefabs/Scene/City/MainCityRoot.prefab';records=source_objects(source_path);transforms={record['go']:record for record in records.values() if record['type'] in [4,224]}
def source_chain(tr):
 chain=[]
 while True:
  chain.append({'name':records[tr['go']]['name'],**{k:tr[k] for k in ['position','rotation','scale']}})
  if not tr['parent']:break
  tr=records[tr['parent']]
 return list(reversed(chain))
selected=['MainCityRoot','Background','BG_SubMesh','BackgroundFront','BG_F_SubMesh','Chessboard','Fund']
nodes={}
for goid,go in records.items():
 if go['type']!=1 or go.get('name') not in selected:continue
 tr=transforms[goid];chain=source_chain(tr);row={'name':go['name'],'active':go['active'],'local':{k:tr[k] for k in ['position','rotation','scale']},'chain':chain,'matrixInMainCityRoot':combined(chain[1:])}
 filt=next((record for record in records.values() if record['type']==33 and record['go']==goid),None)
 if filt:row['meshGuid']=filt['meshGuid']
 nodes[go['name']]=row

# Current source 4-submesh planar mesh: preserve each material/texture slot.
mesh_path=ROOT/'client/SHIN/Assets/Art/City/Chessboard/Grid/Models/CityBgSubMesh.asset';text=mesh_path.read_text(encoding='utf-8-sig')
raw=bytes.fromhex(re.search(r'_typeless[Dd]ata:\s*([0-9a-fA-F]+)',text).group(1));count=int(re.search(r'm_VertexCount: (\d+)',text).group(1))
channel_text=text.split('    m_Channels:',1)[1].split('    m_DataSize:',1)[0];channels=[tuple(map(int,m)) for m in re.findall(r'- stream: (\d+)\s+offset: (\d+)\s+format: (\d+)\s+dimension: (\d+)',channel_text)]
formats={0:(4,'f'),1:(2,'e'),2:(1,'B'),3:(1,'b'),4:(2,'H'),5:(2,'h'),6:(1,'B'),7:(1,'b'),8:(2,'H'),9:(2,'h'),10:(4,'I'),11:(4,'i')};stride=max(off+formats[fmt][0]*dim for stream,off,fmt,dim in channels if dim)
def read_channel(channel):
 stream,off,fmt,dim=channel;return [round(float(v),9) for i in range(count) for v in struct.unpack_from('<'+formats[fmt][1]*dim,raw,i*stride+off)]
indexraw=bytes.fromhex(re.search(r'^  m_IndexBuffer: ([0-9a-fA-F]+)',text,re.M).group(1));indices=list(struct.unpack('<'+'H'*(len(indexraw)//2),indexraw))
sub=text.split('  m_SubMeshes:',1)[1].split('  m_Shapes:',1)[0];submeshes=[]
for i,match in enumerate(re.finditer(r'firstByte: (\d+)\s+indexCount: (\d+)\s+topology: (\d+)\s+baseVertex: (\d+)',sub)):
 first,n,topology,basev=map(int,match.groups());submeshes.append({'materialSlot':i,'texturePart':i+1,'firstByte':first,'indexCount':n,'topology':topology,'baseVertex':basev,'indices':indices[first//2:first//2+n]})
mesh={'name':'CityBgSubMesh','positions':read_channel(channels[0]),'uv':read_channel(channels[4]),'indices':indices,'subMeshes':submeshes,'vertexCount':count,'source':str(mesh_path.relative_to(ROOT)).replace('\\','/')}
(SCENE/'city-background-mesh.json').write_text(json.dumps(mesh,separators=(',',':'))+'\n',encoding='utf-8')
textures={};missing=[]
for mapid in [1,2,41]:
 textures[str(mapid)]={'background':[],'foreground':[]}
 for layer,folder,pattern in [('background','CityBg',f'bg_main_{mapid}_{{part}}.png'),('foreground','CityBgFront',f'bg_main_{mapid}_f_{{part}}.png')]:
  for part in range(1,5):
   source=ROOT/'client/SHIN/Assets/ResourcesAssets/TextureRule'/folder/pattern.format(part=part)
   address=source.stem
   declared=next((item for item in manifest['AssetList'] if item['Address']==address),None)
   if declared:source=ROOT/'client/SHIN'/declared['AssetPath']
   if source.is_file():
    dest=SCENE/source.name;shutil.copy2(source,dest)
    with Image.open(source) as im:entry={'part':part,'url':'assets/scene/'+dest.name,'width':im.width,'height':im.height,'mode':im.mode,'source':str(source.relative_to(ROOT)).replace('\\','/')}
    textures[str(mapid)][layer].append(entry)
   else:missing.append(str(source.relative_to(ROOT)).replace('\\','/'))
variants=[]
for item in manifest['AssetList']:
 if item['Address'] in ['bg_main_1_1','bg_main_1_f_1','bg_main_41_1','bg_main_41_f_1'] or 'Grid/Textures/SquareTex' in item['AssetPath']:
  variants.append(item)
layout={'source':str(source_path.relative_to(ROOT)).replace('\\','/'),'mesh':'assets/scene/city-background-mesh.json','nodes':nodes,'textures':textures,'missing':missing,'manifestVariantEvidence':variants,'notes':['Background and foreground positions/rotation/scale are taken from the CURRENT MainCityRoot source, not inferred from a screenshot.','Background/foreground share CityBgSubMesh; each of 4 material slots reads its own part texture, not one full-image UV.','Foreground exists only when corresponding source image/asset is available; original game also gates it by device grade.']}
(SCENE/'maincity-layout.json').write_text(json.dumps(layout,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'hooks':len(slots),'textSlots':sum(v['text'] is not None for v in slots.values()),'fonts':sorted(font_names),'backgroundVertices':count,'backgroundSubMeshes':len(submeshes),'backgroundNodes':len(nodes),'textures':sum(len(x) for m in textures.values() for x in m.values()),'missing':missing},ensure_ascii=False),flush=True)
print('Slot11 center',slots['11']['center'],flush=True)
print('Text example',next(row['text'] for row in slots.values() if row['text']),flush=True)