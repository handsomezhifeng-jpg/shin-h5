"""Pack generated RGBA poses; keep original colors and use alpha for extraction/QA."""
from pathlib import Path
import json, shutil
import numpy as np
import cv2
from PIL import Image, ImageDraw

root = Path(__file__).resolve().parents[1]
evidence = root.parent / '经验/知识库/美术方案/三国棋盘/张宁手机角色入版-2026-11-02'
evidence.mkdir(parents=True, exist_ok=True)
config = json.loads((root.parent/'经验/outputs/zhangning-mobile-input.json').read_text(encoding='utf-8'))
out = root/'assets/scene/skins/zhangning'
out.mkdir(parents=True, exist_ok=True)
manifest = {'character':'张宁','default':'a','variants':{},'authoredPoses':4,'referenceHeight':133}
flip = {'a':[True,False,True,False], 'b':[False,True,False,True], 'c':[True,True,True,True]}
proof = Image.new('RGB',(900,680),'#faf6eb')
pen = ImageDraw.Draw(proof)
for row,(key,info) in enumerate(config.items()):
    im=Image.open(info['generatedSource']).convert('RGBA')
    assert im.size==(1536,1024)
    shutil.copy2(info['generatedSource'],evidence/(key+'-generated.png'))
    sheet=Image.new('RGBA',(1024,1024))
    frames=[]
    for i in range(4):
        cell=im.crop(((i%2)*768,(i//2)*512,(i%2+1)*768,(i//2+1)*512))
        a=np.array(cell.getchannel('A'))
        count,labels,stats,_=cv2.connectedComponentsWithStats((a>=190).astype('uint8'),8)
        assert count>1, 'No opaque character body'
        component=1+np.argmax(stats[1:,cv2.CC_STAT_AREA])
        mask=cv2.dilate((labels==component).astype('uint8'),np.ones((5,5),'uint8'))
        rgba=np.array(cell);rgba[:,:,3]*=mask
        cell=Image.fromarray(rgba)
        box=cell.getbbox();assert box and box[0]>0 and box[1]>0 and box[2]<768 and box[3]<512, (key,i,box)
        body=cell.crop(box)
        if flip[key][i]:body=body.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        body=body.resize((round(body.width*440/body.height),440),Image.Resampling.LANCZOS)
        foot=np.array(body.getchannel('A'))[round(body.height*.84):]>=190
        fy,fx=np.where(foot);assert len(fx)
        foot_center=round((int(fx.min())+int(fx.max()))/2)
        frame=Image.new('RGBA',(512,512));frame.alpha_composite(body,(256-foot_center,40))
        sheet.alpha_composite(frame,((i%2)*512,(i//2)*512))
        frames.append({'crop':[(i%2)*512,(i//2)*512,512,512],'anchor':[256,480],'bodyHeight':440,'pose':['idle_f','idle_b','walk_f','walk_b'][i]})
        frame.save(evidence/f'{key}-{frames[-1]["pose"]}.png')
        if i==0:
            for x,h in [(40,54),(140,80),(260,120)]:
                small=body.resize((round(body.width*h/440),h),Image.Resampling.LANCZOS)
                proof.paste(small,(x,row*220+65),small)
                pen.text((x,row*220+190),str(h)+'px',fill='#302d25')
            bw=body.resize((round(body.width*100/440),100),Image.Resampling.LANCZOS)
            alpha=bw.getchannel('A').point(lambda a:255 if a>=128 else 0)
            pure=Image.new('RGB',bw.size,'black');white=Image.new('RGB',bw.size,'white');white.paste(pure,(0,0),alpha)
            proof.paste(white,(430,row*220+65));pen.text((430,row*220+190),'100px silhouette',fill='#302d25')
            head=body.crop((0,0,body.width,min(body.height,round(body.width*.92))))
            avatar=Image.new('RGBA',(160,160),'#dae5da');head.thumbnail((150,150),Image.Resampling.LANCZOS);avatar.alpha_composite(head,((160-head.width)//2,0))
            proof.paste(avatar,(650,row*220+25),avatar);avatar.save(out/f'{key}-portrait.png')
            pen.text((10,row*220+15),key.upper(),fill='#302d25')
    sheet.save(out/f'{key}.webp',lossless=True,method=6,exact=True)
    assert Image.open(out/f'{key}.webp').convert('RGBA').tobytes()==sheet.tobytes()
    manifest['variants'][key]={'name':info['name'],'atlas':f'{key}.webp','portrait':f'{key}-portrait.png','frames':frames,'sourceFlips':flip[key]}
(out/'variants.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(evidence/'prompts.json').write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
proof.save(evidence/'手机尺寸与剪影.png')
print(json.dumps({'variants':3,'authoredPosesPerVariant':4,'atlases':[1024,1024],'alphaExtraction':True,'sizes':[54,80,120],'silhouetteHeight':100}))
