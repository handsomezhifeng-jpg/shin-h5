from pathlib import Path
import json,shutil,hashlib
helpers=Path(__file__).with_name('export_event_ui.py').read_text(encoding='utf8').split('# Runtime-created attack selector')[0]
exec(compile(helpers,'event UI helpers','exec'))
pid=names['Common'];rid=next(r for r,e in index[pid]['items'].items()if e['attrs'].get('name')=='CommonFlyText.xml');ensure(pid,rid);data['roots']['CommonFlyText']={'pkg':pid,'id':rid}
DATAFILE.write_text('window.FGUI_DATA = '+json.dumps(data,ensure_ascii=False,separators=(',',':'),allow_nan=False)+';\n',encoding='utf8')
config={'root':'CommonFlyText','hudScale':.0075,'rotationX':35,'size':40,'iconSize':55,'positiveColor':'#ffe753','negativeColor':'#d94057','positiveOutline':'#62422e','negativeOutline':'#622e2e','textWorldOffset':1/3,'sameDiceWorldOffset':1,'effectWorldOffset':.1521,'sources':['client/SHIN/Assets/Script/Game/moduls/Common/FlyText/FlyTextConfigs.cs:66','client/SHIN/Assets/Script/Game/moduls/Common/FlyText/CommonFlyText.cs:25','client/SHIN/Assets/Script/Game/moduls/Chessboard/Square/SquareBase.cs:300','fgui/assets/Common/Component/FlyText/CommonFlyText.xml'],'files':records}
config['audio']={}
for name in ['MoneyDud','LoseMoney']:
 source=ROOT/'client/SHIN/Assets/Art/Audio/Originals/Sound/ChessBorad'/(name+'.ogg');dest=OUT/'assets/scene/coin-fx'/(name+'.ogg');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest);config['audio'][name]={'url':str(dest.relative_to(OUT)).replace('\\','/'),'source':str(source.relative_to(ROOT)).replace('\\','/'),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'volume':1,'pitch':1}
(OUT/'assets/scene/coin-text.json').write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print('Original CommonFlyText exported')
