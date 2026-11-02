"""Slice generated RGBA sheets into source-sized runtime assets; keep originals."""
from pathlib import Path
from PIL import Image
import argparse, hashlib, json
import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'outputs/jiangdong-c-work'
OUT=ROOT/'assets/construction/skins/jiangdong-c'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def isolated_cell(sheet, index, cols, rows, single=False):
    w,h=sheet.size
    im=sheet if single else sheet.crop((round(index%cols*w/cols),round(index//cols*h/rows),round((index%cols+1)*w/cols),round((index//cols+1)*h/rows)))
    p=np.asarray(im).copy();a=p[:,:,3]
    count,labels,stats,_=cv2.connectedComponentsWithStats((a>80).astype('uint8'),8)
    keep=np.zeros_like(a,dtype=bool)
    for n in range(1,count):
        if stats[n,cv2.CC_STAT_AREA]>=max(12,im.width*im.height*.00008):keep[labels==n]=True
    if not keep.any():raise ValueError(f'Empty generated cell {index}')
    expanded=cv2.dilate(keep.astype('uint8'),np.ones((5,5),np.uint8))>0
    p[:,:,3]=np.where(expanded,a,0)
    y,x=np.where(keep);box=(max(0,int(x.min())-2),max(0,int(y.min())-2),min(im.width,int(x.max())+3),min(im.height,int(y.max())+3))
    return Image.fromarray(p).crop(box),box


def surface_pixels(im, source):
    # Tile alpha is geometry, not a paint color. Retain that registered footprint.
    p=np.asarray(im.resize(source.size,Image.Resampling.LANCZOS)).copy()
    valid=(p[:,:,3]>160).astype('uint8')
    if valid.any():
        _,labels=cv2.distanceTransformWithLabels(1-valid,cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL)
        colors=p[:,:,:3][valid>0]
        p[:,:,:3]=colors[np.maximum(0,labels-1)]
    p[:,:,3]=np.asarray(source)[:,:,3]
    return Image.fromarray(p)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--enable',action='store_true');args=ap.parse_args()
    plan=json.loads((WORK/'plan.json').read_text(encoding='utf8'))
    (OUT/'sprites').mkdir(parents=True,exist_ok=True)
    previous=json.loads((OUT/'skin.json').read_text(encoding='utf8')) if (OUT/'skin.json').exists() else {}
    records={};files=dict(previous.get('files',{}));groups=[];missing=[]
    for g in plan['groups']:
        raw=WORK/'raw'/f"{g['id']}.png"
        if not raw.exists() or not raw.with_suffix('.json').exists():missing.append(g['id']);continue
        sheet=Image.open(raw).convert('RGBA')
        for c in g['cells']:
            old=Image.open(ROOT/'assets/construction'/c['source']).convert('RGBA')
            clean_floors=['e5abd22bcce6','b26113fd382c','c4eaa9d34e78']
            paint_raw=raw
            if c['spriteId'] in clean_floors:
                paint_raw=WORK/'raw/hall-floors-clean.png'
                if not paint_raw.with_suffix('.json').exists():raise ValueError('Missing clean hall floor provenance')
                im,box=isolated_cell(Image.open(paint_raw).convert('RGBA'),clean_floors.index(c['spriteId']),3,1)
            else:im,box=isolated_cell(sheet,c['index'],g['columns'],g['rows'],len(g['cells'])==1)
            surface=g['id']=='core-floors' or g['id'].startswith('tiles-')
            if surface:result=surface_pixels(im,old)
            else:result=im.resize(old.size,Image.Resampling.LANCZOS)
            target=OUT/'sprites'/f"{c['spriteId']}.webp"
            result.save(target,lossless=True,exact=True,method=5)
            record={'id':c['spriteId'],'name':c['name'],'url':f"skins/jiangdong-c/sprites/{c['spriteId']}.webp",'sourceURL':c['source'],'size':list(result.size),'group':g['id'],'sheetCell':clean_floors.index(c['spriteId']) if c['spriteId'] in clean_floors else c['index'],'sheetCrop':list(box),'sha256':sha(target),'generatedSheetSha256':sha(paint_raw),'generatedSheet':paint_raw.name,'sourceSha256':sha(ROOT/'assets/construction'/c['source']),'technicalAlphaRetained':surface}
            records[c['spriteId']]=record
            files['assets/construction/'+c['source']]='assets/construction/'+record['url']
        groups.append({'id':g['id'],'cells':len(g['cells']),'nativeSize':list(sheet.size),'sha256':sha(raw)})
    manifest={**previous,'id':'jiangdong-c','title':'江东清雅 · 三国酒楼','version':1,'enabled':args.enable and not missing,'generator':'built-in image_gen','sprites':records,'files':files,'groups':groups,'pendingGroups':missing,'technicalRetained':plan['technicalRetained'],'sourceSceneSpriteCount':plan['sourceSceneSprites'],'generatedSceneSprites':len(records)}
    (OUT/'skin.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'generatedSceneSprites':len(records),'groups':len(groups),'pending':missing,'enabled':manifest['enabled']}))


if __name__=='__main__':main()
