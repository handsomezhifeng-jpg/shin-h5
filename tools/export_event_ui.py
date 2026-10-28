#!/usr/bin/env python3
"""Incrementally add the original event UI and glyph images; never rebuild scene assets."""
from pathlib import Path
import json,re,shutil,hashlib,xml.etree.ElementTree as ET
from PIL import Image
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parents[1];FGUI=ROOT/'fgui/assets';DATAFILE=OUT/'fgui-data.js'
raw=DATAFILE.read_text(encoding='utf8');data=json.loads(raw[raw.index('{'):raw.rfind('}')+1]);original=json.loads(json.dumps(data));index={};names={};records=[];issues=[];seen=set();added=[];font_updated=[]
for folder in sorted(FGUI.iterdir()):
 p=folder/'package.xml'
 if not p.is_file():continue
 xml=ET.parse(p).getroot();pid=xml.get('id')
 if not pid:continue
 entries={e.get('id'):{'kind':e.tag,'attrs':dict(e.attrib)}for e in xml.find('resources')if e.get('id')and e.tag!='folder'}
 index[pid]={'name':folder.name,'folder':folder,'items':entries};names[folder.name]=pid
pids=sorted(index,key=len,reverse=True)
def sourcepath(pid,attrs):return index[pid]['folder']/attrs.get('path','/').lstrip('/')/attrs.get('name','')
def nodejson(e):return {'tag':e.tag,'attrs':dict(e.attrib),'children':[nodejson(c)for c in e]}
def resolve(url):
 value=url.removeprefix('ui://')
 return next(((pid,value[len(pid):])for pid in pids if value.startswith(pid)),None)
