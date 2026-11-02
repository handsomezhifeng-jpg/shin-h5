"""Original-sweeper I2V candidates with capped game sequence frame budgets."""
from pathlib import Path
import argparse,concurrent.futures,hashlib,importlib.util,json,shutil,sys,time
from PIL import Image
from seedance_action_batch import cli,write_json,SKILL

ROOT=Path(__file__).resolve().parents[1];LAB=ROOT/'action-lab';JOBS=ROOT.parent/'seedance-jobs/original-sweeper-draft-v3'
SPECS=[('original-sweep-20','原角色 · 扫地（20帧）','sweep',20,2026110120,
 '保持原图中身体朝左的三分之二视角，双脚站在原地。两只圆圆的小手抓住同一把扫帚木柄。肩和手肘连续带动扫帚毛贴着地面，向画面左侧轻扫，再扫回脚边，再回到原图的左侧起始位置。腰部和膝盖小幅配合，头只轻轻低下看扫帚，不换角度、不大幅转头。0.6—2.6秒完整完成一次“左侧开始→扫到脚边→回到左侧”的2秒循环，2.6—4.6秒同样再重复一次。'),
 ('original-sweeper-walk-24','原角色 · 走路（24帧）','walk',24,2026110124,
 '保持原图朝画面左侧的三分之二正面方向，双手维持原图握扫帚的位置，让扫帚毛抬离地面一点点。小人以短腿正常步态原地行走，左脚抬起向前、落脚承重，右脚跟上抬起向前、落脚承重，两腿交替屈膝，身体只有很轻的重心起伏。双手与扫帚保持稳定连接，不用新增手臂去摆。0.7—2.0秒完成一个左右脚完整交替的1.3秒行走循环，2.0—3.3秒和3.3—4.6秒重复同一循环。角色整体始终留在同一位置，不滑过画面。')]

