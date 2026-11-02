"""Package original generated RGBA atlases unchanged; record sprite bounds only."""
from pathlib import Path
from PIL import Image
import hashlib,json
import numpy as np
import cv2

root=Path(__file__).resolve().parents[1]
out=root/'assets/scene/skins/ink'
generated=Path('C:/Users/zhfzhang/.codex/generated_images/01a19545-c6bc-7aa1-adaf-03ca5af4272e')
sources=[('sweeper',4,2,'exec-f839fe94-7e27-4dda-b3de-468db89ea883.png'),('customers',6,3,'exec-356ab6dc-32b8-4144-8e86-d3e1505f3195.png'),('vendors',3,4,'exec-3ad505f6-7359-4785-8881-2bb0ad1f8629.png')]
manifest={'version':4,'generator':'built-in image_gen','reference':'source-master.png','atlases':{},'animation':'src/ink-resident-rules.mjs','notes':'RGBA pixels retained exactly. Connected regions supply atlas coordinates only; no generated pixels repainted or removed.'}
for name,cols,rows,file in sources:
 source=generated/file
 im=Image.open(source).convert('RGBA');pixels=np.array(im);alpha=pixels[:,:,3]
 count,labels,stats,centroids=cv2.connectedComponentsWithStats((alpha>120).astype('uint8'),8)
 groups=[[] for _ in range(cols*rows)]
 for i in range(1,count):
  if stats[i,cv2.CC_STAT_AREA]<40:continue
  cx,cy=centroids[i];col=min(cols-1,int(cx/im.width*cols));row=min(rows-1,int(cy/im.height*rows));groups[row*cols+col].append(i)
 frames=[]
 for index,parts in enumerate(groups):
  if not parts:raise ValueError(f'Empty frame {name}:{index}')
  xs=[];ys=[]
  for i in parts:
   x,y,w,h,area=stats[i];xs.extend([int(x),int(x+w)]);ys.extend([int(y),int(y+h)])
  left=max(0,min(xs)-3);right=min(im.width,max(xs)+3);top=max(0,min(ys)-3);bottom=min(im.height,max(ys)+3)
  region=pixels[top:bottom,left:right];mask=region[:,:,3]>160
  if name=='vendors':
   foot=mask.copy();foot[:int(len(foot)*.86)]=False
  else:
   foot=mask&(region[:,:,:3].mean(axis=2)<110);foot[:int(len(foot)*.82)]=False
  fy,fx=np.where(foot)
  anchor_x=float((int(fx.min())+int(fx.max()))/2) if len(fx) else (right-left)/2
  anchor_y=int(fy.max())+1 if len(fy) else bottom-top-3
  frames.append({'crop':[left,top,right-left,bottom-top],'anchor':[anchor_x,anchor_y],'bodyHeight':anchor_y-3,'row':index//cols,'column':index%cols})
 target=out/f'residents-{name}-v4.webp'
 im.save(target,lossless=True,exact=True,method=6)
 if Image.open(target).convert('RGBA').tobytes()!=im.tobytes():raise ValueError('Lossless encoding changed RGBA')
 manifest['atlases'][name]={'url':target.name,'size':list(im.size),'columns':cols,'rows':rows,'frames':frames,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'sourceGeneration':file,'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'transparentFraction':float((alpha==0).mean())}
text=json.dumps(manifest,ensure_ascii=False,indent=2)+'\n'
(out/'residents-v4.json').write_text(text,encoding='utf8')
print(json.dumps({name:len(record['frames']) for name,record in manifest['atlases'].items()}))
