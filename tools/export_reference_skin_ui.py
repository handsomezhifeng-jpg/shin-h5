#!/usr/bin/env python3
"""Extract exact requested image resources from original published FairyGUI atlases."""
from pathlib import Path
import struct,json,hashlib
from PIL import Image
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parents[1];GUI=ROOT/'client/SHIN/Assets/ResourcesAssets/GUI'
class Buffer:
 def __init__(self,data):self.data=data;self.p=0;self.strings=[]
 def read(self,fmt):n=struct.calcsize('>'+fmt);v=struct.unpack_from('>'+fmt,self.data,self.p)[0];self.p+=n;return v
 def byte(self):return self.read('B')
 def short(self):return self.read('h')
 def ushort(self):return self.read('H')
 def int(self):return self.read('i')
 def boolean(self):return self.byte()==1
 def string(self,length=None):
  if length is None:length=self.ushort()
  value=self.data[self.p:self.p+length].decode('utf8');self.p+=length;return value
 def s(self):
  n=self.ushort()
  return None if n==65534 else ''if n==65533 else self.strings[n]
 def seek(self,start,index):
  previous=self.p;self.p=start;count=self.byte();small=self.boolean()
  if index>=count:self.p=previous;return False
  self.p+=index*(2 if small else 4);offset=self.short()if small else self.int()
  if offset<=0:self.p=previous;return False
  self.p=start+offset;return True

def package(path):
 b=Buffer(path.read_bytes());assert b.read('I')==0x46475549;b.version=b.int();assert not b.boolean(),'Compressed package not supported';pid=b.string();name=b.string();b.p+=20;start=b.p
 assert b.seek(start,4);b.strings=[b.string()for _ in range(b.int())]
 if b.seek(start,5):
  for _ in range(b.int()):index=b.ushort();length=b.int();b.strings[index]=b.string(length)
 b.seek(start,0)
 for _ in range(b.short()):b.s();b.s()
 branch_count=b.short()if b.version>=2 else 0;branches=[b.s()for _ in range(branch_count)];items={}
 b.seek(start,1)
 for _ in range(b.short()):
  size=b.int();end=b.p+size;kind=b.byte();rid=b.s();rname=b.s();sourcepath=b.s();filename=b.s();exported=b.boolean();width=b.int();height=b.int();item={'kind':kind,'id':rid,'name':rname,'file':filename,'width':width,'height':height,'scale9grid':None}
  if kind==0:
   scale=b.byte()
   if scale==1:item['scale9grid']=[b.int()for _ in range(4)];item['gridTile']=b.int()
   b.boolean()
  if kind==3:
   item['extension']=b.byte();length=b.int();item['rawData']=b.data[b.p:b.p+length]
  items[rid]=item;b.p=end
 sprites={};b.seek(start,2)
 for _ in range(b.short()):
  size=b.ushort();end=b.p+size;rid=b.s();atlas=b.s();rect=[b.int()for _ in range(4)];rotated=b.boolean();offset=[0,0]
  if b.version>=2 and b.boolean():offset=[b.int(),b.int()];original=[b.int(),b.int()]
  else:original=[rect[3],rect[2]]if rotated else rect[2:]
  sprites[rid]={'atlas':atlas,'rect':rect,'rotated':rotated,'offset':offset,'originalSize':original};b.p=end
 return {'id':pid,'name':name,'items':items,'sprites':sprites,'source':path,'strings':b.strings}

