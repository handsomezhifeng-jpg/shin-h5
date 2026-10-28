from pathlib import Path
import json, re
r=Path('F:/superstar');out=r/'shin-h5'
base=r/'client/SHIN/Assets/ResourcesAssets/Config/Data/Default'
def varint(b,p):
 n=s=0
 while True:
  x=b[p];p+=1;n|=(x&127)<<s
  if not x&128:return n,p
  s+=7
  if s>70:raise ValueError('invalid varint')
def fields(b):
 p=0;d={}
 while p<len(b):
  tag,p=varint(b,p);wire=tag&7;k=tag>>3
  if wire==0:v,p=varint(b,p)
  elif wire==2:
   n,p=varint(b,p);v=b[p:p+n];p+=n
  elif wire==1:v=b[p:p+8];p+=8
  elif wire==5:v=b[p:p+4];p+=4
  else:raise ValueError(str(wire))
  d.setdefault(k,[]).append(v)
 return d
def rows(name):return [fields(x) for x in fields((base/(name+'.bytes')).read_bytes())[1]]
def num(d,k,default=0):return d.get(k,[default])[0]
def txt(d,k):
 v=d.get(k,[b''])[0];return v.decode('utf-8') if isinstance(v,bytes) else str(v)
squares=[{'id':num(d,1),'type':num(d,6),'param':num(d,7),'groups':d.get(3,[])} for d in rows('square_group') if num(d,1)>0]
chances=[{'id':num(d,1),'pool':num(d,2),'weight':num(d,3),'titleKey':num(d,4),'type':num(d,5),'param':num(d,6),'quality':num(d,7),'pic':txt(d,8),'descriptionKey':num(d,10)} for d in rows('chance') if num(d,1)>0]
maps=[]
for d in rows('map')[:3]:maps.append({'id':num(d,1),'nameKey':num(d,2),'baseId':num(d,3),'buildIds':d.get(4,[]),'inflation':num(d,5)/10000,'fundBase':num(d,6)})
# Exact ordered grid positions in the original prefab.
prefab=(r/'client/SHIN/Assets/ResourcesAssets/Prefabs/Model/City/NormalChessboard_01.prefab').read_text(encoding='utf-8-sig')
instances=[]
for block in re.split(r'(?m)^--- !u!',prefab):
 if not block.startswith('1001 '):continue
 vals={k:v for k,v in re.findall(r'propertyPath: ([^\n]+)\n\s+value: ([^\n]*)',block)}
 if 'm_Name' in vals or 'm_LocalPosition.x' in vals:
  instances.append(vals)
(out/'outputs/prefab-positions.json').write_text(json.dumps(instances,ensure_ascii=False,indent=2),encoding='utf-8')
positions=[{'id':int(v['m_Name']),'x':float(v['m_LocalPosition.x']),'z':float(v['m_LocalPosition.z'])} for v in instances if v.get('m_Name','').isdigit()]
positions.sort(key=lambda v:v['id'])
globals={txt(d,1):num(d,2) for d in rows('global_variables') if any(k in txt(d,1) for k in ['DICE','SHIELD','GACHA','BUILDING','PRISON','ROLL'])}
bets=[{'min':num(d,2),'values':d.get(3,[]),'activity':d.get(4,[])} for d in rows('dice_bet') if num(d,1)==1]
buildCosts=[{'id':num(d,1),'level':num(d,2),'cost':num(d,3)} for d in rows('build_level') if num(d,1)>0]
gacha=[]
for d in rows('gacha'):
 if num(d,2)!=1:continue
 rewards=[{'id':num(fields(v),1),'count':num(fields(v),2)} for v in d.get(7,[]) if isinstance(v,bytes)]
 gacha.append({'id':num(d,1),'weight':num(d,6),'icon':txt(d,3),'rewards':rewards})
data={'globals':globals,'bets':bets,'buildCosts':buildCosts,'gacha':gacha,'positions':positions,'squares':squares,'chances':chances,'maps':maps,'version':1,'source':'client/SHIN/Assets/ResourcesAssets/Config/Data/Default'}
language=json.loads((r/'client/SHIN/Assets/ResourcesAssets/Lang/Default/lang_zh_cn.txt').read_text(encoding='utf-8-sig'))
lookup={int(row['key']):row['value'] for row in language['lang']}
for chance in data['chances']:
 chance['title']=lookup.get(chance['titleKey'],'机会')
 chance['description']=lookup.get(chance['descriptionKey'],'')
for mapcfg in data['maps']:mapcfg['name']=lookup.get(mapcfg['nameKey'],'地图'+str(mapcfg['id']))
(out/'game-data.js').write_text('window.GAME_DATA = '+json.dumps(data,ensure_ascii=False,separators=(',',':'))+';\n',encoding='utf-8')
print('原配表导出:',len(squares),'格,',len(chances),'张机会卡,',len(maps),'张地图')
print('格子序列:',[(s['id'],s['type']) for s in squares]);print('地图:',maps);print('prefab instances',len(instances));print(instances[:2])