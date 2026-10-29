#!/usr/bin/env python3
"""Incremental original milestone UI export; never invokes scene/config exporters."""
from pathlib import Path
import ast,json,re,hashlib,shutil,xml.etree.ElementTree as ET
from PIL import Image
# Reuse bounded event exporter resource helpers, but none of its export/write phase.
helper=Path(__file__).with_name('export_event_ui.py').read_text(encoding='utf8').split('# Runtime-created attack selector')[0]
helper=helper.replace("xml=ET.fromstring(source.read_text(encoding='utf-8-sig'))","xml=parse_xml(source)")
exec(compile(helper,'incremental resource helpers','exec'))
# Two original source folders reuse a package ID. Native game names Milestone explicitly.
canonical_folder=FGUI/'Milestone';canonical_xml=ET.parse(canonical_folder/'package.xml').getroot();canonical_pid=canonical_xml.get('id')
index[canonical_pid]={'name':'Milestone','folder':canonical_folder,'items':{e.get('id'):{'kind':e.tag,'attrs':dict(e.attrib)}for e in canonical_xml.find('resources')if e.get('id')and e.tag!='folder'}}
names['Milestone']=canonical_pid
if canonical_pid in data['packages']:data['packages'][canonical_pid]['name']='Milestone'
# Same read-only normalization used by the original exporter for malformed editor XML.
mod=ast.parse(Path(__file__).with_name('export_assets.py').read_text(encoding='utf8'))
exec(compile(ast.Module(body=[n for n in mod.body if isinstance(n,ast.FunctionDef)and n.name=='dedupe_attributes'],type_ignores=[]),'XML attribute normalizer','exec'))
xml_warnings=[]
def quote_tag_attributes(match):
 tag=match.group(0);out=[];i=0;quote=None
 while i<len(tag):
  char=tag[i]
  if quote:
   out.append(char)
   if char==quote:quote=None
   i+=1;continue
  if char in ['"',"'"]:quote=char;out.append(char);i+=1;continue
  if char.isspace():
   attr=re.match(r'(\s+[\w:-]+=)([^\s\"\'<>`=]+)(?=\s|/?>)',tag[i:])
   if attr:out.extend([attr.group(1),'"',attr.group(2),'"']);i+=len(attr.group(0));continue
  out.append(char);i+=1
 return ''.join(out)
def parse_xml(source):
 raw=source.read_text(encoding='utf-8-sig');cleaned=re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]','',raw)
 cleaned=re.sub(r'<(?![!?/])[^<>]+>',quote_tag_attributes,cleaned)
 cleaned=re.sub(r'<(?![!?/])[^<>]+>',dedupe_attributes,cleaned)
 if cleaned!=raw:xml_warnings.append(source.relative_to(ROOT).as_posix())
 return ET.fromstring(cleaned)
# Original XML includes stale default-loader IDs; retain and report them, never invent art.
ensure_original=ensure;missing_seen=set()
def ensure(pid,rid):
 key=(pid,rid)
 if pid not in index or rid not in index[pid]['items']:
  if key not in missing_seen:issues.append({'pkg':pid,'id':rid,'reason':'Original referenced resource ID absent from current original package.xml'});missing_seen.add(key)
  return None
 source=sourcepath(pid,index[pid]['items'][rid]['attrs'])
 if not source.is_file():
  if key not in missing_seen:issues.append({'pkg':pid,'id':rid,'source':source.relative_to(ROOT).as_posix(),'reason':'Original source file missing'});missing_seen.add(key)
  return None
 return ensure_original(pid,rid)
roots_added={}
def root(pname,filename,alias=None):
 pid=names[pname];rid=next(r for r,e in index[pid]['items'].items()if e['attrs'].get('name')==filename);ensure(pid,rid);key=alias or filename.removesuffix('.xml');ref={'pkg':pid,'id':rid};data['roots'][key]=ref;roots_added[key]=ref;return ref
for filename in ['Comp_MileStoneMainProgress.xml','Com_MileStoneReward.xml','main_Activity_MileStoneItem.xml','progress_mileStoneActivity.xml']:root('Main',filename)
for filename in ['MileStoneNoRankWindow.xml','MileStoneRankLockWindow.xml','MileStoneRulesWindow.xml','Comp_MileStoneUnLockRank.xml','Comp_StonelDesAndLoot.xml','Comp_MileStoneReward.xml','card.xml']:root('Milestone',filename)
root('Milestone','MileStoneRankLockWindow.xml','MileStoneRankWindow')
for pname,filename in [('CommonActivity','Comp_StoneBigReward.xml'),('Common','Com_CommonTip.xml'),('Common','Com_CommonTipProgress.xml')]:root(pname,filename)
# Ensure all list default/item templates are exported and callable by their native names.
for pid,pkg in list(data['packages'].items()):
 if pkg['name']not in ['Milestone','CommonActivity']:continue
 for rid,item in list(pkg['items'].items()):
  if item.get('kind')!='component' or not item.get('xml'):continue
  key=item['name'].removesuffix('.xml')
  if key not in data['roots']:data['roots'][key]={'pkg':pid,'id':rid}
  roots_added[key]=data['roots'][key]
