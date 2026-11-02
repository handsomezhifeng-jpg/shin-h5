"""Register repainted character textures back into unchanged Spine UV regions."""
from pathlib import Path
from PIL import Image
import json,re,hashlib
import cv2,numpy as np

ROOT=Path(__file__).resolve().parents[1];ASSETS=ROOT/'assets/construction';WORK=ROOT/'outputs/jiangdong-c-work';OUT=ASSETS/'skins/jiangdong-c'

def atlas_regions(text):
    regions=[];current=None
    for line in text.splitlines()[1:]:
        line=line.strip()
        if not line:continue
        if ':' not in line:
            if current:regions.append(current)
            current={'name':line}
        elif current:
            k,v=line.split(':',1)
            if k=='bounds':current[k]=list(map(int,v.split(',')))
            elif k=='rotate':current[k]=v
    if current:regions.append(current)
    return[r for r in regions if 'bounds'in r]

def register(old,generated,regions,role=None):
    p=np.asarray(old).copy();g=np.asarray(generated.resize(old.size,Image.Resampling.LANCZOS)).copy();ga=(g[:,:,3]>100).astype('uint8');output=np.zeros_like(p)
    opaque=g[g[:,:,3]>220,:3];dark=opaque[(opaque.mean(axis=1)>18)&(opaque.mean(axis=1)<75)];ink=np.median(dark,axis=0) if len(dark)else np.array([68,54,42]);records=[]
    for r in regions:
        x,y,w,h=r['bounds'];w,h=(h,w)if r.get('rotate') in ['90','true']else(w,h)
        if x+w>old.width or y+h>old.height:raise ValueError('Spine region outside original atlas '+r['name'])
        source=p[y:y+h,x:x+w];mask=(source[:,:,3]>100).astype('uint8')
        if not mask.any():continue
        margin=min(30,max(6,round(max(w,h)*.1)));l,t,rr,b=max(0,x-margin),max(0,y-margin),min(old.width,x+w+margin),min(old.height,y+h+margin)
        search=ga[t:b,l:rr];match=cv2.matchTemplate(search.astype('float32'),mask.astype('float32'),cv2.TM_CCOEFF_NORMED)
        yy,xx=np.indices(match.shape);penalty=((xx-(x-l))**2+(yy-(y-t))**2)/(max(10,margin)**2)*.025;score=match-penalty;_,best,_,pos=cv2.minMaxLoc(score);gx,gy=l+pos[0],t+pos[1];patch=g[gy:gy+h,gx:gx+w].copy()
        valid=patch[:,:,3]>80
        old_colors=source[:,:,:3][mask>0]
        garment=bool(re.search(r'^(dabi|hudiejie|piaodai|qun|shangyi|youxiu|zuoxiu|yifu|shenti|kuzi|miansha)',r['name'])) or (role in ['q_npc_1029','q_npc_1030'] and bool(re.search(r'^(body|xiabody|youdabi|zuodabi|yaodai|bingyoushoubi|chayoubi|chagebo|chaxiaobi|xiaobi)',r['name'])))
        if valid.any()and not valid.all():
            _,labels=cv2.distanceTransformWithLabels((~valid).astype('uint8'),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL);colors=patch[:,:,:3][valid];patch[:,:,:3]=colors[np.maximum(0,labels-1)]
        elif not valid.any():
            # Find the nearest generated paint in the local attachment vicinity.
            area=g[t:b,l:rr];colors=area[:,:,:3][area[:,:,3]>100]
            patch[:,:,:3]=np.median(colors,axis=0).astype('uint8')if len(colors)else np.round(ink).astype('uint8')
        original=source[:,:,:3].astype('float32');paint=patch[:,:,:3].astype('float32')
        if garment:
            # Transfer the generated cloth paint into the original UV surface.
            # Reuse the rig's lightness/edge registration; never move a sleeve
            # outline, mouth, pupil or hair strand to a nearby atlas island.
            base=cv2.GaussianBlur(paint,(0,0),max(2,min(w,h)*.075));luma=cv2.cvtColor(original,cv2.COLOR_RGB2GRAY);values=luma[mask>0];mid=max(35,float(np.median(values)));shade=np.clip(luma/mid,.56,1.18);rgb=base*shade[:,:,None]
            hsv=cv2.cvtColor(source[:,:,:3],cv2.COLOR_RGB2HSV);skin=(hsv[:,:,0]<25)&(hsv[:,:,1]<150)&(original[:,:,0]>original[:,:,1]*1.08)&(original[:,:,1]>original[:,:,2]*1.08)&(hsv[:,:,2]>80)&bool(re.search(r'^(dabi|.*shou)',r['name']))
            rgb[skin]=original[skin]
        else:
            # Facial UV masks encode the original expression and must keep
            # whites/pupils/eyelashes distinct. Only harmonize their pigment.
            src_mid=np.maximum(np.median(old_colors,axis=0),24);dst_colors=paint[(source[:,:,3]>100)&valid];dst_mid=np.median(dst_colors,axis=0)if len(dst_colors)else src_mid;ratio=np.clip(dst_mid/src_mid,.9,1.1);rgb=original*(.85+.15*ratio[None,None,:])
        patch[:,:,:3]=np.clip(rgb,0,255).astype('uint8');patch[:,:,3]=source[:,:,3];output[y:y+h,x:x+w]=patch;records.append({'name':r['name'],'sourceRect':[x,y,w,h],'generatedRect':[gx,gy,w,h],'alphaFit':round(float(best),4),'expressionMask':not garment,'materialTransfer':garment})
    return Image.fromarray(output),records

def main():
    manifest_path=OUT/'skin.json';previous=json.loads(manifest_path.read_text(encoding='utf8'));roles={name:r for name,r in previous.get('roles',{}).items()if r.get('imageURL')};report=[]
    for folder,file in [('scene-npcs','animations.json'),('portraits','npc-animations.json')]:
        data=json.loads((ASSETS/folder/file).read_text(encoding='utf8'))
        for name,profile in data['roles'].items():
            raw=WORK/'raw'/(name+'.png')
            if not raw.exists():continue
            atlas_path=ASSETS/folder/profile['atlasUrl'];text=atlas_path.read_text(encoding='utf8');page=text.splitlines()[0];original=atlas_path.parent/page;old=Image.open(original).convert('RGBA');new,regions=register(old,Image.open(raw).convert('RGBA'),atlas_regions(text),role=name);target=OUT/'roles'/name;target.mkdir(parents=True,exist_ok=True);new.save(target/page);(target/atlas_path.name).write_text(text,encoding='utf8');roles[name]={'atlasURL':'assets/construction/skins/jiangdong-c/roles/'+name+'/'+atlas_path.name,'textureURL':'assets/construction/skins/jiangdong-c/roles/'+name+'/'+page,'sourceAtlas':str(atlas_path.relative_to(ROOT)).replace('\\','/'),'regions':len(regions),'nativeSourceSize':list(Image.open(raw).size),'registeredSize':list(old.size)};report.append({'role':name,'regions':regions,'outputSha256':hashlib.sha256((target/page).read_bytes()).hexdigest()})
    manifest_path=OUT/'skin.json';manifest=json.loads(manifest_path.read_text(encoding='utf8'));manifest['roles']=roles;manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8');(WORK/'role-registration.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'roles':list(roles),'regions':sum(r.get('regions',0)for r in roles.values())}))

if __name__=='__main__':main()
