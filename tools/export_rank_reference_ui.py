"""Exact published ranking window skin, limited to original activity UI."""
from pathlib import Path
import json,hashlib,shutil
from PIL import Image
HELPER=Path(__file__).with_name('export_reference_skin_ui.py');scope={'__file__':str(HELPER)};exec(HELPER.read_text(encoding='utf8').split('requested=')[0],scope)
ROOT=scope['ROOT'];OUT=scope['OUT'];GUI=scope['GUI'];package=scope['package'];children=scope['component_children'];extract=scope['image_from_atlas'];Buffer=scope['Buffer'];dest=OUT/'assets/scene/milestone/reference';dest.mkdir(exist_ok=True)
packages={name:package(GUI/(name+'_fui.bytes'))for name in ['Milestone','Common']};byid={p['id']:p for p in packages.values()};records=[];components={};images={}
def controllers(p,rid):
 b=Buffer(p['items'][rid]['rawData']);b.strings=p['strings'];rows=[]
 if not b.seek(0,1):return rows
 for _ in range(b.short()):
  length=b.short();start=b.p;end=start+length;b.seek(start,0);name=b.s();auto=b.boolean();pages=[]
  if b.seek(start,1):
   for _ in range(b.short()):pages.append({'id':b.s(),'name':b.s()})
  rows.append({'name':name,'autoRadioGroupDepth':auto,'pages':pages});b.p=end
 return rows

def component(pname,rid):
 p=packages[pname];item=p['items'][rid];rows=children(p,rid)
 b=Buffer(item['rawData']);b.strings=p['strings'];b.seek(0,2);count=b.short()
 def color():return '#'+''.join(f'{b.byte():02x}'for _ in range(4))
 for n in range(count):
  length=b.short();start=b.p;end=start+length;row=rows[n]
  if b.seek(start,1):row['tooltip']=b.s();row['groupIndex']=b.short()
  if b.seek(start,5):
   if row['type']==3:
    shape=b.byte();row['shapeType']=shape
    if shape:
     row['lineSize']=b.int();row['lineColor']=color();row['fillColor']=color()
     if b.boolean():row['cornerRadius']=[b.read('f')for _ in range(4)]
   elif row['type']in[6,7]:
    row['font']=b.s();row['fontSize']=b.short();row['color']=color();row['align']=b.byte();row['vAlign']=b.byte()
  if row['type']in[6,7]and b.seek(start,6):row['text']=b.s()
  if b.seek(start,2):
   for _ in range(b.short()):
    glen=b.ushort();gend=b.p+glen;gtype=b.byte();controller=b.short();count=b.short()
    if gtype in [1,2]:
     def value():return [b.int(),b.int()]+([b.read('f'),b.read('f')]if gtype==2 else [])
     statuses={}
     for _ in range(count):
      page=b.s()
      if page is not None:statuses[page]=value()
     gear={'type':gtype,'controllerIndex':controller,'statuses':statuses}
     if b.boolean():gear['default']=value()
     row.setdefault('nativeLayoutGears',[]).append(gear)
    b.p=gend
  if b.seek(start,3):
   relations=[]
   for _ in range(b.byte()):
    target=b.short();pairs=[{'type':b.byte(),'percent':b.boolean()}for _ in range(b.byte())];relations.append({'targetIndex':target,'pairs':pairs})
   row['relations']=relations
  b.p=end
 record={'package':pname,'id':rid,'name':item['name'],'width':item['width'],'height':item['height'],'controllers':controllers(p,rid),'children':rows,'sourceFui':p['source'].relative_to(ROOT).as_posix()}
 target=dest/(pname+'_'+item['name']+'_published.json');target.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf8');components[pname+'/'+item['name']]={'url':target.relative_to(OUT).as_posix(),'id':rid,'width':item['width'],'height':item['height']};return record