# Current default original IP branch: Milestone_01 dynamic card/goal images.
skin_pid=names['Milestone_01']
for rid,e in index[skin_pid]['items'].items():
 if '/Draw/'in e['attrs'].get('path',''):continue
 ensure(skin_pid,rid)

scene=OUT/'assets/scene/milestone';scene.mkdir(parents=True,exist_ok=True);dynamic={};package_configs={}
def copy_image(source,key):
 assert source.is_file(),str(source)
 dest=scene/source.name;reused=dest.is_file()
 if not reused:shutil.copy2(source,dest)
 assert source.read_bytes()==dest.read_bytes(),('Original dynamic resource differs',str(dest))
 record(source,dest,reused)
 with Image.open(dest)as im:width,height=im.size
 row={'url':dest.relative_to(OUT).as_posix(),'width':width,'height':height,'source':source.relative_to(ROOT).as_posix()};dynamic[key]=row;return row
for ident in [8,24]:
 name='icon_milestone_'+str(ident).zfill(4);copy_image(ROOT/'client/SHIN/Assets/ResourcesAssets/TextureRule/Milestone'/(name+'.png'),name)
# Decode the exact requested packaging rows with the existing original protobuf decoder.
config_module=ast.parse((OUT/'scripts/export_config.py').read_text(encoding='utf8'))
exec(compile(ast.Module(body=[n for n in config_module.body if isinstance(n,ast.FunctionDef)],type_ignores=[]),'original config decoder','exec'))
base=ROOT/'client/SHIN/Assets/ResourcesAssets/Config/Data/Default'
for row in rows('activity_milestone_ui'):
 ident=num(row,1)
 if ident not in [8,24]:continue
 cfg={'skinId':ident,'title':txt(row,2),'noRankBgMain':txt(row,3),'noRankBg':txt(row,4),'rankBg':[v.decode('utf8')for v in row.get(5,[])]};package_configs[str(ident)]=cfg
 for stem in [cfg['title'],cfg['noRankBg'],*cfg['rankBg']]:
  path=ROOT/'client/SHIN/Assets/ResourcesAssets/Texture/ArtisticFont/zh_cn'/(stem+'_zh_cn.png')
  if not path.is_file() and stem.startswith('img_tournament_banner_'):path=ROOT/'client/SHIN/Assets/ResourcesAssets/Texture/Block10x10'/(stem+'.png')
  copy_image(path,stem)
assert set(package_configs)=={'8','24'}
copy_image(ROOT/'client/SHIN/Assets/ResourcesAssets/Texture/Block8x8/MileStoneIcon/bg_milestone_main_01.png','bg_milestone_main_01')
# Tooltip title loaded dynamically by the native NoRank window.
for stem in ['tipsTitle']:
 path=ROOT/'client/SHIN/Assets/ResourcesAssets/Texture/ArtisticFont/zh_cn'/(stem+'_zh_cn.png')
 if path.is_file():copy_image(path,stem)
 else:issues.append({'name':stem,'reason':'requested original Chinese tooltip title missing at normal source path'})
# Actual native literal strings used by the exported windows, kept verbatim.
language_path=ROOT/'client/SHIN/Assets/ResourcesAssets/Lang/Default/lang_zh_cn.txt';language=json.loads(language_path.read_text(encoding='utf-8-sig'));lookup={int(row['key']):row['value']for row in language['lang']};string_ids=set()
for filename in ['MileStoneNoRankWindow.cs','MileStoneRankLockWindow.cs','MileStoneRulesWindow.cs']:
 code=ROOT/'client/SHIN/Assets/Script/Game/moduls/MailStone'/filename
 string_ids.update(int(value)for value in re.findall(r'LangUtil\.Str(?:Format)?\(\s*(\d+)',code.read_text(encoding='utf-8-sig')))
assert string_ids<=lookup.keys();strings={str(k):lookup[k]for k in sorted(string_ids)};(scene/'strings.json').write_text(json.dumps(strings,ensure_ascii=False,indent=2)+'\n',encoding='utf8');record(language_path,scene/'strings.json',False)

# Original reward imagery used by this activities config, not text or generated substitutes.
activity_config=json.loads((OUT/'assets/activities/config.json').read_text(encoding='utf8'));reward_images={};item_names={};reward_variants={};reward_issues=[]
def package_image(pname,stem):
 pid=names[pname];matches=[(rid,e)for rid,e in index[pid]['items'].items()if e['kind']=='image'and e['attrs'].get('name')==stem+'.png']
 if not matches:return None
 rid,entry=matches[0];item=ensure(pid,rid)
 if not item or not item.get('url'):return None
 return {'url':item['url'],'w':item['width'],'h':item['height'],'width':item['width'],'height':item['height'],'pkg':pname,'id':rid,'icon':stem,'source':sourcepath(pid,entry['attrs']).relative_to(ROOT).as_posix()}
