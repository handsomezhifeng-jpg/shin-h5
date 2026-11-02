from pathlib import Path
from PIL import Image,ImageDraw
import json,math
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'outputs/jiangdong-c-work';ASSETS=ROOT/'assets/construction'
def main():
    inventory=json.loads((ROOT/'outputs/construction-first-ten/resources.json').read_text(encoding='utf8'));groups=[]
    def board(key,items,cols,desc,kind='ui'):
        rows=math.ceil(len(items)/cols);im=Image.new('RGB',(cols*420,rows*420),'#e5e9e4');d=ImageDraw.Draw(im);cells=[]
        for i,item in enumerate(items):
            p=ROOT/item['source'];source=Image.open(p).convert('RGBA');size=list(source.size);source.thumbnail((378,350),Image.Resampling.LANCZOS);x=i%cols*420;y=i//cols*420;im.paste(source,(x+(420-source.width)//2,y+48+(350-source.height)//2),source);d.text((x+10,y+9),f"{i+1} {p.stem}",fill='#233c32');cells.append({'index':i,'source':item['source'],'size':size,'name':p.stem,**{k:v for k,v in item.items()if k!='source'}})
        p=WORK/'references'/f'{key}.png';im.save(p);groups.append({'id':key,'columns':cols,'rows':rows,'cells':cells,'reference':str(p),'kind':kind,'description':desc})
    items=[];technical=[]
    for f in inventory['files']:
        if f['category'].startswith('共用UI')and f['path'].endswith('.png'):
            name=Path(f['path']).stem
            if name.startswith(('Glow_','Ring_','Mask_','Noise_','Common_EmptySquare','common_bg_white')):
                technical.append({'source':f['path'],'reason':'Neutral mask/glow used by the original compositing and transitions.'});continue
            items.append({'source':f['path']})
    for start in range(0,len(items),12):board('ui-'+str(start//12+1),items[start:start+12],4,'每格原有的界面底板、按钮、木框、任务书、箭头或功能图标，按相同语义改成江东酒楼风格：米白纸、浅胡桃木、灰青与竹叶少量点缀。保持原图外形、长宽比例和九宫格边框，按钮内不写数值或新文字；已有＋、×、锁、箭头等功能符号必须清晰保留。不要生成完整界面，不画人物，不加界面外文字。原功能图标仍能认出相同用途，未开放平台标记用中性小竹牌/包裹图案替换。')
    icons=[{'source':f['path']}for f in inventory['files']if f['category']=='货币/任务奖励图标'];board('goods-icons',icons,4,'前十步的铜钱、经验、奖励物品图标，保留每格原物件语义与数量，换成江东水墨Q版的干净大色块、古铜、竹木、陶器与米白灰青。没有文字或数量。', 'goods')
    profiles=json.loads((ASSETS/'portraits/npc-animations.json').read_text(encoding='utf8'))['roles']
    for id in [8001,8002,8012,8016]:
        p=profiles['npc_'+str(id)];board('static-'+str(id),[{'source':'assets/construction/portraits/'+p['image']['url'],'role':'npc_'+str(id)}],1,'图1中原角色身份、性别、年龄、姿势不变。换成C版汉末三国酒楼相关人物：简洁朴素的衣物、米白灰青浅木棕、温润淡彩水墨，脸部轮廓清晰，保持原图身体裁切范围、视线与表情，不增加人物。透明背景。','static')
    for step in inventory['steps']:
        for cg in step['cg']:board('cg-'+str(cg['id']),[{'source':cg['path'],'cgId':cg['id']}],1,'保留参考中的事件构图、人物关系、动作和镜头，换成C版江东三国酒楼世界的淡彩水墨Q版剧情插图，服装汉末朴素布衣，场景材质浅木、米白、灰青。不要增加人物、UI、文字或水印，非照片、不华丽宫廷，沿用原画裁切范围。','cg')
    board('hammer',[{'source':'assets/construction/images-ui/UIFX_Customization_Chuizi_01-336b6a49.png'}],1,'保持原施工锤子轮廓、角度和功能，改成C版淡木柄、灰青铁锤头、柔和水墨Q版。','hammer')
    for f in inventory['files']:
        if f['path'].startswith(('assets/construction/images-hammer/','assets/construction/story-fx/')) and f['path'].endswith('.png'):
            technical.append({'source':f['path'],'reason':'Neutral particle, smoke sheet or hit alpha used by source shaders; preserve timing and compositing geometry.'})
    p=WORK/'extras-plan.json';p.write_text(json.dumps({'groups':groups,'technicalRetained':technical},ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'groups':[(g['id'],len(g['cells']))for g in groups],'neutralTechnical':len(technical)}))
if __name__=='__main__':main()
