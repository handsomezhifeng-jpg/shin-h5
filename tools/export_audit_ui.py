from pathlib import Path
import ast,json,shutil,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parents[1];dest=OUT/'assets/scene/audit-ui';dest.mkdir(parents=True,exist_ok=True);images={}
for name in ['img_gacha_title_01','img_gacha_title_02']:
 src=ROOT/'client/SHIN/Assets/ResourcesAssets/Texture/ArtisticFont/zh_cn'/(name+'_zh_cn.png');target=dest/src.name;shutil.copy2(src,target);images[name]=target.relative_to(OUT).as_posix()
rules=json.loads((OUT/'assets/board-rules.json').read_text(encoding='utf8'));gacha_source=(OUT/'game-data.js').read_text(encoding='utf8');gd=json.loads(gacha_source[gacha_source.index('{'):gacha_source.rfind('}')+1]);wanted={r['icon'] for r in gd['gacha']};wanted.update(stem for m in rules['gachaMeta'].values() for stem in [m['shell'],m['shell']+'_b']);wanted.add('normal_golden')
mod=ast.parse((OUT/'scripts/export_config.py').read_text(encoding='utf8'));exec(compile(ast.Module(body=[n for n in mod.body if isinstance(n,ast.FunctionDef)],type_ignores=[]),'native probability decoder','exec'));base=ROOT/'client/SHIN/Assets/ResourcesAssets/Config/Data/Default'
lang=json.loads((ROOT/'client/SHIN/Assets/ResourcesAssets/Lang/Default/lang_zh_cn.txt').read_text(encoding='utf-8-sig'));lookup={int(x['key']):x['value']for x in lang['lang']};pv={num(x,1):x for x in rows('player_variables')};items={num(x,1):x for x in rows('item')};probabilities=[]
for r in rows('gacha_rule'):
 if num(r,2)!=1:continue
 rewards=[fields(x)for x in r.get(4,[])]
 for i,v in enumerate(rewards):
  t,ident,count=num(v,1),num(v,2),num(v,3);cfg=(pv if t==1 else items).get(ident,{});icon=txt(cfg,3 if t==1 else 9);wanted.add(icon);probabilities.append({'gold':bool(num(r,3)),'name':lookup.get(num(cfg,2),str(ident))+'×'+str(count),'icon':icon,'probability':num(r,5)/100 if not num(r,3)or i==0 else 0,'split':i==len(rewards)-1,'yMove':.5*(len(rewards)-1)if i==0 and len(rewards)>1 else 0})
for pkg in ['GachaMachine','IconItem']:
 folder=ROOT/'fgui/assets'/pkg;xml=ET.parse(folder/'package.xml').getroot()
 for e in xml.find('resources'):
  name=e.get('name','');stem=Path(name).stem
  if e.tag=='image' and stem in wanted:
   src=folder/e.get('path','/').lstrip('/')/name;target=dest/(pkg+'-'+name);shutil.copy2(src,target);images[stem]=target.relative_to(OUT).as_posix()
lang=json.loads((ROOT/'client/SHIN/Assets/ResourcesAssets/Lang/Default/lang_zh_cn.txt').read_text(encoding='utf-8-sig'));strings={str(x['key']):x['value']for x in lang['lang']if int(x['key'])in[10400071,10100016,11000007,11200027,10200053,10200054,10800038,10800055]}
(OUT/'assets/scene/audit-ui.json').write_text(json.dumps({'images':images,'strings':strings,'gachaProbabilities':probabilities},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