for ident,cfg in activity_config['items'].items():
 item_names[ident]=cfg['name'];stem=cfg['icon'];preferred=['IconItem','IconActivity']if cfg['itemType']==6 else ['IconActivity','IconItem'];image=next((found for pname in preferred if (found:=package_image(pname,stem))),None)
 if image:reward_images[ident]={**image,'name':cfg['name'],'quality':cfg['quality'],'itemId':int(ident),'configuredIcon':stem}
 elif ident=='45020'and stem=='icon_storm_01':
  variants={str(skin):package_image('IconActivity',stem+'_'+str(skin).zfill(2))for skin in [1,3,4,5]};reward_variants[ident]={k:v for k,v in variants.items()if v}
  reward_issues.append({'itemId':45020,'configuredIcon':stem,'reason':'Original icon_storm_01.png does not exist; native ActivityHelper resolves a running Storm activity subCfg.icon. True source variants are exported by activity skin, without pretending the unsuffixed icon exists.','variants':list(reward_variants[ident])})
 else:raise FileNotFoundError('Unresolved requested original item icon '+ident+' '+stem)
for row in rows('player_variables'):
 ident=num(row,1)
 if ident not in range(1,8):continue
 stem=txt(row,3);image=package_image('IconItem',stem)
 if not image:
  source_candidates=[ROOT/'client/SHIN/Assets/ResourcesAssets/TextureRule'/folder/(stem+'.png')for folder in ['IconItem','Shield']]
  source=next((p for p in source_candidates if p.is_file()),None)
  if source:
   exported=copy_image(source,stem);image={**exported,'w':exported['width'],'h':exported['height'],'icon':stem,'pkg':None,'configurationSource':'Original Unity texture exists though absent from current IconItem FGUI package.'}
 assert image,('Original resource icon absent',ident,stem)
 reward_images['resource:'+str(ident)]={**image,'name':lookup.get(num(row,2),activity_config['resourceTypes'][str(ident)]['name']),'resourceId':ident,'configuredIcon':stem,'configuration':'player_variables.config_pic'}
for stem in ['hely_icon_10_01','hely_icon_11_01']:
 image=package_image('GameRule',stem);assert image,stem;dynamic[stem]=image
string_ids.update(range(11500001,11500009));strings={str(k):lookup[k]for k in sorted(string_ids)};(scene/'strings.json').write_text(json.dumps(strings,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

for record_row in records:record_row['sha256']=hashlib.sha256((OUT/record_row['output']).read_bytes()).hexdigest()
# Keep every preexisting tree and resource unchanged (font bitmaps may only be enriched).
for pid,pkg in original['packages'].items():
 for rid,item in pkg['items'].items():
  before=dict(item);after=dict(data['packages'][pid]['items'][rid]);before.pop('bitmap',None);after.pop('bitmap',None);assert before==after,(pid,rid)
DATAFILE.write_text('window.FGUI_DATA = '+json.dumps(data,ensure_ascii=False,separators=(',',':'),allow_nan=False)+';\n',encoding='utf8')
result={'roots':roots_added,'aliases':{'MileStoneRankWindow':'MileStoneRankLockWindow'},'skinPackage':'Milestone_01','packagingConfigs':package_configs,'dynamicImages':dynamic,'rewardImages':reward_images,'itemNames':item_names,'rewardImageVariants':reward_variants,'rewardImageIssues':reward_issues,'stringsURL':'assets/scene/milestone/strings.json','notes':['Package ids8/24 are activity packaging rows, not Milestone_08/24 FGUI IP packages. Original current IP dynamic card art is Milestone_01.','MileStoneRankWindow is an H5 lookup alias of the actual native MileStoneRankLockWindow root.','Screenshot targets: icon_milestone_0008 is the orange; icon_milestone_0024 is a small drum with two drumsticks.','Original component trees, controllers, layout and transitions are preserved. Dynamic lists still need native-layout handling in the H5 renderer.'],'issues':issues}
(scene/'ui.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
proof={'sourceRoot':'fgui/assets','preservedBranch':'Original assets, never assets_CN','addedResources':added,'rootsAdded':roots_added,'fontsUpdated':font_updated,'records':records,'xmlReadOnlyNormalizations':sorted(set(xml_warnings)),'packagingConfigSource':'client/SHIN/Assets/ResourcesAssets/Config/Data/Default/activity_milestone_ui.bytes','issues':issues}
previous_proof=OUT/'assets-milestone-ui-source.json'
if previous_proof.is_file():
 previous=json.loads(previous_proof.read_text(encoding='utf8'));proof['addedResources']=list({(r['pkg'],r['id']):r for r in previous.get('addedResources',[])+added}.values())
(OUT/'assets-milestone-ui-source.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({'roots':roots_added,'addedResourceCount':len(added),'copiedFiles':sum(not r['reused']for r in records),'dynamicImages':dynamic,'xmlNormalizations':sorted(set(xml_warnings)),'issues':issues},ensure_ascii=False))
# Restore exact screenshot skin from original published FGUI atlases after incremental UI export.
import subprocess,sys
subprocess.run([sys.executable,str(OUT/'tools/export_reference_skin_ui.py')],check=True)
