"""Extend existing milestone UI metadata with original scheduled skins. No component changes."""
from pathlib import Path
import ast,json,shutil
from PIL import Image
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parents[1]
c=json.loads((OUT/'assets/activities/config.json').read_text(encoding='utf8'));p=OUT/'assets/scene/milestone/ui.json';ui=json.loads(p.read_text(encoding='utf8'))
mod=ast.parse((OUT/'scripts/export_config.py').read_text(encoding='utf8'))
exec(compile(ast.Module(body=[n for n in mod.body if isinstance(n,ast.FunctionDef)],type_ignores=[]),'original config decoder','exec'))
base=ROOT/'client/SHIN/Assets/ResourcesAssets/Config/Data/Default'
configs={num(r,1):r for r in rows('activity_milestone_ui')};proof=[]
def copy(source,stem):
 if not source.is_file():raise FileNotFoundError(source)
 dest=OUT/'assets/scene/milestone'/source.name
 if not dest.is_file():shutil.copy2(source,dest)
 assert source.read_bytes()==dest.read_bytes()
 with Image.open(dest)as im:w,h=im.size
 ui['dynamicImages'][stem]={'url':dest.relative_to(OUT).as_posix(),'width':w,'height':h,'source':source.relative_to(ROOT).as_posix()}
 proof.append({'source':source.relative_to(ROOT).as_posix(),'output':dest.relative_to(OUT).as_posix()})
for a in c['activities']:
 ident=a['skinId'];r=configs[ident];cfg={'skinId':ident,'title':txt(r,2),'noRankBgMain':txt(r,3),'noRankBg':txt(r,4),'rankBg':[v.decode('utf8')for v in r.get(5,[])]};ui['packagingConfigs'][str(ident)]=cfg
 copy(ROOT/a['iconSource'],a['icon'])
 for stem in set([cfg['noRankBg']] if a['kind']=='noRank' else [cfg['title'],*cfg['rankBg']]):
  source=ROOT/'client/SHIN/Assets/ResourcesAssets/Texture/ArtisticFont/zh_cn'/(stem+'_zh_cn.png')
  if not source.is_file() and stem.startswith('img_tournament_banner_'):source=ROOT/'client/SHIN/Assets/ResourcesAssets/Texture/Block10x10'/(stem+'.png')
  copy(source,stem)
p.write_text(json.dumps(ui,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(OUT/'assets-activity-calendar-source.json').write_text(json.dumps({'source':'原国服排期与原 Unity 美术','records':list({x['output']:x for x in proof}.values())},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({'activities':len(c['activities']),'skins':len(ui['packagingConfigs']),'images':len(ui['dynamicImages'])}))
