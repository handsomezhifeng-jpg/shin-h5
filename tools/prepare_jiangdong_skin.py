"""Build source-linked reference boards for the selected Jiangdong C skin."""
from pathlib import Path
from PIL import Image, ImageDraw
import json, math

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'outputs/jiangdong-c-work'
ASSETS = ROOT / 'assets/construction'
STYLE = ROOT.parent / '经验/知识库/美术方案/三国酒楼/2026-11-02-十步后三版/C-江东清雅.png'


def main():
    WORK.mkdir(exist_ok=True)
    refs = WORK / 'references'
    refs.mkdir(exist_ok=True)
    inventory = json.loads((ROOT / 'outputs/construction-first-ten/resources.json').read_text(encoding='utf8'))
    scene = json.loads((ASSETS / 'scene-runtime.json').read_text(encoding='utf8'))
    profiles = []

    def board(key, title, ids, cols, desc, labels=None):
        rows = math.ceil(len(ids)/cols)
        width, height = cols*420, rows*420
        im = Image.new('RGB', (width, height), '#e5e9e4')
        draw = ImageDraw.Draw(im)
        cells = []
        for i, id in enumerate(ids):
            record = scene['sprites'][id]
            source = Image.open(ASSETS / record['url']).convert('RGBA')
            source.thumbnail((376, 355), Image.Resampling.LANCZOS)
            x, y = i % cols*420, i//cols*420
            im.paste(source, (x+(420-source.width)//2, y+45+(355-source.height)//2), source)
            draw.text((x+12, y+10), str(i+1)+' '+record['name'], fill='#233c32')
            cells.append({'index': i, 'spriteId': id, 'name': record['name'], 'source': record['url'], 'size': record['imageSize'], 'label': labels[i] if labels else record['name']})
        target = refs / (key+'.png')
        im.save(target)
        profiles.append({'id': key, 'title': title, 'columns': cols, 'rows': rows, 'reference': str(target), 'cells': cells, 'description': desc})

    core = {}
    for s in inventory['steps']:
        for t in s['targets']:
            core[t['unitId']] = t
    for key, uid, title, desc in [
        ('wine-stall', '0_11749', '酒水摊', '把原茶摊改成C版酒水摊：浅胡桃木、米白素布、青瓷酒壶、深陶酒坛和一面仅写“酒”的小幌。不要人物。'),
        ('food-stall', '0_11754', '蒸食酒肴摊', '把原甜品摊改成C版蒸食酒肴摊：浅木柜、米白素布、竹蒸笼、包子和陶碟，一面仅写“食”的小幌。不要人物。'),
        ('fruit-stall', '0_11753', '果盘摊', '把原水果摊改成C版果盘摊：浅木柜、素布、竹篮、桃梨橘子与小果盘，一面仅写“果”的小幌。不要人物。'),
        ('parasols', '0_13010', '纸伞与桌凳', 'C版临水酒楼的浅青纸伞、素净石桌与浅木小凳，保持各格原物件组合和朝向。不要多加桌凳。')]:
        t = core[uid]
        ids = [s['id'] for s in t['initial']['sprites']] + [s['id'] for v in t['variants'] for s in v['sprites']]
        board(key, title, ids, 2, desc+' 四格顺序：破损待修状态、完成款式1、完成款式2、完成款式3。后三款在江东C同一风格内以青白/淡竹/浅木细节区分。')
    fence = core['0_13009']
    board('fences', '三向围栏', [s['id'] for s in fence['initial']['sprites']]+[s['id'] for v in fence['variants'] for s in v['sprites']], 3,
          '每格严格只画原图对应的一段围栏或一根立柱，保留原来的对角方向和正面朝向，不补成整圈。浅木细竹、青灰少量连接件。每排三件是同款围栏组件；第一排断裂破旧，第二至第四排分别是三款完整样式。')
    floors=[]
    for uid in ['0_11833', '1_10045']:
        t=core[uid]
        for s in t['initial']['sprites']+[s for v in t['variants'] for s in v['sprites']]:
            if s['id'] not in floors: floors.append(s['id'])
    board('core-floors', '十步修建地面', floors, 5,
          '全是等距俯视的独立菱形地砖，沿原图2比1斜轴，不是平铺正方形。前四格是轻微破裂、边缘长草的待修地砖；第5至7格是入口三款完整地面：淡木板、浅米灰石板、青白细砖；第8至10格是厅堂三款：青白大砖、淡暖石砖、浅灰绿石砖。每块的轮廓和砖缝方向必须和输入格保持一致，边缘连续、平整，不带高底座。')
    debris=[]
    for uid in ['1_11996','1_11720','1_11724','1_12908','1_11716','1_12909']:
        for s in core[uid]['initial']['sprites']:
            if s['id'] not in debris: debris.append(s['id'])
    board('core-debris', '待清理物件', debris, 3,
          '江东酒楼开张前的旧木杂物、破桌、草袋和碎木器。保持每格对应物件类型、数量、视角与左右朝向。轻度旧损、素木灰麻布，清楚有序，不要血迹或现代垃圾，不要加入新家具。')
    # Runtime-visible surroundings, including the source's still-dark rooms.
    loaded=set(json.loads((ROOT/'outputs/construction-first-ten/verification.json').read_text(encoding='utf8'))['loadedConstructionFiles'])
    all_ids=[id for id,s in scene['sprites'].items() if 'assets/construction/'+s['url'] in loaded]
    covered={c['spriteId'] for p in profiles for c in p['cells']}
    technical=[]
    buckets={'tiles':[], 'plants':[], 'architecture':[], 'props':[]}
    for id in all_ids:
        if id in covered:continue
        name=scene['sprites'][id]['name'].lower()
        if name.startswith('mask_'):
            technical.append({'spriteId':id,'reason':'Functional fog mask; retain original alpha geometry.'});continue
        if name=='river_01':
            buckets['tiles'].append(id)
        elif any(t in name for t in ['dizhuan','diban','mudiban','caodi','nilu','zhuanbian','dizuo','floor','ditan','xiajiao','zuoxia']):buckets['tiles'].append(id)
        elif any(t in name for t in ['luwei','xiaohua','liushu','huashu','shu_','hehua','heye','caodui','he-','hehuan','taoshu']):buckets['plants'].append(id)
        elif any(t in name for t in ['qiang','men','zhuzi','lizhu','langan','weilan','denglong','chuanghu','guahua','pingfeng']):buckets['architecture'].append(id)
        else:buckets['props'].append(id)
    for kind, ids in buckets.items():
        # Large silhouettes have their own cells rather than being hidden in a full scene.
        gate=[id for id in ids if scene['sprites'][id]['name']=='bad_roomgate_damen']
        ids=[id for id in ids if id not in gate]
        if gate:board('main-gate','三国酒楼门楼',gate,1,'独立门楼，不带背景。将牌匾严格写成四个汉字“三国酒楼”，浅木、青灰瓦、米白灯笼，结构完整但略有旧痕；保持原图形状、朝向、视角与各柱脚位置，所有牌匾字在图内清楚完整。')
        size=12 if kind=='tiles' else 9
        desc={
            'tiles':'保持每格原地表/岸砖/边条的功能、形状与等距轴，换成C版浅青水、米灰砖、淡绿草地、浅木边条或旧席垫。菱形砖的四边要可连续拼接，边条不增加台阶厚度。',
            'plants':'植物、柳树、花团、芦苇、荷叶、岸草按每格原物种与方向重画。C版灰绿浅青、少量米白小花，大团块、简化碎叶，读得清，不新增花盆或地面。',
            'architecture':'江东临水酒楼的独立墙段、门、立柱、栏杆、窗、挂画或屏风。严格按原图每格的方向、占地轮廓和破损程度重画，粉白灰墙、浅胡桃木、青灰瓦、素竹纸；旧件仍旧，破件仍破，不加屋顶、地板或成套房间。',
            'props':'按每格原独立道具类型和朝向改成江东C版酒楼用具或岸边摆件。木柜、破旧柜台、桌椅、旧木箱仍按原破损状态；石兽换成朴素汉式小石狮，水边摆件保持亲切Q版。浅木、青瓷、灰石与竹麻，禁止现代物品，不加人物与背景。'}[kind]
        for start in range(0,len(ids),size):board(f'{kind}-{start//size+1}',kind,ids[start:start+size],4 if kind=='tiles' else 3,desc)
    packet={'styleReference':str(STYLE),'groups':profiles,'technicalRetained':technical,'sourceSceneSprites':len(all_ids),'coreSprites':len(inventory['sceneSprites'])}
    (WORK/'plan.json').write_text(json.dumps(packet,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'groups':[(p['id'],len(p['cells']))for p in profiles],'technical':technical,'totalMapped':sum(len(p['cells']) for p in profiles)},ensure_ascii=False))


if __name__=='__main__':main()
