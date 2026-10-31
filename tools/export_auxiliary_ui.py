#!/usr/bin/env python3
"""Incrementally export only original Friend and PictureAlbum window dependency trees."""
from pathlib import Path
import ast,json,re,hashlib,shutil,xml.etree.ElementTree as ET
from PIL import Image
helper=Path(__file__).with_name('export_event_ui.py').read_text(encoding='utf8').split('# Runtime-created attack selector')[0]
exec(compile(helper,'original dependency helpers','exec'))
# Existing logical packages take precedence over source folders sharing a package ID.
for pname,pid in original['byName'].items():
 folder=FGUI/pname;path=folder/'package.xml'
 if not path.is_file():continue
 xml=ET.parse(path).getroot()
 if xml.get('id')!=pid:continue
 index[pid]={'name':pname,'folder':folder,'items':{e.get('id'):{'kind':e.tag,'attrs':dict(e.attrib)}for e in xml.find('resources')if e.get('id')and e.tag!='folder'}}
for pname in ['Friend','PictureAlbum']:
 folder=FGUI/pname;xml=ET.parse(folder/'package.xml').getroot();pid=xml.get('id');names[pname]=pid;index[pid]={'name':pname,'folder':folder,'items':{e.get('id'):{'kind':e.tag,'attrs':dict(e.attrib)}for e in xml.find('resources')if e.get('id')and e.tag!='folder'}}
pids=sorted(index,key=len,reverse=True)
# Reuse the exact read-only attribute normalizer already used by prior increments.
for filename,fnames in [('export_assets.py',{'dedupe_attributes'}),('export_milestone_ui.py',{'quote_tag_attributes','parse_xml'})]:
 module=ast.parse(Path(__file__).with_name(filename).read_text(encoding='utf8'));exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef)and n.name in fnames],type_ignores=[]),filename,'exec'))
xml_warnings=[];seen=set();roots_added={};source_differences=[];copied=[];missing_seen=set();dynamic_loaders=[]
original_hashes={item['url']:hashlib.sha256((OUT/item['url']).read_bytes()).hexdigest()for pkg in original['packages'].values()for item in pkg['items'].values()if item.get('url')and(OUT/item['url']).is_file()}

def absent(pid,rid,reason,source=None):
 key=(pid,rid,reason)
 if key not in missing_seen:issues.append({'pkg':pid,'id':rid,'reason':reason,**({'source':source.relative_to(ROOT).as_posix()}if source else {})});missing_seen.add(key)
 return None

def visit_xml(pid,rid,tree):
 def walk(node,path=''):
  attrs=node.get('attrs',{});name=attrs.get('name');path=path+'/'+name if name else path
  src=attrs.get('src')
  if src and node['tag']in['component','image','movieclip','loader3D']:ensure(attrs.get('pkg',pid),src)
  if node['tag']in['loader','loader3D']and not attrs.get('url'):dynamic_loaders.append({'pkg':pid,'id':rid,'path':path.lstrip('/'),'name':name})
  for key,value in attrs.items():
   if key.startswith('designImage'):continue
   for uri in re.findall(r'ui://[A-Za-z0-9_]+',value):
    ref=resolve(uri)
    if ref:ensure(*ref)
    else:absent(pid,rid,'Unresolvable original dynamic/default URI '+uri)
  for child in node.get('children',[]):walk(child,path)
 walk(tree)

