"""Prepare/submit/query the installed Seedance skill; no credentials in project."""
from pathlib import Path
import argparse,concurrent.futures,json,subprocess,sys,time,hashlib
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
LAB=ROOT/'action-lab'
JOBS=ROOT.parent/'seedance-jobs/market-actions-draft-v1'
SKILL=Path('C:/Users/zhfzhang/.agents/skills/seedance-video/scripts/seedance_video.py')
DEFINITIONS=[
 ('sweep','扫地','扫地人','sweeper',0,'sweep',
  '双手始终握住同一把扫帚，重心轻轻前移，肩肘手腕连贯发力，把扫帚从左侧地面扫向右侧，再自然收回。扫帚毛触地，腰部和膝盖随动作微屈，目光看扫帚前的地面。重复三次完整的扫地动作，动作轻快但不夸张，四肢不是整张图左右摇摆。'),
 ('sweeper-walk-front','携扫帚走路 · 正面','扫地人','sweeper',6,'walk',
  '保持三分之二正面、脸朝画面左侧约30度，以正常步态原地行走。左右腿交替迈步，脚掌经历抬脚、摆腿、脚跟或前脚掌触地、承重、蹬离。髋部和双肩有相反方向的轻微转动。左手握同一把扫帚的木柄，使扫帚竖立在肩侧，另一只手自然摆臂，扫帚与手接触稳定。'),
 ('sweeper-walk-back','携扫帚走路 · 背面','扫地人','sweeper',4,'walk',
  '保持三分之二背面、身体朝画面右上方向约30度，以正常步态原地行走。左右腿交替迈步，脚掌经历抬脚、摆腿、落脚、承重和蹬离；肩膀和髋部自然反向配合。单手稳定握住同一把扫帚的木柄，让扫帚竖在肩侧；另一只手自然摆动。始终保留背面，不能转向镜头。'),
 ('customer-walk-front','顾客提菜走路 · 正面','买菜顾客','customers',4,'walk',
  '保持三分之二正面、脸朝画面左侧约30度，右手提一个米棕色小布袋，以正常步态原地行走。左右腿交替迈步并真实屈膝，脚掌有完整抬脚、向前摆、落脚、承重、蹬离的过程。髋部有适量转动，空着的手自然摆臂，布袋随步伐轻轻摆动而不变形。布袋和内容物使用米色和暖棕色，不使用背景同样的亮绿色。'),
 ('customer-walk-back','顾客走向摊位 · 背面','买菜顾客','customers',0,'walk',
  '保持三分之二背面、身体朝画面左上方向约30度，以正常步态原地行走。左右腿交替迈步并真实屈膝，脚掌完整抬起、摆腿、落脚、承重、蹬离。双手自然前后摆动，肩膀和髋部轻微反向转动。没有手持物，始终保留背面，不能转向镜头。'),
 ('customer-buy','顾客伸手购买','买菜顾客','customers',0,'gesture',
  '保持三分之二背面朝画面左上方，双脚基本站稳。先稍微前倾看货，右臂从自然下垂抬起，手掌朝上向前伸出，五指自然弯曲做接过物品的手势，停留半秒，然后收回到胸前看一眼，再自然放下。头部和肩膀轻微跟随，重复两遍。只表演一个人的购买动作，不添加商贩、柜台或悬浮物品。'),
 ('vendor-serve','摊主招呼递货','摊主','vendors',0,'gesture',
  '保持参考角色的三分之二正面，视线朝画面右下方的顾客位置。轻轻点头微笑，右肩带动右臂向前伸出，肘部逐步伸展，手掌自然摊开做递货手势，停留半秒后慢慢收回，再用另一只手做一个温和招呼手势，然后回到初始双手姿态。重复两遍，保持完整肩、肘、手腕和手的连接。'),
 ('vendor-arrange','摊主整理货物','摊主','vendors',0,'gesture',
  '保持参考角色的三分之二正面，头稍微低下看向身前腰部位置。双肩与肘部自然配合，双手交替向下前方伸出，像把两件小货物轻轻摆正，再收手，抬头微笑，回到初始姿态。重复两遍。动作表达清晰，手腕自然弯曲，不画额外物品、桌子或柜台，双手不互相穿透。')
]

def write_json(p,value):
 p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8');tmp.replace(p)