def component_children(pkg,rid):
 b=Buffer(pkg['items'][rid]['rawData']);b.strings=pkg['strings'];children=[]
 assert b.seek(0,2)
 for _ in range(b.short()):
  length=b.short();start=b.p;end=start+length;b.seek(start,0);typ=b.byte();src=b.s();pid=b.s();ident=b.s();name=b.s();xy=[b.int(),b.int()];size=None;scale=[1,1]
  if b.boolean():size=[b.int(),b.int()]
  if b.boolean():[b.int()for _ in range(4)]
  if b.boolean():scale=[b.read('f'),b.read('f')]
  if b.boolean():[b.read('f')for _ in range(2)]
  pivot=[0,0];anchor=False
  if b.boolean():pivot=[b.read('f'),b.read('f')];anchor=b.boolean()
  alpha=b.read('f');rotation=b.read('f');visible=b.boolean();touch=b.boolean();grayed=b.boolean();row={'id':ident,'name':name,'type':typ,'src':src,'pkg':pid,'xy':xy,'size':size,'scale':scale,'pivot':pivot,'anchor':anchor,'alpha':alpha,'rotation':rotation,'visible':visible,'grayed':grayed,'color':'#ffffffff'}
  if b.seek(start,5):
   if typ==0:
    if b.boolean():row['color']='#'+''.join(f'{b.byte():02x}'for _ in range(4))
   elif typ==4:
    row['url']=b.s();b.p+=7;b.int()
    if b.boolean():row['color']='#'+''.join(f'{b.byte():02x}'for _ in range(4))
  if b.seek(start,2):
   gears=[]
   for _ in range(b.short()):
    glen=b.ushort();gend=b.p+glen;gtype=b.byte();controller=b.short();cnt=b.short();g={'type':gtype,'controllerIndex':controller}
    if gtype in [0,8]:g['pages']=[b.s()for _ in range(cnt)]
    elif gtype in [4,7]:
     statuses={}
     for _ in range(cnt):
      page=b.s()
      if page is None:continue
      statuses[page]=['#'+''.join(f'{b.byte():02x}'for _ in range(4))for _ in range(2)]if gtype==4 else b.s()
     if b.boolean():g['default']=['#'+''.join(f'{b.byte():02x}'for _ in range(4))for _ in range(2)]if gtype==4 else b.s()
     g['statuses']=statuses
    gears.append(g);b.p=gend
   row['gears']=gears
  children.append(row);b.p=end
 return children

def image_from_atlas(pkg,rid):
 item=pkg['items'][rid];sprite=pkg['sprites'][rid];atlas=pkg['items'][sprite['atlas']];filename=atlas['file'];filename=filename if filename.startswith(pkg['name']+'_')else pkg['name']+'_'+filename;atlaspath=pkg['source'].parent/filename
 with Image.open(atlaspath)as im:
  x,y,w,h=sprite['rect'];piece=im.convert('RGBA').crop((x,y,x+w,y+h))
 if sprite['rotated']:piece=piece.transpose(Image.Transpose.ROTATE_270)
 original=Image.new('RGBA',tuple(sprite['originalSize']),(0,0,0,0));original.alpha_composite(piece,tuple(sprite['offset']))
 return original,atlaspath,item,sprite

requested={'Main':['d0a66','syfz1ke471f','j0rg1ke46s5'],'Common':['mwjh1ke479l','mwjh1ke479m','ctd01ke46x1','ctd01ke46x2','ctd01ke46x3','ctd01ke46x4','xoij1ke46lk','xoij1ke46mf']};outdir=OUT/'assets/scene/milestone/reference';outdir.mkdir(parents=True,exist_ok=True);proof=[];variants={}
for pkgname,ids in requested.items():
 for branch in ['default','CN']:
  path=GUI/(pkgname+'_fui.bytes')if branch=='default'else GUI/'__CN'/(pkgname+'_fui.bytes')
  if not path.is_file():continue
  pkg=package(path)
  for rid in ids:
   if rid not in pkg['items']or rid not in pkg['sprites']:continue
   im,atlas,item,sprite=image_from_atlas(pkg,rid);dest=outdir/(pkgname+'_'+rid+'_'+branch+'.png');im.save(dest)
   row={'pkg':pkgname,'id':rid,'name':item['name'],'url':dest.relative_to(OUT).as_posix(),'width':im.width,'height':im.height,'w':im.width,'h':im.height,'scale9grid':item['scale9grid'],'sourceFui':path.relative_to(ROOT).as_posix(),'sourceAtlas':atlas.relative_to(ROOT).as_posix(),'sprite':sprite,'branch':branch,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()};variants.setdefault(pkgname+'/'+rid,{})[branch]=row;proof.append(row)