def record(src,dest,reused):
 records.append({'source':str(src.relative_to(ROOT)).replace('\\','/'),'output':str(dest.relative_to(OUT)).replace('\\','/'),'reused':reused,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
def fields(line):return {k:(v[1:-1]if v.startswith('"')else v)for k,v in re.findall(r'(\w+)=("[^"]*"|\S+)',line)}
def bitmap(pid,rid,item,source):
 lines=source.read_text(encoding='utf-8-sig').splitlines();header=fields(next(line for line in lines if line.startswith('info ')));glyphs={}
 for line in lines:
  if not line.startswith('char '):continue
  a=fields(line);gid=a.get('img')
  if not gid:issues.append({'font':item['name'],'reason':'bitmap glyph has no img resource ID','line':line});continue
  if gid.startswith('ui://'):
   target=resolve(gid)
   if not target:raise ValueError('Unknown bitmap glyph URI '+gid)
   gpid,grid=target
  else:gpid,grid=pid,gid
  image=ensure(gpid,grid)
  assert image and image.get('url'),(item['name'],gid)
  glyphs[chr(int(a['id']))]={'image':{**image,'pkg':gpid,'id':grid},'xoffset':int(a.get('xoffset',0)),'yoffset':int(a.get('yoffset',0)),'xadvance':int(a.get('xadvance',0))}
 item['bitmap']={'size':int(header['size']),'resizable':header.get('resizable','false')=='true','colored':header.get('colored','false')=='true','glyphs':glyphs};font_updated.append({'pkg':pid,'id':rid,'name':item['name'],'glyphs':len(glyphs)})
 return item

def ensure(pid,rid):
 if pid not in index or rid not in index[pid]['items']:raise ValueError('Original resource absent '+pid+'/'+rid)
 pkg=index[pid];entry=pkg['items'][rid];attrs=entry['attrs'];source=sourcepath(pid,attrs)
 if 'Draw'in source.parts:raise ValueError('Refusing design draft '+str(source))
 if not source.is_file():raise FileNotFoundError(str(source))
 data['byName'][pkg['name']]=pid;items=data['packages'].setdefault(pid,{'name':pkg['name'],'items':{}})['items'];item=items.get(rid)
 if (pid,rid)in seen:return item
 seen.add((pid,rid))
 if item is None:
  item={'kind':entry['kind'],'name':attrs.get('name',''),'width':0,'height':0};items[rid]=item;added.append({'pkg':pid,'id':rid,'name':item['name']})
  for k in ['scale','gridTile']:
   if k in attrs:item[k]=attrs[k]
  if attrs.get('scale9grid'):item['scale9grid']=[int(v)for v in attrs['scale9grid'].split(',')]
 if entry['kind']=='component':
  xml=ET.fromstring(source.read_text(encoding='utf-8-sig'))
  if 'xml'not in item:
   item['xml']=nodejson(xml);item['width'],item['height']=[float(v)for v in xml.get('size','0,0').split(',')[:2]]
  for child in xml.iter():
   src=child.get('src')
   if src and child.tag in ['component','image','movieclip','loader3D']:ensure(child.get('pkg',pid),src)
   for attr,value in child.attrib.items():
    if attr.startswith('designImage'):continue
    for uri in re.findall(r'ui://[A-Za-z0-9_]+',value):
     ref=resolve(uri)
     if ref:ensure(*ref)
  return item
 if item.get('url'):dest=OUT/item['url']
 else:
  dest=OUT/'assets/ui'/pkg['name']/(rid+source.suffix.lower());item['url']=str(dest.relative_to(OUT)).replace('\\','/')
 reused=dest.is_file();dest.parent.mkdir(parents=True,exist_ok=True)
 if not reused:shutil.copy2(source,dest)
 record(source,dest,reused)
 if entry['kind']=='image'and not item.get('width'):
  with Image.open(dest)as im:item['width'],item['height']=im.size
 if entry['kind']=='font'and source.suffix.lower()=='.fnt':bitmap(pid,rid,item,source)
 return item

# Runtime-created attack selector is not reachable from the window XML.
pid=names['MakeTrouble'];rid=next(r for r,e in index[pid]['items'].items()if e['attrs'].get('name')=='com_selectBuilding.xml');ensure(pid,rid);data['roots']['com_selectBuilding']={'pkg':pid,'id':rid}
# Existing used ArtFont bitmap resources; recursively add each true image glyph.
for pid,pkg in list(data['packages'].items()):
 if pkg['name']!='ArtFont':continue
 for rid,item in list(pkg['items'].items()):
  if item['kind']=='font'and item['name'].endswith('.fnt'):ensure(pid,rid)
# Ordinary default skin. Existing original resources remain in place and are reused.
for pname in ['BlindBox_01']:
 pid=names[pname]
 for rid,e in index[pid]['items'].items():
  n=e['attrs'].get('name','')
  if n in {'bg_BlindBox_background.png','img_BlindBox_blue.png','bg_BlindBox_blue01.png','bg_BlindBox_blue02.png','bg_BlindBox_blue03.png'}or re.fullmatch(r'icon_BlindBox_figure0[234](?:_s)?\.png',n):ensure(pid,rid)

# Explicitly verify this increment did not replace existing component trees or scene files.
for pid,pkg in original['packages'].items():
 for rid,item in pkg['items'].items():
  after=dict(data['packages'][pid]['items'][rid]);after.pop('bitmap',None);before=dict(item);before.pop('bitmap',None)
  assert before==after,('Unrelated existing FGUI resource changed',pid,rid)
for row in font_updated:
 item=data['packages'][row['pkg']]['items'][row['id']]
 assert item['bitmap']['glyphs']and all(Path(OUT/g['image']['url']).is_file()for g in item['bitmap']['glyphs'].values())
DATAFILE.write_text('window.FGUI_DATA = '+json.dumps(data,ensure_ascii=False,separators=(',',':'),allow_nan=False)+';\n',encoding='utf8')

# Only localized title artwork actually requested by these event-window controllers.
event_dir=OUT/'assets/scene/events';event_dir.mkdir(parents=True,exist_ok=True)
event_artistic_fonts={}
title_fields=[
 ('PrisonWindow','loader_title_main','img_main_title_01','PrisonWindow.cs',208),
 ('PrisonWindow','loader_title_fail','img_main_title_03','PrisonWindow.cs',209),
 ('PrisonWindow','loader_title_success','img_main_title_04','PrisonWindow.cs',210),
 ('ChanceWindow','icon_title','img_card_title','ChanceWindow.cs',146),
 ('BlindBoxRewardWindow','loader_title','img_BlindBox_title_01','BlindBoxRewardWindow.cs',200),
 ('BlindBoxRewardWindow','loader_guessingBox_hint','img_BlindBox_title_02','BlindBoxRewardWindow.cs',201),
 ('BlindBoxRewardWindow','loader_star','img_Guessing_box_Lucky','BlindBoxRewardWindow.cs',197),
]
for window,field,name,code,line in title_fields:
 source=ROOT/'client/SHIN/Assets/ResourcesAssets/Texture/ArtisticFont/zh_cn'/(name+'_zh_cn.png')
 assert source.is_file(),str(source)
 dest=event_dir/source.name;reused=dest.is_file()
 if not reused:shutil.copy2(source,dest)
 assert source.read_bytes()==dest.read_bytes(),('Localized event image differs',str(dest))
 record(source,dest,reused)
 with Image.open(dest)as im:width,height=im.size
 event_artistic_fonts.setdefault(window,{})[field]={'name':name,'url':str(dest.relative_to(OUT)).replace('\\','/'),'width':width,'height':height,'source':str(source.relative_to(ROOT)).replace('\\','/'),'code':'client/SHIN/Assets/Script/Game/moduls/ChessboardEvent/'+code,'line':line}
# Same original Chinese language source and key/value decoding as scripts/export_config.py.
language_path=ROOT/'client/SHIN/Assets/ResourcesAssets/Lang/Default/lang_zh_cn.txt'
language=json.loads(language_path.read_text(encoding='utf-8-sig'));lookup={int(row['key']):row['value']for row in language['lang']}
reward_code=ROOT/'client/SHIN/Assets/Script/Game/moduls/ChessboardEvent/BlindBoxRewardWindow.cs'
reward_ids={int(value)for value in re.findall(r'LangUtil\.Str(?:Format)?\(\s*(\d+)',reward_code.read_text(encoding='utf-8-sig'))}
string_ids={11200001,11200003,11200016,11200017,11200029,10200033,10900005,10900002,11200024,11200025,10900008,10900009,10900001,10900006,10700025,10100017}|reward_ids
assert string_ids<=lookup.keys(),sorted(string_ids-lookup.keys())
strings={str(key):lookup[key]for key in sorted(string_ids)}
strings_path=event_dir/'strings.json';strings_path.write_text(json.dumps(strings,ensure_ascii=False,indent=2)+'\n',encoding='utf8');record(language_path,strings_path,False)

manifest={'sourceRoot':'fgui/assets','preservedBranch':'Original default assets; assets_CN is never read.','addedResources':added,'bitmapFonts':font_updated,'records':records,'issues':issues}
manifest['eventArtisticFonts']=event_artistic_fonts
manifest['eventStrings']={'url':'assets/scene/events/strings.json','source':str(language_path.relative_to(ROOT)).replace('\\','/'),'ids':sorted(string_ids),'blindBoxRewardReferencedIds':sorted(reward_ids)}
manifest['eventArtisticFontNotes']=['DestroyBuildingWindow and BlindBoxWindow themselves do not call SetArtisticFont in the current original code; BlindBox localized artwork belongs to BlindBoxRewardWindow.','ResUtils.SetArtisticFont appends the current language code; this export selects the actual zh_cn files.']
previous_path=OUT/'assets-event-ui-source.json'
if previous_path.is_file():
 previous=json.loads(previous_path.read_text(encoding='utf8'));prior=previous.get('addedResources',[]);manifest['addedResources']=list({(r['pkg'],r['id']):r for r in prior+added}.values())
(OUT/'assets-event-ui-source.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({'addedResources':added,'bitmapFonts':font_updated,'rootsAdded':{'com_selectBuilding':data['roots']['com_selectBuilding']},'copiedFiles':sum(not r['reused']for r in records),'reusedFiles':sum(r['reused']for r in records),'issues':issues},ensure_ascii=False))