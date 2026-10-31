#!/usr/bin/env python3
"""Isolated published main UI namespace. Never changes current FGUI data or existing assets."""
from pathlib import Path
import json,re,ast,copy,hashlib,xml.etree.ElementTree as ET
from PIL import Image
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'shin-h5';DEST=OUT/'assets/ui/reference-main';DEST.mkdir(parents=True,exist_ok=True)
helper=Path(__file__).with_name('export_reference_skin_ui.py');scope={'__file__':str(helper)};exec(helper.read_text(encoding='utf8').split('requested=')[0],scope);package=scope['package'];childrows=scope['component_children'];extract=scope['image_from_atlas'];GUI=scope['GUI']
raw=(OUT/'fgui-data.js').read_text(encoding='utf8');existing=json.loads(raw[raw.index('{'):raw.rfind('}')+1]);source_folders={};names={};registry={};issues=[];normalizations=[];xml_warnings=[]
for base in [ROOT/'fgui/assets',ROOT/'peibiao/fairygui/trunk/assets']:
 for folder in base.iterdir():
  path=folder/'package.xml'
  if not path.is_file():continue
  p=ET.parse(path).getroot();pid=p.get('id');names[folder.name]=pid
  if pid:registry[(folder.name,pid)]={e.get('id'):dict(e.attrib)for e in p.find('resources')if e.get('id')};source_folders[(folder.name,pid)]=folder
for filename,fnames in [('export_assets.py',{'dedupe_attributes'}),('export_milestone_ui.py',{'quote_tag_attributes','parse_xml'})]:
 mod=ast.parse((OUT/'tools'/filename).read_text(encoding='utf8'));exec(compile(ast.Module(body=[n for n in mod.body if isinstance(n,ast.FunctionDef)and n.name in fnames],type_ignores=[]),filename,'exec'))
PACKAGES=['Main','Common','Main_01','MainSideBar','IconItem'];native={};pname_by_id={};sources={};result={'packages':{},'byName':{},'roots':{},'layouts':{},'issues':issues,'sourcePackages':sources,'externalPackages':{},'notes':['Images are exact published __CN resource pixels when present, falling back per resource to default package. Atlas rotation and trim are restored, no recoloring.','Controllers, page defaults and all native gears are decoded from published binary. Matching original peibiao/fairygui/trunk XML retains relations, transitions and specialized styles; display order and common node transforms/sizes are native binary.','Main/Common/Main_01/MainSideBar plus only referenced IconItem resources are isolated. Other original package references retain their original external PID and use existing data.','No existing fgui-data, assets, event/ranking references or gameplay sources are modified.']}
for pname in PACKAGES:
 variants={}
 for branch,path in [('default',GUI/(pname+'_fui.bytes')),('CN',GUI/'__CN'/(pname+'_fui.bytes'))]:
  if path.is_file():
   p=package(path);variants[branch]=p;sources.setdefault(pname,{})[branch]={'source':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'packageId':p['id']}
 assert variants,pname
 native[pname]=variants;pid=next(iter(variants.values()))['id'];pname_by_id[pid]=pname;result['byName'][pname]=pid;result['packages'][pid]={'name':pname,'items':{}}

def choose(pname,rid):
 for branch in ['CN','default']:
  p=native[pname].get(branch)
  if p and rid in p['items']:return branch,p,p['items'][rid]
 return None,None,None

def node(e):return {'tag':e.tag,'attrs':dict(e.attrib),'children':[node(c)for c in e]}
def xml_source(pname,pid,rid):
 attrs=registry.get((pname,pid),{}).get(rid)
 if attrs:
  path=source_folders[(pname,pid)]/attrs.get('path','/').lstrip('/')/attrs['name']
  if path.is_file():return node(parse_xml(path)),path.relative_to(ROOT).as_posix()
 old=existing['packages'].get(pid,{}).get('items',{}).get(rid)
 if old and old.get('xml'):return copy.deepcopy(old['xml']),'existing H5 tree fallback; native common layout overrides'
 return None,None

def fmt(values):return ','.join(str(round(float(x),7)).rstrip('0').rstrip('.')if float(x)!=int(float(x))else str(int(float(x)))for x in values)
def rgba(c):return '#'+c[7:9]+c[1:7]if len(c)==9 else c