common=package(GUI/'Common_fui.bytes');native_item=common['items']['nbao1ke46yb'];native_children=component_children(common,'nbao1ke46yb')
component={'package':'Common','id':'nbao1ke46yb','name':'Com_List02','width':native_item['width'],'height':native_item['height'],'children':native_children,'defaultPage':'0','nativeYellowColors':['#fff1afff','#ffc15bff'],'note':'Exact published component parameters. GearColor default/page0 must override serialized initial colors. Images retain native untinted pixels.'}
component_path=outdir/'Common_Com_List02_published.json';component_path.write_text(json.dumps(component,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
main=package(GUI/'Main_fui.bytes');component_id=next(rid for rid,item in main['items'].items()if item['name']=='Comp_MileStoneMainProgress');main_children=component_children(main,component_id)
main_component={'package':'Main','id':component_id,'name':'Comp_MileStoneMainProgress','width':main['items'][component_id]['width'],'height':main['items'][component_id]['height'],'children':main_children}
(outdir/'Main_Comp_MileStoneMainProgress_published.json').write_text(json.dumps(main_component,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
reward_item=main['items']['b4z81ke46tx'];reward_children=component_children(main,'b4z81ke46tx')
reward_component={'package':'Main','id':'b4z81ke46tx','name':'Com_MileStoneReward','width':reward_item['width'],'height':reward_item['height'],'children':reward_children,'note':'Published original brown circles use shared Common.bg_common_round with exact authored node colors; editor source later changed colors and dimensions.'}
reward_path=outdir/'Main_Com_MileStoneReward_published.json';reward_path.write_text(json.dumps(reward_component,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
reference={}
controls={'d0a66':'loader_bgMain','syfz1ke471f':'n173','j0rg1ke46s5':'n157'}
for source,branch in variants.items():
 row=dict(branch['default']);row['atlasRotationRestored']=True;row['rotation']=0
 grid=row['scale9grid'];row['nineSliceInsets']=None if grid is None else {'left':grid[0],'top':grid[1],'right':row['width']-grid[0]-grid[2],'bottom':row['height']-grid[1]-grid[3]}
 if row['pkg']=='Main':
  control=next(c for c in main_children if c['name']==controls[row['id']]);row['controlPath']='Main/Comp_MileStoneMainProgress/'+control['name'];row['layout']={key:control[key]for key in ['xy','size','pivot','anchor','scale','rotation','color']}
 elif row['id']=='xoij1ke46mf':
  control=next(c for c in main_children if c['name']=='n170');row['controlPath']='Main/Comp_MileStoneMainProgress/n170';row['layout']={key:control[key]for key in ['xy','size','pivot','anchor','scale','rotation','color']}
 elif row['id']=='xoij1ke46lk':
  row['controlPaths']=['Main/Comp_MileStoneMainProgress/com_mileReward/'+name for name in ['n146','n147']];row['layouts']={c['name']:{key:c[key]for key in ['xy','size','pivot','anchor','scale','rotation','color']}for c in reward_children if c['name']in['n146','n147']};row['nativeComponentURL']=reward_path.relative_to(OUT).as_posix()
 else:row['controlPath']='Common/Com_List02';row['nativeComponentURL']=component_path.relative_to(OUT).as_posix()
 reference[row['name']]=row
ui_path=OUT/'assets/scene/milestone/ui.json'
if ui_path.is_file():
 ui=json.loads(ui_path.read_text(encoding='utf8'));ui['referenceSkinImages']=reference;ui['referenceSkinComponents']={'Common/Com_List02':{'url':component_path.relative_to(OUT).as_posix(),'width':component['width'],'height':component['height'],'page':'0'},'Main/Comp_MileStoneMainProgress':{'url':(outdir/'Main_Comp_MileStoneMainProgress_published.json').relative_to(OUT).as_posix()}};ui['referenceSkinComponents']['Main/Com_MileStoneReward']={'url':reward_path.relative_to(OUT).as_posix(),'width':reward_component['width'],'height':reward_component['height'],'parentLayout':next(c for c in main_children if c['name']=='com_mileReward')};ui_path.write_text(json.dumps(ui,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
proof={'decoderEvidence':['client/SHIN/Assets/External/GameFramework/3rd/FairyGUI/Scripts/UI/UIPackage.cs:749-1009','client/SHIN/Assets/External/GameFramework/3rd/FairyGUI/Scripts/Core/NTexture.cs:349-376'],'variants':variants,'referenceSkinImages':reference,'missingNewEditorIds':['Common/mwjh1ke479l','Common/mwjh1ke479m'],'note':'Exact original published atlas pixels, with authored rotation/trim restored. No recoloring or generated art. Common published component uses older image resources and authored GearColor defaults.'}
(OUT/'assets-reference-skin-source.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({'exportedImages':len(proof['referenceSkinImages']),'nativeCommonSize':[component['width'],component['height']],'mainComponent':component_id,'branchPixelsEqual':{key:value['default']['sha256']==value['CN']['sha256']for key,value in variants.items()if 'default'in value and'CN'in value},'controls':{key:value.get('layout')for key,value in reference.items()if value['pkg']=='Main'}},ensure_ascii=False))
