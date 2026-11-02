from pathlib import Path
from PIL import Image
import json,hashlib
from pack_jiangdong_skin import isolated_cell
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'outputs/jiangdong-c-work';OUT=ROOT/'assets/construction/skins/jiangdong-c'
def main():
    plan=json.loads((WORK/'extras-plan.json').read_text(encoding='utf8'));p=OUT/'skin.json';manifest=json.loads(p.read_text(encoding='utf8'));files=manifest.setdefault('files',{});roles=manifest.setdefault('roles',{});records=[];pending=[]
    for g in plan['groups']:
        raw=WORK/'raw'/(g['id']+'.png')
        if not raw.exists()or not raw.with_suffix('.json').exists():pending.append(g['id']);continue
        sheet=Image.open(raw).convert('RGBA')
        for c in g['cells']:
            source=Image.open(ROOT/c['source']).convert('RGBA')
            if g['kind']=='cg':im=sheet;box=(0,0,*sheet.size)
            else:im,box=isolated_cell(sheet,c['index'],g['columns'],g['rows'],len(g['cells'])==1)
            im=im.resize(source.size,Image.Resampling.LANCZOS);key=hashlib.sha256(c['source'].encode()).hexdigest()[:16];target=OUT/'interface'/f'{key}.webp';target.parent.mkdir(exist_ok=True);im.save(target,lossless=True,exact=True,method=5);relative='assets/construction/skins/jiangdong-c/interface/'+target.name;files[c['source']]=relative
            if g['kind']=='static':roles[c['role']]={'imageURL':relative}
            records.append({'source':c['source'],'url':relative,'group':g['id'],'kind':g['kind'],'size':list(im.size),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'generatedSheetSha256':hashlib.sha256(raw.read_bytes()).hexdigest(),'sheetCell':c['index'],'sheetCrop':list(box)})
    aliases=[];by_name={Path(r['source']).name:r for r in records}
    for candidate in (ROOT/'assets/construction').glob('images-*/*.png'):
        record=by_name.get(candidate.name)
        if not record:continue
        relative=candidate.relative_to(ROOT).as_posix()
        if relative==record['source']:continue
        if hashlib.sha256(candidate.read_bytes()).digest()!=hashlib.sha256((ROOT/record['source']).read_bytes()).digest():continue
        files[relative]=record['url'];aliases.append({'source':relative,'identicalTo':record['source'],'url':record['url']})
    manifest['fileAliases']=aliases;manifest['extras']=records;manifest['pendingExtras']=pending;manifest['neutralTechnicalRetained']=plan['technicalRetained'];p.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'extras':len(records),'pending':pending,'fileMappings':len(files),'aliases':len(aliases),'roles':len(roles)}))
if __name__=='__main__':main()
