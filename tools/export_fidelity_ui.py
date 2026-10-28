from pathlib import Path
import json,shutil,xml.etree.ElementTree as ET,hashlib
from PIL import Image
ROOT=Path('F:/superstar');OUT=ROOT/'shin-h5';FG=ROOT/'fgui/assets';U=ROOT/'client/SHIN/Assets'
d=json.loads((OUT/'fgui-data.js').read_text(encoding='utf-8').split('=',1)[1].strip().rstrip(';'))
manifest=[]
def copy(src,dst):
 dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);manifest.append({'source':str(src.relative_to(ROOT)).replace('\\','/'),'output':str(dst.relative_to(OUT)).replace('\\','/'),'sha256':hashlib.sha256(dst.read_bytes()).hexdigest()})
for pkg in ['Main_01','ChessboardEvent_01','BlindBox_01']:
 root=ET.parse(FG/pkg/'package.xml').getroot();pid=root.get('id');p=d['packages'].setdefault(pid,{'name':pkg,'items':{}})
 for el in root.find('resources'):
  if el.tag!='image':continue
  src=FG/pkg/el.get('path').lstrip('/')/el.get('name');dest=OUT/'assets/ui'/pkg/(el.get('id')+'.png');copy(src,dest)
  with Image.open(src) as im:w,h=im.size
  item={'kind':'image','name':el.get('name'),'width':w,'height':h,'url':str(dest.relative_to(OUT)).replace('\\','/')}
  for k in ['scale','scale9grid']:
   if el.get(k):item[k]=[int(x) for x in el.get(k).split(',')] if k=='scale9grid' else el.get(k)
  p['items'][el.get('id')]=item
(OUT/'fgui-data.js').write_text('window.FGUI_DATA = '+json.dumps(d,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')+';\n',encoding='utf-8')
for src in (U/'ResourcesAssets/Texture/Block8x8/ChanceIcon').glob('*_01.png'):copy(src,OUT/'assets/scene/chance'/src.name)
copy(U/'ResourcesAssets/Texture/ArtisticFont/zh_cn/img_card_title_zh_cn.png',OUT/'assets/scene/chance/title.png')
m={};exec((OUT/'scripts/export_config.py').read_text(encoding='utf-8').split('squares=')[0],m)
bases={}
for row in m['rows']('map_base'):
 bid=m['num'](row,1)
 if bid not in [1,2,41]:continue
 coords=[]
 for k in range(6,11):
  v=m['fields'](row[k][0]);coords.append([m['num'](v,1),m['num'](v,2)])
 bases[str(bid)]={'positions':coords,'order':row[5],'board':m['txt'](row,3),'background':m['txt'](row,4)}
buildings={}
for bid in [1,2,41]:
 copy(U/f'ResourcesAssets/Texture/Block10x10/BuildingBg/bg_build_{bid}.png',OUT/f'assets/scene/bg_build_{bid}.png')
 for folder,prefix in [('Building','icon_build_'),('BuildingIcon','icon_build_s_')]:
  for src in (U/f'ResourcesAssets/TextureRule/{folder}').glob(f'{prefix}{bid:03d}_*.png'):
   copy(src,OUT/'assets/scene/buildings'/src.name)
   with Image.open(src) as im:buildings[src.name]=list(im.size)
(OUT/'assets/scene/building-layout.json').write_text(json.dumps({'bases':bases,'images':buildings},ensure_ascii=False,separators=(',',':')),encoding='utf-8')
copy(FG/'Common/Font/NotoSansSCBold.ttf',OUT/'assets/fonts/NotoSansSCBold.ttf')
(OUT/'fidelity-assets-source.json').write_text(json.dumps({'files':manifest,'branch':'original (no assets_CN override)','mapBases':[1,41,2]},ensure_ascii=False,indent=2),encoding='utf-8')
print('Exported',len(manifest),'original files;',len(buildings),'building images')