def native_controls(pkg,rid,xml):
 b=scope['Buffer'](pkg['items'][rid]['rawData']);b.strings=pkg['strings'];out=[];old={c['attrs'].get('name'):c for c in xml['children']if c['tag']=='controller'}
 if not b.seek(0,1):return out
 for _ in range(b.short()):
  length=b.short();start=b.p;end=start+length;b.seek(start,0);name=b.s();radio=b.boolean();b.seek(start,1);pages=[(b.s(),b.s())for _ in range(b.short())];home_type=b.byte();home=b.short()if home_type==1 else 0
  if home_type==3:b.s()
  c=copy.deepcopy(old.get(name,{'tag':'controller','attrs':{},'children':[]}));c['attrs'].update({'name':name,'pages':','.join(str(v or'')for pair in pages for v in pair),'selected':str(home),'autoRadioGroupDepth':'true'if radio else'false'});out.append(c);b.p=end
 return out

def native_gears(pkg,rid,controls):
 b=scope['Buffer'](pkg['items'][rid]['rawData']);b.strings=pkg['strings'];result={};gear_names=['gearDisplay','gearXY','gearSize','gearLook','gearColor','gearAnimation','gearText','gearIcon','gearDisplay2','gearFontSize']
 if not b.seek(0,2):return result
 def col():
  r,g,blue,a=[b.byte()for _ in range(4)];return '#'+''.join(f'{v:02x}'for v in[a,r,g,blue])
 def value(typ):
  if typ==1:return fmt([b.int(),b.int()])
  if typ==2:return fmt([b.int(),b.int(),b.read('f'),b.read('f')])
  if typ==3:return fmt([b.read('f'),b.read('f'),int(b.boolean()),int(b.boolean())])
  if typ==4:return col()+','+col()
  if typ==5:return ('true'if b.boolean()else'false')+','+str(b.int())
  if typ in[6,7]:return b.s()or''
  if typ==9:return str(b.int())
  raise ValueError(('Unknown gear type',typ))
 for _ in range(b.short()):
  length=b.short();start=b.p;end=start+length;b.seek(start,0);b.byte();b.s();b.s();ident=b.s();gears=[]
  if b.seek(start,2):
   for _ in range(b.short()):
    glen=b.ushort();gend=b.p+glen;typ=b.byte();ci=b.short();cnt=b.short();attrs={'controller':controls[ci]['attrs']['name']if 0<=ci<len(controls)else str(ci)};pages=[];values=[]
    if typ in[0,8]:pages=[b.s()for _ in range(cnt)]
    else:
     for _ in range(cnt):
      page=b.s()
      if page is None:continue
      pages.append(page);values.append(value(typ))
     if b.boolean():attrs['default']=value(typ)
    attrs['pages']=','.join(p or''for p in pages)
    if values:attrs['values']='|'.join(values)
    if b.p<gend and b.boolean():attrs['tween']='true';attrs['ease']=str(b.byte());attrs['duration']=str(b.read('f'));attrs['delay']=str(b.read('f'))
    if typ==8 and b.p<gend:attrs['condition']=str(b.byte())
    if typ==1 and b.p<gend and b.boolean():
     attrs['positionsInPercent']='true';percent={}
     for _ in range(cnt):
      page=b.s()
      if page is not None:percent[page]=fmt([b.read('f'),b.read('f')])
     default_percent=fmt([b.read('f'),b.read('f')])if b.boolean()else None
     if values:attrs['values']='|'.join(v+','+percent[page]if page in percent else v for page,v in zip(pages,values))
     if default_percent and'default'in attrs:attrs['default']+=','+default_percent
    gears.append({'tag':gear_names[typ],'attrs':attrs,'children':[]});b.p=gend
  result[ident]=gears;b.p=end
 return result
seen=set();image_checks=[];source_stats={};pending=[]