def cli(verb,job=None,extra=()):
 args=[sys.executable,str(SKILL),verb]
 if job:args+=['--job-dir',str(job)]
 args+=list(map(str,extra));result=subprocess.run(args,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=160)
 raw=result.stdout.strip() or result.stderr.strip()
 try:value=json.loads(raw)
 except json.JSONDecodeError:value={'error':'Skill command did not return valid JSON','command':verb,'returncode':result.returncode}
 if result.returncode and 'error' not in value:value['error']='Skill command failed'
 return value

def prepare():
 LAB.mkdir(exist_ok=True);(LAB/'references').mkdir(exist_ok=True);JOBS.mkdir(parents=True,exist_ok=True)
 old=json.loads((LAB/'manifest.json').read_text(encoding='utf8')) if (LAB/'manifest.json').exists() else None
 if old:return old
 source=ROOT/'assets/scene/skins/ink';atlas=json.loads((source/'residents-v4.json').read_text(encoding='utf8'));clips=[]
 for i,(ident,name,character,sheet,index,kind,action) in enumerate(DEFINITIONS):
  record=atlas['atlases'][sheet];frame=record['frames'][index];x,y,w,h=frame['crop'];sprite=Image.open(source/record['url']).convert('RGBA').crop((x,y,x+w,y+h));ref=Image.new('RGB',(720,1280),(0,255,0));ratio=min(470/w,870/h);sprite=sprite.resize((round(w*ratio),round(h*ratio)),Image.Resampling.LANCZOS);ref.paste(sprite,((720-sprite.width)//2,1060-sprite.height),sprite);refpath=LAB/'references'/f'{ident}.png';ref.save(refpath)
  identity={'sweeper':'米色短袍、深蓝领口和腰带、黑鞋、圆形黑发髻、同一把草黄色扫帚','customers':'灰蓝色短袍、黑鞋、圆形黑发髻，原参考同一位顾客','vendors':'黑色发髻、红棕色马甲、米白色袖子，原参考同一位女摊主'}[sheet]
  framing='完整全身，头顶和脚底均保持在画面内，人物占画面高度65%，鞋底基线固定在画面高度83%位置。' if sheet!='vendors' else '保持参考的头顶到腰部构图，整个头部、双肩、双臂和双手始终在画面内，人物占画面高度62%，腰部基线固定在画面高度83%位置。'
  prompt=f'''【任务】制作一条6秒、9:16、720p、24fps的游戏角色动作绿幕素材，单人，固定机位、固定比例、无剪辑。不是贴图平移或整张图摇晃，要有自然连续的关节动作。
【身份】严格保持参考图中这一个原创水墨Q版中国古代市井人物的身份：{identity}。圆脸、大头短身，眼睛和脸型、发型、衣服配色、线条、柔和水彩质感、年龄与头身比均沿用参考。参考只用于人物身份和构图，不生成任何第二个人。
【摄影与背景】锁定镜头、焦距、光照与角色尺寸。{framing}角色中心不发生平移，行走动作为原地走路供游戏引擎控制位移。背景为均匀纯亮绿RGB(0,255,0)色面，覆盖整幅画面；背景没有渐变、纹理、地平线、景物、投影、倒影、绿幕褶皱。人物服装和道具不能变成背景的纯亮绿色，轮廓清楚适合色键。镜头不缩放、不摇移、不旋转。
【分秒动作】0.0—0.4秒保持初始姿态，轻微呼吸。0.4—5.5秒：{action}5.5—6.0秒平稳回到起始姿态，为循环衔接留出稳定画面。
【检查约束】所有动作保持两条手臂、两只手、完整自然的人体连接；道具始终由原来那只手抓持，不增减、不漂浮、不融化。无角色变形换脸，无复制肢体，无定格抖动；衣服不能闪烁或变色。人物脚底/腰部基线稳定，角色不突然变大变小。
【声音与文字】完全无声，没有对白、配乐或任何音轨。画面无字幕、标题、文字、数字、UI、Logo或水印。'''
  promptpath=JOBS/f'{ident}-prompt.txt';promptpath.write_text(prompt,encoding='utf8');job=JOBS/ident
  prepared=cli('prepare',job,['--prompt-file',promptpath,'--duration','6','--ratio','9:16','--resolution','720p','--seed',202611010+i,'--reference-image',refpath,'--silent'])
  clip={'id':ident,'name':name,'character':character,'kind':kind,'model':'Doubao-seedance-2-5','version':'draft-v1','reviewStatus':'pending','generationStatus':'prepared','reference':'references/'+refpath.name,'durationRequested':6,'seed':202611010+i,'prompt':prompt,'jobId':None,'video':None,'frames':None,'error':prepared.get('error')}
  clips.append(clip)
 manifest={'version':1,'title':'角色动作模拟器','model':'Seedance 2.5','source':'Actual gateway video generation; approvals are reserved for the user.','batch':'核心动作首批审核','clips':clips,'updatedAt':time.time()};write_json(LAB/'manifest.json',manifest)
 # Reuse the approved empty scene only as an optional review background.
 Image.open(source/'source-clean-v3.png').save(LAB/'scene.webp',lossless=True,exact=True,method=6)
 return manifest

def run():
 manifest=prepare();clips=manifest['clips']
 def submit_clip(clip):
  if clip.get('error'):return clip['id'],{'error':clip['error']}
  return clip['id'],cli('submit',JOBS/clip['id'])
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  for ident,result in pool.map(submit_clip,clips):
   clip=next(c for c in clips if c['id']==ident);clip['jobId']=result.get('id');clip['generationStatus']=result.get('status','submitted' if clip['jobId'] else 'error');clip['error']=result.get('error');manifest['updatedAt']=time.time();write_json(LAB/'manifest.json',manifest);print(json.dumps({'clip':ident,'status':clip['generationStatus'],'jobId':clip['jobId'],'error':clip['error']},ensure_ascii=False),flush=True)
 for iteration in range(60):
  active=[c for c in clips if c.get('jobId') and c['generationStatus'] not in ['ready','failed','error','processing-error']]
  if not active:break
  def poll(clip):return clip['id'],cli('status',JOBS/clip['id'])
  with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
   for ident,result in pool.map(poll,active):
    clip=next(c for c in clips if c['id']==ident);status=result.get('status',clip['generationStatus'])
    if result.get('error') and not result.get('status'):print(json.dumps({'clip':ident,'queryError':result['error']},ensure_ascii=False),flush=True);continue
    if status!=clip['generationStatus']:print(json.dumps({'clip':ident,'status':status},ensure_ascii=False),flush=True)
    clip['generationStatus']=status
    if status in ['failed','error']:clip['error']=result.get('error') or 'Generation failed'
    if status in ['completed','succeeded','success']:
     downloaded=cli('download',JOBS/ident)
     if downloaded.get('path'):
      destination=LAB/'media'/ident;destination.mkdir(parents=True,exist_ok=True)
      processed=subprocess.run([sys.executable,str(ROOT/'tools/extract_seedance_actions.py'),'--input',downloaded['path'],'--output',str(destination),'--id',ident],capture_output=True,text=True,encoding='utf8',errors='replace',timeout=240)
      if processed.returncode:clip['generationStatus']='processing-error';clip['error']=processed.stderr[-1500:];print(json.dumps({'clip':ident,'status':'processing-error','error':clip['error']},ensure_ascii=False),flush=True)
      else:
       info=json.loads((destination/'frames.json').read_text(encoding='utf8'));clip['video']=f'media/{ident}/green-screen.mp4';clip['frames']=f'media/{ident}/frames.json';clip['poster']=f'media/{ident}/poster.webp';clip['qa']=info['qa'];clip['generationStatus']='ready';clip['error']=None;print(json.dumps({'clip':ident,'status':'ready','frames':info['count'],'qa':info['qa']['status']},ensure_ascii=False),flush=True)
     else:clip['error']=downloaded.get('error','Media download did not finish')
    manifest['updatedAt']=time.time();write_json(LAB/'manifest.json',manifest)
  if any(c.get('jobId') and c['generationStatus'] not in ['ready','failed','error','processing-error'] for c in clips):time.sleep(45)
 print(json.dumps({'done':True,'ready':sum(c['generationStatus']=='ready' for c in clips),'total':len(clips)},ensure_ascii=False),flush=True)

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('command',choices=['prepare','run']);args=parser.parse_args()
 if args.command=='prepare':print(json.dumps({'prepared':len(prepare()['clips'])}))
 else:run()
