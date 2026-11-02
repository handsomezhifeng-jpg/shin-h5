"""Resolve task/level reward ids through original item tables and ResourcesPath."""
import json
import hashlib
from pathlib import Path

HERE=Path(__file__).resolve().parent
ns={'__file__':str(HERE/'export_mhx_construction_ui.py')}
exec(compile((HERE/'export_mhx_construction_ui.py').read_text(encoding='utf8').split('\nselected = []',1)[0],str(HERE/'export_mhx_construction_ui.py'),'exec'),ns)
OUT=ns['OUT'];CONFIG=OUT/'config';images=OUT/'images-task';images.mkdir(exist_ok=True);ns['IMAGES']=images
def table(p):return json.loads((CONFIG/(p+'.json')).read_text(encoding='utf8'))
paths=['Goods/Currency','MainPlay/MotherPieceVo','MainPlay/PieceVo','MainPlay/FunctionalPieceVo','Data/Common/CommonItemVo']
tables={p:table(p)for p in paths};lookup={}
for p,t in tables.items():
    for row in t['rows']:lookup[str(row['id'])]=(p,row)
quests=table('Data/Common/MainQuestVo')['rows'];levels=table('Common/PlayerExp')['rows'];resources={str(r['id']):r['resourcePath']for r in table('Module/ResourcesPath')['rows']}
needed={'102','104'}
for row in quests+levels:
    for field in ['rewardId','showRewardId']:
        if row[field]!='':needed.update(str(row[field]).split(';'))
base=json.loads((OUT/'ui.json').read_text(encoding='utf8'));items={};missing=[]
for item_id in sorted(needed,key=int):
    entry=lookup.get(item_id)
    if not entry:missing.append(dict(id=item_id,reason='Original item table not included in bounded export'));continue
    source_table,row=entry;photo=str(row.get('photoId',''))
    if ':'not in photo:missing.append(dict(id=item_id,reason='No original photoId',sourceTable=source_table));continue
    resource_id,name=photo.split(':',1);resource=resources[resource_id];asset_path=resource+'/'+name
    record=dict(id=int(item_id),name=row.get('name_zh_CN',row.get('name','')),photoId=photo,resourcePath=resource,assetPath=asset_path,sourceTable='assets/construction/config/'+source_table+'.json',sourceRow=row)
    if resource.lower().startswith('uiatlas/'):
        sprite=base['spritesByName'].get(name)
        if sprite:record['sprite']=sprite
    else:
        bundle_name='assets_bundleresources_'+asset_path.lower().replace('/','_')+'.bytes'
        source=next((s for s,names,_ in reversed(ns['records'])if bundle_name in names),None)
        if source:
            ns['load'](source)
            for f in list(ns['environment'].cabs.values()):
                if not isinstance(f,ns['SerializedFile'])or ns['cabinet_sources'].get(f.name.lower())!=source:continue
                for obj in f.objects.values():
                    if obj.type.name=='Sprite'and obj.peek_name()==name:
                        key=ns['export_sprite'](obj);record['sprite']=ns['sprites'][key]
                        tree=ns['read_tree'](obj);texture=ns['resolve'](tree['m_RD']['texture'],obj.assets_file)
                        if texture:
                            full=texture.read().image;rect=tree['m_Rect']
                            if full.size==(round(rect['width']),round(rect['height'])):
                                filename=record['sprite']['url'].rsplit('/',1)[-1]
                                full.save(images/filename)
                                record['sprite'].update(width=full.width,height=full.height,extraction='Full original standalone texture matching logical Sprite rect; retains transparent padding.',textureRect=tree['m_RD']['textureRect'],textureRectOffset=tree['m_RD']['textureRectOffset'])
            if 'sprite'not in record:
                for f in list(ns['environment'].cabs.values()):
                    if not isinstance(f,ns['SerializedFile'])or ns['cabinet_sources'].get(f.name.lower())!=source:continue
                    for obj in f.objects.values():
                        if obj.type.name=='Texture2D'and obj.peek_name()==name:
                            d=obj.read();key=ns['identity'](obj);filename=name+'-'+hashlib.sha256(key.encode()).hexdigest()[:8]+'.png';im=d.image;im.save(images/filename);record['sprite']=dict(name=name,url='assets/construction/images-task/'+filename,width=im.width,height=im.height,sourceObject=key)
            record['sourceBundle']=source
    if 'sprite'in record:
        record['sprite']['url']=record['sprite']['url'].replace('/images-ui/','/images-task/') if record['sprite']['sourceObject']in ns['sprites']else record['sprite']['url']
        record['icon']=record['sprite']['url'];record['sha256']=hashlib.sha256((ns['ROOT']/record['icon']).read_bytes()).hexdigest()
    else:missing.append(dict(id=item_id,photoId=photo,reason='Original source image absent from bounded cached inventory'))
    items[item_id]=record

def walk(n):
    yield n
    for c in n.get('children',[]):yield from walk(c)
prefab=base['prefabs']['TaskDailog'];nodes=list(walk(prefab));targets={}
for n in nodes:
    targets[n['sourceObject']]=n['path']
    for c in n['components']:targets[c['sourceObject']]=n['path']
bindings={}
for n in nodes:
    for c in n['components']:
        if c.get('script')=='LuaOutlet':
            cab=c['sourceObject'].rsplit(':',1)[0]
            bindings[n['path']]={r['Name']:dict(path=targets.get(cab+':'+str(r['TargetObject']['m_PathID'])),componentType=r['ComponentType'])for r in c['fields'].get('outletInfos',[])}
pack=dict(formatVersion=1,items=items,taskLuaBindings=bindings,sources=ns['loaded_sources'],tables={p:dict(sha256=hashlib.sha256((CONFIG/(p+'.json')).read_bytes()).hexdigest(),tsvSha256=t['tsvSha256'])for p,t in tables.items()},missing=missing,notes=['photoId is resolved through original Module/ResourcesPath, not inferred from item id.','Dynamic standalone goods icons supersede the earlier approximate common-atlas coin binding.','Map and merge-board item definitions are retained as source metadata; no gameplay exchange is invented.'])
(OUT/'task-content.json').write_text(json.dumps(pack,ensure_ascii=False,indent=2),encoding='utf8')
# Merge only the two dynamic currency bindings into the current UI export.
# Preserve animations and source-prefab additions produced by the other tools.
ui_path=OUT/'ui.json';current=json.loads(ui_path.read_text(encoding='utf8'))
currency={}
for item_id,role in [('102','currencyCoin'),('104','currencyExp')]:
    record=items[item_id];sprite=record['sprite'];current['sprites'][sprite['sourceObject']]=sprite
    current['spritesByName'][sprite['name']]=sprite;current['visualBindings'][role]=sprite['name']
    currency[item_id]={k:v for k,v in record.items()if k in ['id','photoId','resourcePath','sourceTable','sourceBundle','icon','sha256']}
current['visualBindings']['experience']=items['104']['sprite']['name'];current['currencySource']=currency
ui_path.write_text(json.dumps(current,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(items=len(items),images=sum('icon'in r for r in items.values()),missing=missing,first=[items.get(str(i))for i in [102,104,20601,30201,10701,31101,30402,10104]]),ensure_ascii=True))