def ensure(pid,rid):
 if pid not in pname_by_id:result['externalPackages'][pid]=existing['packages'].get(pid,{}).get('name','unresolved external');return
 pname=pname_by_id[pid];out=result['packages'][pid]['items']
 if (pid,rid)in seen:return
 seen.add((pid,rid));branch,p,item=choose(pname,rid)
 if not item:
  old=existing['packages'].get(pid,{}).get('items',{}).get(rid)
  if old:out[rid]=copy.deepcopy(old);out[rid]['referenceFallback']=True;issues.append({'pkg':pname,'id':rid,'reason':'Absent from published package; existing resource retained as external URL/tree fallback'})
  else:issues.append({'pkg':pname,'id':rid,'reason':'Referenced original resource absent from published and existing data'})
  return
 if item['kind']==0:
  if rid not in p['sprites']:issues.append({'pkg':pname,'id':rid,'reason':'Published image has no sprite entry'});return
  im,atlas,_,sprite=extract(p,rid);path=DEST/pname/(rid+'.png');path.parent.mkdir(parents=True,exist_ok=True);im.save(path);n=item['name']+'.png';source_stats[branch]=source_stats.get(branch,0)+1
  out[rid]={'kind':'image','name':n,'width':im.width,'height':im.height,'url':path.relative_to(OUT).as_posix(),'source':{'branch':branch,'fui':p['source'].relative_to(ROOT).as_posix(),'atlas':atlas.relative_to(ROOT).as_posix(),'sprite':sprite,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}}
  if item.get('scale9grid'):out[rid]['scale9grid']=item['scale9grid'];out[rid]['scale']='9grid'
  if item.get('gridTile'):out[rid]['gridTile']=item['gridTile']
  assert im.size==tuple(sprite['originalSize']);image_checks.append((pname,rid,branch,im.size));return
 if item['kind']!=3:
  old=existing['packages'].get(pid,{}).get('items',{}).get(rid)
  if old:out[rid]=copy.deepcopy(old)
  else:issues.append({'pkg':pname,'id':rid,'kind':item['kind'],'reason':'Non-image/component runtime resource not decoded; retain existing if available'})
  return
 xml,source=xml_source(pname,pid,rid)
 if xml is None:xml={'tag':'component','attrs':{},'children':[]};issues.append({'pkg':pname,'id':rid,'reason':'No original XML; native common node layout emitted without specialized properties'})
 xml['attrs']['size']=str(item['width'])+','+str(item['height']);dl=next((c for c in xml['children']if c['tag']=='displayList'),None)
 if dl is None:dl={'tag':'displayList','attrs':{},'children':[]};xml['children'].append(dl)
 controllers=native_controls(p,rid,xml);xml['children']=[c for c in xml['children']if c['tag']!='controller'];xml['children'][0:0]=controllers;decoded_gears=native_gears(p,rid,controllers)
 oldnodes={c['attrs'].get('id'):c for c in dl['children']};rows=childrows(p,rid);newnodes=[];tags={0:'image',1:'movieclip',3:'graph',4:'loader',5:'group',6:'text',7:'richtext',8:'inputtext',9:'component',10:'list',17:'tree',18:'loader3D'}
 for row in rows:
  n=copy.deepcopy(oldnodes.get(row['id'],{'tag':tags.get(row['type'],'component'),'attrs':{},'children':[]}));a=n['attrs'];a.update({'id':row['id'],'name':row['name'],'xy':fmt(row['xy']),'scale':fmt(row['scale']),'pivot':fmt(row['pivot']),'anchor':'true'if row['anchor']else'false','rotation':str(row['rotation']),'alpha':str(row['alpha']),'visible':'true'if row['visible']else'false','grayed':'true'if row['grayed']else'false'})
  if row['size']is None:a.pop('size',None)
  else:a['size']=fmt(row['size'])
  if row['src']:a['src']=row['src']
  if row['pkg']:a['pkg']=row['pkg']
  else:a.pop('pkg',None)
  if row['type']in[0,4]:a['color']=rgba(row['color'])
  if row['type']==4:
   if row.get('url'):a['url']=row['url']
   else:a.pop('url',None)
  n['children']=[c for c in n['children']if not c['tag'].startswith('gear')]+decoded_gears.get(row['id'],[]);newnodes.append(n)
 dl['children']=newnodes
 validids={n['attrs']['id']for n in newnodes}
 for trans in [c for c in xml['children']if c['tag']=='transition']:
  invalid=[c for c in trans['children']if c['attrs'].get('target')and c['attrs']['target']not in validids]
  if invalid:issues.append({'pkg':pname,'id':rid,'transition':trans['attrs'].get('name'),'reason':'Original XML transition target absent in published children; omitted only invalid items'});trans['children']=[c for c in trans['children']if c not in invalid]
 out[rid]={'kind':'component','name':item['name']+'.xml','width':item['width'],'height':item['height'],'xml':xml,'source':{'branch':branch,'fui':p['source'].relative_to(ROOT).as_posix(),'xml':source}}
 result['layouts'][pname+'/'+item['name']]={'pkg':pid,'id':rid,'width':item['width'],'height':item['height'],'children':rows,'sourceXml':source}
 # Recurse only original component dependencies, not gameplay windows referenced by side-menu business code.
 def walk(n):
  a=n['attrs'];src=a.get('src')
  if src and n['tag']in['image','component','movieclip','loader3D']:ensure(a.get('pkg',pid),src)
  for key,value in a.items():
   if key.startswith('designImage'):continue
   for uri in re.findall(r'ui://[A-Za-z0-9_]+',value):
    if len(uri)>13:ensure(uri[5:13],uri[13:])
  for c in n['children']:walk(c)
 walk(xml)