def ensure(pid,rid):
 existing=data['packages'].get(pid,{}).get('items',{}).get(rid)
 if (pid,rid)in seen:return existing
 seen.add((pid,rid))
 entry=index.get(pid,{}).get('items',{}).get(rid)
 if existing is not None:
  # Existing trees/bitmap structs and every existing file remain byte-for-byte unchanged.
  if existing.get('xml'):visit_xml(pid,rid,existing['xml'])
  if entry and existing.get('url'):
   source=sourcepath(pid,entry['attrs']);target=OUT/existing['url']
   if source.is_file()and target.is_file()and source.read_bytes()!=target.read_bytes():source_differences.append({'pkg':pid,'id':rid,'url':existing['url'],'reason':'Existing original export differs from current source; preserved existing bytes as requested.'})
  return existing
 if not entry:return absent(pid,rid,'Original referenced resource ID absent from package.xml')
 pkg=index[pid];attrs=entry['attrs'];source=sourcepath(pid,attrs)
 if 'Draw'in source.parts:return absent(pid,rid,'Original reference points to design draft; not exported',source)
 if not source.is_file():return absent(pid,rid,'Original referenced source file missing',source)
 if entry['kind']=='component':
  xml=parse_xml(source);item={'kind':'component','name':attrs.get('name',''),'width':float(xml.get('size','0,0').split(',')[0]),'height':float(xml.get('size','0,0').split(',')[1]),'xml':nodejson(xml)}
 else:
  target=OUT/'assets/ui'/pkg['name']/(rid+source.suffix.lower());target.parent.mkdir(parents=True,exist_ok=True)
  if target.is_file():assert target.read_bytes()==source.read_bytes(),('Refuse replacing existing orphan file',str(target))
  else:shutil.copy2(source,target);copied.append(target.relative_to(OUT).as_posix())
  item={'kind':entry['kind'],'name':attrs.get('name',''),'width':0,'height':0,'url':target.relative_to(OUT).as_posix()}
  for k in ['scale','gridTile']:
   if k in attrs:item[k]=attrs[k]
  if attrs.get('scale9grid'):item['scale9grid']=[int(v)for v in attrs['scale9grid'].split(',')]
  if entry['kind']=='image':
   with Image.open(target)as im:item['width'],item['height']=im.size
 data['byName'].setdefault(pkg['name'],pid);data['packages'].setdefault(pid,{'name':pkg['name'],'items':{}})['items'][rid]=item;added.append({'pkg':pid,'id':rid,'name':item['name']})
 if item.get('xml'):visit_xml(pid,rid,item['xml'])
 if entry['kind']=='font'and source.suffix.lower()=='.fnt':bitmap(pid,rid,item,source)
 return item
for pname,filename in [('Friend','FriendMainWindow.xml'),('PictureAlbum','PictureAlbumMainWindow.xml')]:
 pid=names[pname];rid=next(r for r,e in index[pid]['items'].items()if e['attrs'].get('name')==filename);item=ensure(pid,rid);assert item and item.get('xml'),filename;ref={'pkg':pid,'id':rid};key=filename.removesuffix('.xml')
 if key in data['roots']:assert data['roots'][key]==ref,('Existing root differs',key)
 else:data['roots'][key]=ref
 roots_added[key]=ref
for pid,pkg in original['packages'].items():
 assert data['packages'][pid]['name']==pkg['name']
 for rid,item in pkg['items'].items():assert data['packages'][pid]['items'][rid]==item,('Existing resource changed',pid,rid)
for pname,pid in original['byName'].items():assert data['byName'][pname]==pid
for key,ref in original['roots'].items():assert data['roots'][key]==ref
for url,digest in original_hashes.items():assert hashlib.sha256((OUT/url).read_bytes()).hexdigest()==digest,('Existing file changed',url)
# Identify exact referring nodes for every unresolved original resource.
for issue in issues:
 target=(issue['pkg'],issue['id']);references=[]
 for ipid,irid in seen:
  item=data['packages'].get(ipid,{}).get('items',{}).get(irid)
  if not item or not item.get('xml'):continue
  def scan(node,path=''):
   attrs=node.get('attrs',{});path=path+'/'+attrs['name']if attrs.get('name')else path
   matches=attrs.get('src')==target[1]and attrs.get('pkg',ipid)==target[0]
   matching_attributes=[key for key,value in attrs.items()if not key.startswith('designImage')and 'ui://'+target[0]+target[1]in value]
   if matches or matching_attributes:references.append({'component':item['name'],'pkg':ipid,'id':irid,'path':path.lstrip('/'),'attributes':matching_attributes})
   for child in node.get('children',[]):scan(child,path)
  scan(item['xml'])
 issue['references']=references
DATAFILE.write_text('window.FGUI_DATA = '+json.dumps(data,ensure_ascii=False,separators=(',',':'),allow_nan=False)+';\n',encoding='utf8')
print(json.dumps({'roots':roots_added,'addedResources':len(added),'copiedFiles':len(copied),'preservedResources':sum(len(p['items'])for p in original['packages'].values()),'preservedFiles':len(original_hashes),'sourceDifferencesPreserved':source_differences,'xmlNormalizations':sorted(set(xml_warnings)),'issues':issues,'dynamicLoaders':dynamic_loaders},ensure_ascii=False))