roots=[('Milestone','r5dd1ke46rl'),('Milestone','o24d1ke475g'),('Milestone','v4q91ke474x'),('Milestone','v4q91ke474q'),('Milestone','v4q91ke474u'),('Common','kdeb1ke46vw')]
metadata=[component(*ref)for ref in roots]
requested={'Common':['kdeb1ke46vs','kdeb1ke46vu','mzam1ke46sh','mann1ke46xt'],'Milestone':['udcm1ke46rf','ugwg1ke46ol','udcm1ke46re']}
for pname,ids in requested.items():
 p=packages[pname]
 for rid in ids:
  im,atlas,item,sprite=extract(p,rid);target=dest/(pname+'_'+rid+'_default.png');im.save(target);grid=item['scale9grid'];usage=[]
  for comp in metadata:
   for child in comp['children']:
    childpkg=child.get('pkg')or packages[comp['package']]['id']
    matched=child.get('src')==rid and childpkg==p['id']or child.get('url')=='ui://'+p['id']+rid
    if matched:usage.append({'controlPath':comp['package']+'/'+comp['name']+'/'+child['name'],'layout':{k:child[k]for k in ['xy','size','pivot','anchor','scale','rotation','color']},'gears':child['gears']})
  row={'pkg':pname,'id':rid,'name':item['name'],'url':target.relative_to(OUT).as_posix(),'width':im.width,'height':im.height,'w':im.width,'h':im.height,'scale9grid':grid,'nineSliceInsets':None if grid is None else {'left':grid[0],'top':grid[1],'right':im.width-grid[0]-grid[2],'bottom':im.height-grid[1]-grid[3]},'atlasRotationRestored':True,'rotation':0,'usages':usage,'sourceFui':p['source'].relative_to(ROOT).as_posix(),'sourceAtlas':atlas.relative_to(ROOT).as_posix(),'sprite':sprite};image_key=('rank_'+item['name'])if pname=='Milestone'else item['name'];images[image_key]=row;records.append({**row,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
goldsource=ROOT/'peibiao/fairygui/trunk/assets/Common/Images/Btn/btn_com_close_new.png';goldtarget=dest/'Common_btn_com_close_new_screenshot.png';shutil.copyfile(goldsource,goldtarget)
with Image.open(goldtarget)as gold:w,h=gold.size
goldrow=dict(images['btn_com_close_new']);goldrow.update({'publishedVariantURL':goldrow['url'],'url':goldtarget.relative_to(OUT).as_posix(),'width':w,'height':h,'w':w,'h':h,'source':goldsource.relative_to(ROOT).as_posix(),'referenceVariant':'Original trunk source gold circle redX matches user screenshot; current native atlas is blue variant.'});images['btn_com_close_new']=goldrow;records.append({**goldrow,'sha256':hashlib.sha256(goldtarget.read_bytes()).hexdigest()})
ui_path=OUT/'assets/scene/milestone/ui.json';ui=json.loads(ui_path.read_text(encoding='utf8'));ui.setdefault('referenceSkinImages',{}).update(images);ui.setdefault('referenceSkinComponents',{}).update(components)
ui['rankWindowReference']={'lockedRoot':'Milestone/MileStoneRankLockWindow','unlockedRoot':'Milestone/MileStoneRankShowInfoWindow','legacyRoot':'Milestone/MileStoneRankLockWindowOld','lockedPoster':{'configuredField':'activity_milestone_ui.rankBg[0]','image':ui['dynamicImages']['img_rules_banner_8'],'control':'loader_titleBg'},'unlockedPoster':{'configuredField':'activity_milestone_ui.rankBg[0]','image':ui['dynamicImages']['img_rules_banner_8'],'control':'loader_titleBg'},'closeButton':'Common/btn_close_03','closeImage':'btn_com_close_new','lockImage':'icon_lock','progressFrame':'rank_bg_milestone_progress_02','notes':['Both current locked and unlocked code load rankBg[0]. The empty orange tournament banner is not their poster.','The screenshot is locked:0/1, final lock, goal explanation. Current unlocked native root has ranking rows; retain distinct states.','Published current RankLock differs substantially from editor XML: rank progress is milestoneRankProgress component; current published RankLock has no ctrl_lockType. That controller belongs to legacy root.','MilestoneEventTemplateWindow_fui.bytes is absent from original GUI; editor package shares Milestone packageID, but runtime Config.package is Milestone.','Current native Common package and bundle contain later blue close button. Gold circle/redX is exact preserved peibiao/fairygui/trunk source, visually confirmed against screenshot.']}
ui_path.write_text(json.dumps(ui,ensure_ascii=False,indent=2)+'\n',encoding='utf8');(OUT/'assets-rank-reference-source.json').write_text(json.dumps({'records':records,'components':metadata,'reference':ui['rankWindowReference']},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({'images':{k:[v['url'],v['width'],v['height'],v['scale9grid']]for k,v in images.items()},'components':components},ensure_ascii=False))