for pname in ['Main','Common','Main_01']:
 pid=result['byName'][pname]
 for rid,old in existing['packages'].get(pid,{}).get('items',{}).items():
  if old.get('kind')=='image':ensure(pid,rid)
for pname,cname in [('Main','MainWindow'),('Common','Top_Bar'),('Main','Main_Big_Button'),('MainSideBar','MainSideBarWindow')]:
 pid=result['byName'][pname];rid=next((rid for p in native[pname].values()for rid,i in p['items'].items()if i['kind']==3 and i['name']==cname),None);assert rid,(pname,cname);ensure(pid,rid);result['roots'][cname]={'pkg':pid,'id':rid}
commonpid=result['byName']['Common']
for p in native['Common'].values():
 for rid,i in p['items'].items():
  if i['name']in ['img_main_infobarbg_01','img_main_infobarbg_02','bg_main_top02']:ensure(commonpid,rid)
# Exact top-money coin and KB badge, used by published Top_money/Top_Bar Label defaults.
for rid in ['khoq1ke46sb','xoij1ke46n7']:ensure(result['byName']['IconItem'],rid)
# Business-code dynamic imagery: explicit native names, never inferred/generated icons.
for pname,wanted in [('MainSideBar',['icon_main_more_'+n for n in ['02','07','04','03','06','13','12','12_02','14','15','08']]),('Main_01',['bg_main_bottom','bg_main_bottom_02','bg_main_bottom_03'])]:
 pid=result['byName'][pname]
 for stem in wanted:
  rid=next((rid for p in native[pname].values()for rid,i in p['items'].items()if i['kind']==0 and i['name']==stem),None)
  if rid:ensure(pid,rid)
  else:issues.append({'pkg':pname,'name':stem,'reason':'Requested native dynamic image absent from published package'})
result['imageRefs']={}
for pid,pkg in result['packages'].items():
 for rid,i in pkg['items'].items():
  if i['kind']=='image'and i.get('source',{}).get('branch'):result['imageRefs'][pkg['name']+'/'+i['name']]={'pkg':pid,'id':rid}
result['validation']={'binaryDecodedControllersAndGears':True,'restoredImages':len(image_checks),'imageBranches':source_stats,'componentCount':sum(i['kind']=='component'for p in result['packages'].values()for i in p['items'].values()),'xmlReadOnlyNormalizations':sorted(set(xml_warnings)),'atlasRotation':'PIL ROTATE_270 restores FairyGUI rotated sprite UV; trim offset restored into original size canvas.'}
(DEST/'ui.json').write_text(json.dumps({'referenceUI':{'main':result}},ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n',encoding='utf8')
print(json.dumps({'url':'assets/ui/reference-main/ui.json','roots':result['roots'],'validation':result['validation'],'issues':issues,'externalPackages':result['externalPackages']},ensure_ascii=False))