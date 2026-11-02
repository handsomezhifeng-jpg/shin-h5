"""Decode actual Seedance video, key its green background and pack review frames."""
from pathlib import Path
import argparse,hashlib,json,math,shutil,subprocess,zipfile
import cv2,numpy as np
from PIL import Image,ImageDraw
import imageio_ffmpeg

FFMPEG=imageio_ffmpeg.get_ffmpeg_exe()
def run(args):
 p=subprocess.run(args,capture_output=True)
 if p.returncode:raise RuntimeError(p.stderr.decode('utf8',errors='replace')[-1800:])
 return p.stdout
def key_green(rgb):
 p=rgb.astype(np.float32);height,width=p.shape[:2];border=np.concatenate([p[:12].reshape(-1,3),p[:height//2,:12].reshape(-1,3),p[:height//2,-12:].reshape(-1,3)]);background=np.median(border,axis=0);difference=np.sqrt(np.mean((p-background)**2,axis=2));noise=np.percentile(np.sqrt(np.mean((border-background)**2,axis=1)),95);low=max(4.,float(noise)+2);high=low+13
 # Some actual candidates use a muted green watercolor field. Detect the
 # connected exterior by its measured color; keep enclosed actor colors.
 eligible=(difference<high).astype('uint8');n,bg_labels,_,_=cv2.connectedComponentsWithStats(eligible,8);border_labels=np.unique(np.concatenate([bg_labels[0],bg_labels[-1],bg_labels[:,0],bg_labels[:,-1]]));border_labels=border_labels[border_labels!=0];exterior=np.isin(bg_labels,border_labels);alpha=np.full((height,width),255,dtype='uint8');alpha[exterior]=np.round(np.clip((difference[exterior]-low)/(high-low),0,1)*255).astype('uint8');alpha[difference<low]=0
 if background[1]>200 and background[0]<80 and background[2]<80:
  green_excess=p[:,:,1]-np.maximum(p[:,:,0],p[:,:,2]);chroma_alpha=np.round((1-np.clip((green_excess-12)/100,0,1))*255).astype('uint8');alpha=np.minimum(alpha,chroma_alpha)
 count,labels,stats,_=cv2.connectedComponentsWithStats((alpha>50).astype('uint8'),8)
 if count>1:
  largest=max(stats[1:,cv2.CC_STAT_AREA]);keep=np.zeros_like(alpha)
  for i in range(1,count):
   if stats[i,cv2.CC_STAT_AREA]>=max(25,largest*.003):keep[labels==i]=255
  keep=cv2.dilate(keep,np.ones((3,3),np.uint8));alpha=np.minimum(alpha,keep)
 edge=(alpha>0)&(alpha<250);weight=np.maximum(alpha.astype(np.float32)/255,.04);clean=(p-background[None,None,:]*(1-weight[:,:,None]))/weight[:,:,None];p=np.where(edge[:,:,None],np.clip(clean,0,255),p)
 silhouette=(alpha>24).astype('uint8');rim=(silhouette-cv2.erode(silhouette,np.ones((5,5),np.uint8)))>0;spill=rim&(p[:,:,1]>np.maximum(p[:,:,0],p[:,:,2])+4);p[:,:,1]=np.where(spill,np.maximum(p[:,:,0],p[:,:,2]),p[:,:,1])
 rgba=np.dstack([p.astype('uint8'),alpha]);rgba[alpha==0,:3]=0
 return rgba
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--input',required=True);ap.add_argument('--output',required=True);ap.add_argument('--id',required=True);ap.add_argument('--max-frames',type=int);ap.add_argument('--cycle',choices=['sweep','walk']);ap.add_argument('--version');args=ap.parse_args();source=Path(args.input);out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
 ffprobe=shutil.which('ffprobe');probe=json.loads(run([ffprobe,'-v','error','-show_streams','-show_format','-of','json',str(source)]));video=next(s for s in probe['streams'] if s['codec_type']=='video');duration=float(probe['format']['duration']);w,h=int(video['width']),int(video['height']);rate=video['avg_frame_rate'];audio=sum(s['codec_type']=='audio' for s in probe['streams'])
 # Keep the original in its private job directory. Review MP4 is a silent,
 # browser-compatible copy, so unexpected generated audio is never played.
 run([FFMPEG,'-y','-v','error','-i',str(source),'-map','0:v:0','-an','-c:v','libx264','-crf','18','-preset','fast','-pix_fmt','yuv420p','-movflags','+faststart',str(out/'green-screen.mp4')])
 preview_width=432;preview_height=round(h/w*preview_width/2)*2;fps=24
 process=subprocess.Popen([FFMPEG,'-v','error','-i',str(source),'-vf',f'fps={fps},scale={preview_width}:{preview_height}','-f','rawvideo','-pix_fmt','rgb24','pipe:1'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 size=preview_width*preview_height*3;frames=[];boxes=[];green=[]
 while True:
  raw=bytearray()
  while len(raw)<size:
   packet=process.stdout.read(size-len(raw))
   if not packet:break
   raw.extend(packet)
  if not raw:break
  if len(raw)!=size:raise RuntimeError('Incomplete decoded frame')
  rgb=np.frombuffer(raw,dtype='uint8').reshape(preview_height,preview_width,3);rgba=key_green(rgb);ys,xs=np.where(rgba[:,:,3]>100)
  if not len(xs):raise RuntimeError('Green key removed the entire actor; requires a revised candidate')
  boxes.append([int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]);green.append(float((rgba[:,:,3]==0).mean()));frames.append(rgba)
 error=process.stderr.read().decode('utf8',errors='replace');code=process.wait()
 if code:raise RuntimeError(error[-1600:])
 if len(frames)<24:raise RuntimeError('Actual decoded candidate is too short')
 source_count=len(frames);source_indices=list(range(source_count));cycle_selection=None;playback_fps=fps
 if args.max_frames:
  if args.max_frames<2:raise ValueError('A sequence needs at least two frames')
  features=[];fl=min(b[0] for b in boxes);ft=min(b[1] for b in boxes);fr=max(b[2] for b in boxes);fb=max(b[3] for b in boxes)
  for rgba in frames:
   reduced=cv2.resize(rgba[ft:fb,fl:fr],(54,96),interpolation=cv2.INTER_AREA).astype(np.float32)/255;reduced[:,:,:3]*=reduced[:,:,3:4];features.append(reduced.flatten())
  f=np.stack(features);norm=np.mean(f*f,axis=1);mse=np.maximum(0,norm[:,None]+norm[None,:]-2*(f@f.T)/f.shape[1]);candidates=[];min_length,max_length=(36,60) if args.cycle=='sweep' else (24,40)
  for start in range(16,min(90,source_count-min_length-12)):
   for length in range(min_length,min(max_length,source_count-start-8)+1):
    end=start+length;motion=float(np.max(mse[start,start:end]));seam=float(mse[start,end]);
    if motion<.001:continue
    candidates.append((seam/max(motion,.001)+abs(length-(48 if args.cycle=='sweep' else 31))*.0007,start,end,motion,seam))
  if not candidates:raise RuntimeError('No complete moving cycle found; do not manufacture a capped sequence from stills')
  _,start,end,motion,seam=min(candidates);count=min(args.max_frames,end-start);source_indices=[round(start+(end-start)*i/count) for i in range(count)]
  if len(set(source_indices))!=count:raise RuntimeError('Capped sequence contains duplicated source samples')
  frames=[frames[i] for i in source_indices];boxes=[boxes[i] for i in source_indices];green=[green[i] for i in source_indices];playback_fps=round(count/((end-start)/fps),6);cycle_selection={'startSourceFrame':start,'endSourceFrameExclusive':end,'sourceDuration':(end-start)/fps,'motionAmplitude':motion,'sourceSeamDifference':seam,'selection':'Closest matching active-cycle endpoints; evenly sampled without duplicated source frames.'}
 bounds=[max(0,min(b[0] for b in boxes)-8),max(0,min(b[1] for b in boxes)-8),min(preview_width,max(b[2] for b in boxes)+8),min(preview_height,max(b[3] for b in boxes)+8)];l,t,r,b=bounds
 cell_w,cell_h=320,480;scale=min((cell_w-28)/(r-l),(cell_h-32)/(b-t));target=(round((r-l)*scale),round((b-t)*scale));left=(cell_w-target[0])//2;top=cell_h-16-target[1];columns,rows=(5,4) if args.max_frames==20 else (6,4) if args.max_frames==24 else (8,4);per_sheet=columns*rows;sheets=[];normal=[];pngdir=out/'frames';pngdir.mkdir(exist_ok=True)
 for i,rgba in enumerate(frames):
  cell=Image.new('RGBA',(cell_w,cell_h));sprite=Image.fromarray(rgba[t:b,l:r]).resize(target,Image.Resampling.LANCZOS);cell.paste(sprite,(left,top));normal.append(cell);cell.save(pngdir/f'{i:04d}.png')
 for start in range(0,len(normal),per_sheet):
  atlas=Image.new('RGBA',(cell_w*columns,cell_h*rows))
  for j,im in enumerate(normal[start:start+per_sheet]):atlas.paste(im,((j%columns)*cell_w,(j//columns)*cell_h))
  name=f'atlas-{start//per_sheet:02d}.webp';atlas.save(out/name,lossless=True,exact=True,method=3);sheets.append(name)
  if args.max_frames:atlas.save(out/'sequence-sheet.png')
 normal[0].save(out/'poster.webp',lossless=True,exact=True,method=4);normal[-1].save(out/'last-frame.png');normal[len(normal)//2].save(out/'keyframe.png')
 contact=Image.new('RGB',(320*4,480*2),'#eee8df');dc=ImageDraw.Draw(contact)
 for j in range(8):
  index=min(len(normal)-1,round((len(normal)-1)*j/7));x=j%4*320;y=j//4*480;contact.paste(normal[index],(x,y),normal[index]);dc.text((x+10,y+8),f'{index/playback_fps:.2f}s / {index}',fill='#24312e')
 contact.save(out/'contact.jpg',quality=90)
 centers=[(b[0]+b[2])/2 for b in boxes];heights=[b[3]-b[1] for b in boxes];seam=float(np.abs(np.asarray(normal[0],dtype=float)-np.asarray(normal[-1],dtype=float)).mean());warnings=[]
 if min(green)<.35:warnings.append('绿幕背景占比偏低，需检查背景或抠像。')
 if max(centers)-min(centers)>preview_width*.13:warnings.append('人物水平漂移偏大，请重点核对原地动作。')
 if (max(heights)-min(heights))/max(1,np.median(heights))>.18:warnings.append('轮廓高度变化较大，请核对动作幅度和镜头比例。')
 if seam>16:warnings.append('首尾差异较大，可调整循环范围或退回重做。')
 if any(b[0]<=1 or b[1]<=1 or b[2]>=preview_width-1 or b[3]>=preview_height-1 for b in boxes):warnings.append('部分轮廓接近视频边界，需检查是否裁切。')
 if not args.max_frames:warnings.append('候选片的头身比、发型或服装细节与角色参考存在差异，请对照审核。')
 qa={'status':'needs-attention' if warnings else 'awaiting-human-review','warnings':warnings,'durationSeconds':duration,'sequenceDuration':len(normal)/playback_fps,'sourceResolution':[w,h],'sourceFPS':rate,'sourceCodec':video['codec_name'],'sourceAudioTracks':audio,'reviewAudioTracks':0,'decodedFrames':len(frames),'sourceDecodedFrames':source_count,'extractedFPS':playback_fps,'frameLimit':args.max_frames,'minimumTransparentBackground':min(green),'horizontalDriftPixels':max(centers)-min(centers),'loopSeamMeanDifference':seam,'notes':'Matte and timing metrics are automatic checks, not approval of motion quality.'}
 info={'id':args.id,'version':args.version or ('draft-v2' if args.max_frames else 'draft-v1'),'generator':'Seedance 2.5','count':len(normal),'fps':playback_fps,'width':cell_w,'height':cell_h,'columns':columns,'rows':rows,'framesPerSheet':per_sheet,'sheets':sheets,'cropBounds':bounds,'sourceDecodeResolution':[preview_width,preview_height],'framePattern':'frames/{index:04d}.png','sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'qa':qa}
 if args.max_frames:
  info.update(frameLimit=args.max_frames,sourceFrameIndices=source_indices,sourceTimes=[i/fps for i in source_indices],cycleSelection=cycle_selection)
  backgrounds=[]
  for im in normal:
   bg=Image.new('RGBA',im.size,'#eee9de');bg.alpha_composite(im);backgrounds.append(bg.convert('RGB'))
  backgrounds[0].save(out/'sequence-preview.gif',save_all=True,append_images=backgrounds[1:],duration=round(1000/playback_fps),loop=0,optimize=False)
 (out/'frames.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 with zipfile.ZipFile(out/'frames.zip','w',compression=zipfile.ZIP_DEFLATED,compresslevel=3) as z:
  z.write(out/'frames.json','frames.json')
  for p in pngdir.glob('*.png'):z.write(p,'frames/'+p.name)
 print(json.dumps({'id':args.id,'frames':len(normal),'fps':playback_fps,'qa':qa['status'],'warnings':warnings},ensure_ascii=False))
if __name__=='__main__':main()
