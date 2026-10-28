#!/usr/bin/env python3
"""Export only original assets used by the Shin H5 board. Does not modify source assets."""
from pathlib import Path
import xml.etree.ElementTree as ET
import json,re,shutil,hashlib,struct,math
from collections import deque
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parents[1]
FGUI=ROOT/'fgui/assets'
CN=ROOT/'fgui/assets_CN'
ASSETS=OUT/'assets'
UNITY=ROOT/'client/SHIN/Assets'


def node_json(e):
    return {'tag':e.tag,'attrs':dict(e.attrib),'children':[node_json(c) for c in e]}


def dedupe_attributes(match):
    tag=match.group(0)
    seen=set()
    def retain(attribute):
        key=attribute.group(1)
        if key in seen:return ''
        seen.add(key);return attribute.group(0)
    return re.sub(r'\s+([\w:-]+)="[^"]*"',retain,tag)


def export_meshes(scene,record):
    meshes={};issues=[]
    formats={0:(4,'f'),1:(2,'e'),2:(1,'B'),3:(1,'b'),4:(2,'H'),5:(2,'h'),6:(1,'B'),7:(1,'b'),8:(2,'H'),9:(2,'h'),10:(4,'I'),11:(4,'i')}
    folder=UNITY/'Art/City/Chessboard/Grid/Models'
    paths=sorted([*folder.glob('checkerboard*.asset'),*folder.glob('checkerboard*.mesh')])
    for path in paths:
        try:
            text=path.read_text(encoding='utf-8-sig')
            if 'm_VertexData:' not in text:continue
            name=re.search(r'^  m_Name: (.+)$',text,re.M).group(1).strip()
            count=int(re.search(r'm_VertexCount: (\d+)',text).group(1))
            channel_text=text.split('    m_Channels:',1)[1].split('    m_DataSize:',1)[0]
            channels=[tuple(map(int,m)) for m in re.findall(r'- stream: (\d+)\s+offset: (\d+)\s+format: (\d+)\s+dimension: (\d+)',channel_text)]
            if len(channels)<5 or channels[0][3]!=3 or channels[4][3]!=2:raise ValueError('missing position/UV0 channels')
            raw=bytes.fromhex(re.search(r'_typeless[Dd]ata:\s*([a-fA-F0-9]+)',text).group(1))
            strides={}
            for stream,offset,fmt,dimension in channels:
                if dimension:strides[stream]=max(strides.get(stream,0),offset+formats[fmt][0]*dimension)
            bases={};base=0
            for stream in sorted(strides):
                bases[stream]=base;base=(base+strides[stream]*count+15)//16*16
            def channel_values(channel):
                stream,offset,fmt,dimension=channel
                size,typ=formats[fmt];values=[]
                for i in range(count):
                    decoded=struct.unpack_from('<'+typ*dimension,raw,bases[stream]+i*strides[stream]+offset)
                    for value in decoded:
                        if fmt==2:value/=255
                        elif fmt==3:value=max(-1,value/127)
                        elif fmt==4:value/=65535
                        elif fmt==5:value=max(-1,value/32767)
                        if not math.isfinite(value):raise ValueError('non-finite vertex')
                        values.append(round(value,8))
                return values
            positions=channel_values(channels[0]);uv=channel_values(channels[4])
            index_raw=bytes.fromhex(re.search(r'^  m_IndexBuffer: ([a-fA-F0-9]+)',text,re.M).group(1))
            index_format=int(re.search(r'm_IndexFormat: (\d+)',text).group(1));size,fmt=(2,'H') if index_format==0 else (4,'I')
            indices=list(struct.unpack('<'+fmt*(len(index_raw)//size),index_raw))
            if len(indices)%3 or any(i>=count for i in indices):raise ValueError('invalid triangle indices')
            if name in meshes:issues.append({'file':path.name,'reason':'duplicate mesh name; retained first export'});continue
            meshes[name]={'positions':positions,'uv':uv,'indices':indices,'vertexCount':count,'stride':strides.get(0),'source':str(path.relative_to(ROOT)).replace('\\','/')}
        except Exception as error:issues.append({'file':path.name,'reason':str(error)})
    output=scene/'grid-meshes.json';output.write_text(json.dumps(meshes,separators=(',',':'))+'\n',encoding='utf-8')
    for mesh in meshes.values():record(ROOT/mesh['source'],output)
    return {'url':'assets/scene/grid-meshes.json','meshes':len(meshes),'issues':issues}


def main():
    index={};by_name={}
    for folder in sorted(FGUI.iterdir()):
        package=folder/'package.xml'
        if not package.is_file():continue
        tree=ET.parse(package).getroot();pid=tree.get('id')
        if not pid:continue
        resources={}
        for el in list(tree.find('resources')):
            rid=el.get('id')
            if not rid or el.tag=='folder':continue
            resources[rid]={'kind':el.tag,'attrs':dict(el.attrib)}
        index[pid]={'name':folder.name,'folder':folder,'items':resources}
        by_name[folder.name]=pid
    wanted={
      'Main':['MainWindow.xml','BoardReportWindow.xml'],
      'Common':['bg_com_window01.xml','Com_FirstPopUp.xml','Com_SecondPopUp.xml','Com_ThirdPopUp.xml','CommonDescWindow.xml'],
      'ChessboardEvent':['ChanceWindow.xml','FriendRentWindow.xml','PrisonWindow.xml','SheildWindow.xml','PrisonCageWindow.xml'],
      'Build':['BuildWindow.xml','BuildCompletedWindow.xml','MapChooseWindow.xml','MapUpgradeWindow.xml','Com_BuildBottom.xml'],
      'BlindBox':['BlindBoxWindow.xml','BlindBoxRewardWindow.xml','BlindBoxRuleWindow.xml'],
      'MakeTrouble':['DestroyBuildingWindow.xml','ChooseOpponentWindow.xml','BadFriendLoadingWindow.xml'],
      'Fund':['FundMainWindow.xml','FundSocialWindow.xml','FundPublicWelfareWindow.xml','FundCongratulationsWindow.xml'],
      'GachaMachine':['GachaMachineWindow.xml','GachaMachineProbability.xml'],
      'Player':['PlayerInfoWindow.xml'],
    }
    roots={};queue=deque();missing=[];warnings=[];manifest=[];packages={}
    for pname,names in wanted.items():
        pid=by_name[pname]
        for rid,entry in index[pid]['items'].items():
            if entry['attrs'].get('name') in names:
                key=entry['attrs']['name'].removesuffix('.xml')
                roots[key]={'pkg':pid,'id':rid};queue.append((pid,rid))
    dynamic_names={
      'IconItem':{'icon_money.png','icon_dice.png','icon_dice_02.png','icon_GachaCoin.png','icon_EXGachaCoin.png','icon_kb.png','icon_prison.png'},
      'Common':{'img_common_avatar_player.png','icon_dice_02.png','icon_shield07.png'},
      'ChessboardEvent':{'img_card_03.png','img_card_04.png','img_card_06.png','img_card_10.png','img_card_11.png','img_character_01.png','img_character_02.png','img_event_shinchan_01.png','img_event_shinchan_02.png','img_event_shinchan_03.png'},
    }
    for pname,names in dynamic_names.items():
        pid=by_name[pname]
        for rid,entry in index[pid]['items'].items():
            if entry['attrs'].get('name') in names:queue.append((pid,rid))
    # Original board tile icons are exported separately when available, not guessed.
    ids=sorted(index,key=len,reverse=True)
    def from_url(url):
        for pid in ids:
            if url.startswith(pid):return pid,url[len(pid):]
        return None
    def original_path(pid,attrs):
        rel=Path(attrs.get('path','/').lstrip('/'))/attrs.get('name','')
        # Preserve the original Shin branch; CN contains replacement artwork.
        return index[pid]['folder']/rel
    def record(source,dest):
        manifest.append({'source':str(source.relative_to(ROOT)).replace('\\','/'),'output':str(dest.relative_to(OUT)).replace('\\','/'),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
    seen=set()
    while queue:
        pid,rid=queue.popleft()
        if (pid,rid) in seen:continue
        seen.add((pid,rid))
        if pid not in index or rid not in index[pid]['items']:
            missing.append({'pkg':pid,'id':rid,'reason':'resource ID absent'});continue
        pkg=index[pid];res=pkg['items'][rid];a=res['attrs'];source=original_path(pid,a)
        item={'kind':res['kind'],'name':a.get('name',''),'width':0,'height':0}
        if a.get('scale9grid'):item['scale9grid']=[int(v) for v in a['scale9grid'].split(',')]
        if a.get('scale'):item['scale']=a['scale']
        if a.get('gridTile'):item['gridTile']=a['gridTile']
        packages.setdefault(pid,{'name':pkg['name'],'items':{}})['items'][rid]=item
        if not source.is_file():
            missing.append({'pkg':pid,'id':rid,'path':str(source.relative_to(ROOT)).replace('\\','/'),'reason':'source file absent'});continue
        if res['kind']=='component':
            try:
                raw=source.read_text(encoding='utf-8-sig')
                cleaned=re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]','',raw)
                cleaned=re.sub(r'(\s[\w:-]+)=([^\s\"\'<>`=]+)(?=\s|/?>)',lambda m:m.group(1)+'="'+m.group(2)+'"',cleaned)
                cleaned=re.sub(r'<(?![!?/])[^<>]+>',dedupe_attributes,cleaned)
                xml=ET.fromstring(cleaned)
                if cleaned!=raw:warnings.append({'pkg':pid,'id':rid,'warning':'Read-only XML normalization: quoted original numeric attributes / removed forbidden control characters.'})
            except ET.ParseError as e:
                missing.append({'pkg':pid,'id':rid,'reason':str(e)});continue
            item['xml']=node_json(xml)
            size=xml.get('size','0,0').split(',');item['width'],item['height']=map(float,size[:2])
            for child in xml.iter():
                src=child.get('src')
                child_pkg=child.get('pkg',pid)
                if src and child.tag in ['component','image','movieclip','loader3D']:queue.append((child_pkg,src))
                for key,value in child.attrib.items():
                    if key.startswith('designImage'):continue
                    for url in re.findall(r'ui://([A-Za-z0-9_]+)',value):
                        target=from_url(url)
                        if target:queue.append(target)
            continue
        dest_dir=ASSETS/'ui'/pkg['name'];dest_dir.mkdir(parents=True,exist_ok=True)
        ext=source.suffix.lower() or '.bin';dest=dest_dir/(rid+ext)
        shutil.copy2(source,dest);item['url']=str(dest.relative_to(OUT)).replace('\\','/');record(source,dest)
        if res['kind']=='image':
            try:
                with Image.open(source) as im:item['width'],item['height']=im.size
            except Exception as e:warnings.append({'pkg':pid,'id':rid,'warning':'image dimensions: '+str(e)})
        elif res['kind']=='movieclip':
            warnings.append({'pkg':pid,'id':rid,'warning':'Original FairyGUI movieclip retained; H5 renderer must support it or use static first frame.'})
        elif res['kind']=='font':
            # FGUI bitmap font pages may be beside the fnt data.
            for page in source.parent.glob(source.stem+'*.png'):
                target=dest_dir/page.name;shutil.copy2(page,target);record(page,target)
    scene=ASSETS/'scene';scene.mkdir(parents=True,exist_ok=True)
    scene_data={'maps':{}}
    for map_id in [1,2]:
        parts=[]
        for n in range(1,5):
            src=UNITY/'ResourcesAssets/TextureRule/CityBg'/f'bg_main_{map_id}_{n}.png'
            if not src.is_file():missing.append({'path':str(src.relative_to(ROOT)),'reason':'map tile missing'});continue
            with Image.open(src) as im:
                dest=scene/f'bg_main_{map_id}_{n}.webp';im.save(dest,'WEBP',quality=92,method=4)
                parts.append({'url':str(dest.relative_to(OUT)).replace('\\','/'),'width':im.width,'height':im.height,'part':n})
            record(src,dest)
        scene_data['maps'][str(map_id)]=parts
        # Preview both common 2x2 layouts; exact mesh ordering is in the original Unity prefab.
        if len(parts)==4:
            ims=[Image.open(OUT/x['url']).convert('RGB') for x in parts]
            canv=Image.new('RGB',(1288,2048),'white');draw=ImageDraw.Draw(canv)
            for n,im in enumerate(ims):
                im.thumbnail((644,1024));x=(n%2)*644;y=(n//2)*1024;canv.paste(im,(x,y));draw.text((x+12,y+12),f'PART {n+1}',fill='red',stroke_width=1,stroke_fill='white')
            preview=scene/f'map_{map_id}_parts_preview.jpg';canv.save(preview,quality=85)
            full=Image.new('RGB',(ims[0].width+ims[1].width,ims[0].height+ims[2].height),'white')
            for n,im in enumerate(ims):full.paste(im,((0 if n%2==0 else ims[0].width),(0 if n<2 else ims[0].height)))
            full_url=scene/f'bg_main_{map_id}_full.webp';full.save(full_url,'WEBP',quality=92,method=4)
            scene_data['map'+str(map_id)+'Full']={'url':str(full_url.relative_to(OUT)).replace('\\','/'),'width':full.width,'height':full.height,'partsOrder':[[1,2],[3,4]]}
            for n in range(1,5):record(UNITY/'ResourcesAssets/TextureRule/CityBg'/f'bg_main_{map_id}_{n}.png',full_url)
            for im in ims:im.close()
    for map_id in [1,2]:
        src=UNITY/'ResourcesAssets/Texture/Block10x10/BuildingBg'/f'bg_build_{map_id}.png'
        if src.is_file():
            with Image.open(src) as im:
                dest=scene/f'bg_build_{map_id}.webp';im.save(dest,'WEBP',quality=92,method=4)
                scene_data[f'build{map_id}']={'url':str(dest.relative_to(OUT)).replace('\\','/'),'width':im.width,'height':im.height}
            record(src,dest)
    src=UNITY/'Art/City/Chessboard/Grid/Textures/SquareTex.png'
    dest=scene/'SquareTex.png';shutil.copy2(src,dest);record(src,dest)
    scene_data['tileAtlas']='assets/scene/SquareTex.png'
    scene_data['gridMeshes']=export_meshes(scene,record)
    spine_out=ASSETS/'spine/shin';spine_out.mkdir(parents=True,exist_ok=True)
    base=UNITY/'Art/Spine/ChessPiece/role_001'
    for source_name,output_name in [('1_body.skel.bytes','1_body.skel'),('1_body.atlas.txt','1_body.atlas'),('1_body.png','1_body.png')]:
        src=base/source_name;dest=spine_out/output_name;shutil.copy2(src,dest);record(src,dest)
    result={'packages':packages,'byName':by_name,'roots':roots,'scene':scene_data,'missing':missing,'warnings':warnings}
    (OUT/'fgui-data.js').write_text('window.FGUI_DATA = '+json.dumps(result,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')+';\n',encoding='utf-8')
    (OUT/'assets-source.json').write_text(json.dumps({'files':manifest,'missing':missing,'warnings':warnings,'roots':roots,'scene':scene_data},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    total=sum(x.stat().st_size for x in ASSETS.rglob('*') if x.is_file())
    print(json.dumps({'packages':len(packages),'resources':len(seen),'files':len(manifest),'roots':len(roots),'missing':len(missing),'warnings':len(warnings),'assetMB':round(total/1024/1024,2)},ensure_ascii=False))
    for x in missing[:15]:print('MISSING '+json.dumps(x,ensure_ascii=False))

if __name__=='__main__':main()