def prepare():
 JOBS.mkdir(parents=True,exist_ok=True);record=JOBS/'batch.json'
 if record.exists():return json.loads(record.read_text(encoding='utf8'))
 generated=Path('C:/Users/zhfzhang/.codex/generated_images/01a19545-c6bc-7aa1-adaf-03ca5af4272e/exec-5dea96f9-c0e0-4016-b715-012c89f7033b.png');clean=LAB/'references/original-sweeper-clean-v2.png';shutil.copyfile(generated,clean)
 sprite=Image.open(clean).convert('RGBA');sprite=sprite.crop(sprite.getchannel('A').getbbox());ratio=min(440/sprite.width,770/sprite.height);sprite=sprite.resize((round(sprite.width*ratio),round(sprite.height*ratio)),Image.Resampling.LANCZOS);ref=Image.new('RGB',(720,1280),(0,255,0));ref.paste(sprite,((720-sprite.width)//2,1020-sprite.height),sprite);reference=LAB/'references/original-sweeper-first-last-v2.png';ref.save(reference)
 clips=[]
 for ident,name,kind,count,seed,action in SPECS:
  prompt=f'''直接让首帧图中这一个原来的Q版扫地小人动起来，并回到完全相同的尾帧。首尾图是角色外形与画面布局的严格约束，不是灵感参考。6秒，固定相机，纯亮绿色背景，无声。
角色必须一直长得和图上一样：大而圆的黑头发，橙色发绳的圆发髻，原图的两颗纯黑圆点眼睛、很小的嘴、圆脸，米色短外衣，深蓝领口及腰带，黑色圆鞋，同一把草黄色短扫帚。保持原来的胖圆二头身，头部含发髻接近整个人物高度的一半，头宽约等于肩宽；躯干和腿短圆，不能长高或变瘦。保持原图的柔和插画表面和颜色，不换成写实、铅笔线稿、水墨成人或三头身。眼睛始终是原图的纯黑圆点，没有眼白、虹膜或成年人的细长五官。
0.0—0.6秒保持首帧原姿态。
0.6—4.6秒：{action}
4.6—5.5秒自然回到首帧站姿，5.5—6.0秒保持尾帧同一姿势。动作要来自肩肘腕和双腿的连贯运动，不是整张图平移、伸缩或摇摆。
原人物全身和扫帚完整在画面内，比例、中心位置、鞋底高度和景别固定，不推拉镜头，不切镜，不转到另一面，不增加人、手臂、手、扫帚或物品。背景保持首帧的均匀纯绿色，不添加地面、地平线、阴影、字幕、文字、UI、Logo、水印或音乐。'''
  prompt_path=JOBS/f'{ident}-prompt.txt';prompt_path.write_text(prompt,encoding='utf8');job=JOBS/ident
  p=cli('prepare',job,['--prompt-file',prompt_path,'--duration','6','--ratio','9:16','--resolution','720p','--seed',seed,'--reference-image',reference,'--reference-image',reference,'--silent'])
  if p.get('error'):raise RuntimeError(p['error'])
  request=json.loads((job/'request.json').read_text(encoding='utf8'));request['body']['ratio']='adaptive';request['conditioning']={'roles':['first_frame','last_frame'],'documentation':'https://docs.volcengine.com/docs/ark/seedance-2-5?lang=zh','implementation':'Installed skill submit/auth/idempotency. Image roles first/last plus New API metadata.content forwarding in memory; no base64 persisted.','gatewayContract':'https://github.com/QuantumNous/new-api/blob/main/plugins/tasks/doubao/plugin.js#L832'};write_json(job/'request.json',request)
  clips.append({'id':ident,'name':name,'character':'原画扫地角色','kind':kind,'frameLimit':count,'model':'Doubao-seedance-2-5','version':'draft-v3','reviewStatus':'pending','generationStatus':'prepared','reference':'references/'+reference.name,'originalReference':'references/original-sweeper-locked.json','durationRequested':6,'seed':seed,'prompt':prompt,'jobId':None,'video':None,'frames':None,'error':None,'conditioning':'first_frame + last_frame'})
 batch={'version':2,'clips':clips};write_json(record,batch);merge(batch);return batch

def merge(batch):
 manifest=json.loads((LAB/'manifest.json').read_text(encoding='utf8'));ids={c['id'] for c in batch['clips']};manifest['clips']=[*batch['clips'],*[c for c in manifest['clips'] if c['id'] not in ids]];manifest['batch']='原扫地角色：20帧扫地 / 24帧走路';manifest['updatedAt']=time.time();write_json(LAB/'manifest.json',manifest);write_json(JOBS/'batch.json',batch)

def submit_first_last(job):
 spec=importlib.util.spec_from_file_location('installed_seedance_skill',SKILL);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);config=module.read_json(module.CONFIG_PATH);key=module.credential(config['api_key_env']);real_api=module.api
 def conditioned_api(config,key,method,endpoint,body=None):
  if body is not None:
   images=[c for c in body['content'] if c.get('type')=='image_url']
   if len(images)!=2:raise ValueError('Original character requires exactly two frame anchors')
   for item,role in zip(images,['first_frame','last_frame']):item['role']=role
   body['ratio']='adaptive'
   body['metadata']={k:body[k] for k in ['content','ratio','resolution','generate_audio','watermark','return_last_frame','seed'] if k in body}
  return real_api(config,key,method,endpoint,body)
 module.api=conditioned_api
 return module.submit(job,config,key)

def run():
 batch=prepare()
 for clip in batch['clips']:
  if clip.get('jobId'):continue
  try:result=submit_first_last(JOBS/clip['id']);clip['jobId']=result.get('id');clip['generationStatus']=result.get('status','submitted');clip['error']=None
  except Exception as e:clip['error']=str(e);clip['generationStatus']='error'
  merge(batch);print(json.dumps({'id':clip['id'],'status':clip['generationStatus'],'jobId':clip['jobId'],'error':clip['error']},ensure_ascii=False),flush=True)
 for iteration in range(60):
  active=[c for c in batch['clips'] if c['generationStatus'] not in ['completed','ready','error','failed']]
  if not active:break
  for clip in active:
   result=cli('status',JOBS/clip['id']);status=result.get('status',clip['generationStatus'])
   if result.get('error') and not result.get('status'):continue
   if status in ['completed','succeeded','success']:
    media=cli('download',JOBS/clip['id'])
    if media.get('path'):clip['generationStatus']='completed';clip['sourceDownloaded']=True
   else:clip['generationStatus']=status;clip['error']=result.get('error')
   merge(batch);print(json.dumps({'id':clip['id'],'status':clip['generationStatus']},ensure_ascii=False),flush=True)
  if any(c['generationStatus'] not in ['completed','ready','error','failed'] for c in batch['clips']):time.sleep(45)
 print(json.dumps({'finished':True,'states':{c['id']:c['generationStatus'] for c in batch['clips']}},ensure_ascii=False),flush=True)

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('command',choices=['prepare','run']);args=parser.parse_args()
 if args.command=='prepare':print(json.dumps({'prepared':len(prepare()['clips'])}))
 else:run()
