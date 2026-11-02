"""User-authorized extraction from the selected original painting; no new artwork."""
from pathlib import Path
from PIL import Image,ImageDraw
import json
import cv2
import numpy as np

root=Path(__file__).resolve().parents[1]
out=root/'assets/scene/skins/ink'
source=Image.open(out/'source-master.png').convert('RGBA')
# Exact original visible silhouettes, including counter occlusion for sellers.
people=[
 ('sweeper',True,[329,320],[329,320],[(312,207),(324,207),(334,213),(334,226),(344,235),(349,248),(347,261),(344,267),(352,276),(355,302),(349,312),(343,319),(329,321),(321,316),(310,319),(303,315),(302,302),(301,287),(297,287),(297,297),(293,310),(285,319),(273,320),(272,312),(282,299),(289,294),(291,283),(295,279),(301,276),(300,269),(294,259),(293,248),(297,237),(306,227),(305,218)]),
 ('produce-seller',False,[125,612],[75,532],[(119,544),(133,543),(143,549),(149,561),(148,577),(144,587),(148,593),(146,600),(137,600),(132,593),(126,594),(123,600),(116,604),(109,604),(103,598),(100,588),(102,577),(101,565),(107,552)]),
 ('produce-customer',True,[172,662],[122,582],[(172,552),(181,550),(190,555),(193,565),(192,573),(201,580),(205,595),(202,608),(196,615),(197,630),(201,644),(197,653),(187,657),(181,662),(169,663),(159,657),(153,655),(151,647),(152,634),(150,620),(143,616),(138,607),(140,598),(145,595),(143,587),(144,574),(153,563),(166,560)]),
 ('tea-seller',False,[854,450],[854,450],[(841,372),(854,368),(867,369),(878,377),(881,389),(878,404),(873,413),(879,418),(887,430),(888,443),(883,450),(875,453),(866,448),(862,442),(849,442),(843,438),(838,439),(828,434),(821,433),(819,425),(825,416),(832,413),(829,404),(829,390),(832,379)]),
 ('tea-blue-customer',True,[785,519],[785,519],[(769,416),(778,414),(786,418),(789,426),(788,433),(798,438),(808,449),(813,460),(810,473),(805,479),(805,490),(810,502),(807,511),(796,516),(786,519),(774,516),(768,513),(765,506),(766,494),(768,481),(766,477),(759,468),(754,461),(753,449),(757,437),(766,432),(765,424)]),
 ('tea-red-customer',True,[854,556],[854,556],[(839,461),(854,460),(867,465),(874,474),(879,489),(877,501),(871,508),(877,510),(882,519),(879,528),(875,532),(876,542),(872,550),(860,554),(851,557),(841,553),(835,550),(831,541),(832,530),(830,522),(825,517),(823,506),(820,495),(823,479),(831,469)]),
 ('cloth-seller',False,[230,1204],[230,1204],[(218,1130),(233,1127),(245,1131),(256,1140),(261,1152),(257,1169),(250,1177),(253,1183),(259,1189),(253,1197),(242,1199),(234,1203),(224,1200),(217,1204),(208,1198),(203,1190),(204,1181),(210,1175),(204,1166),(202,1156),(206,1142)]),
 ('cloth-customer',True,[329,1268],[329,1268],[(328,1148),(341,1149),(348,1156),(348,1166),(358,1173),(364,1186),(361,1201),(355,1211),(359,1227),(363,1246),(359,1256),(348,1261),(341,1264),(328,1269),(318,1267),(310,1261),(307,1253),(310,1239),(311,1228),(304,1224),(298,1213),(298,1203),(305,1202),(312,1208),(316,1203),(309,1196),(306,1182),(309,1168),(318,1160),(321,1153)]),
 ('grain-seller',False,[861,1075],[861,1075],[(850,999),(862,998),(878,1003),(895,1014),(908,1026),(900,1031),(884,1031),(884,1042),(890,1051),(893,1064),(886,1075),(875,1077),(868,1069),(864,1063),(857,1061),(850,1067),(842,1065),(840,1053),(831,1045),(831,1033),(819,1031),(817,1027),(827,1015),(840,1006)])
]
atlas=Image.new('RGBA',(480,540),(0,0,0,0));records=[]
for i,(name,standing,foot,destination,polygon) in enumerate(people):
 left=max(0,min(x for x,y in polygon)-6);top=max(0,min(y for x,y in polygon)-6)
 right=min(source.width,max(x for x,y in polygon)+7);bottom=min(source.height,max(y for x,y in polygon)+7)
 width,height=right-left,bottom-top
 mask=Image.new('L',(width*4,height*4));ImageDraw.Draw(mask).polygon([((x-left)*4,(y-top)*4) for x,y in polygon],fill=255)
 mask=mask.resize((width,height),Image.Resampling.LANCZOS)
 image=source.crop((left,top,right,bottom))
 # Refine the authorized source cutout along actual painted outlines. The
 # polygon supplies foreground/background seeds, not rectangular pasted edges.
 region=np.array(mask)>127
 seed=cv2.erode(region.astype('uint8'),np.ones((9,9),np.uint8))
 expanded=cv2.dilate(region.astype('uint8'),np.ones((5,5),np.uint8))
 labels=np.where(expanded,cv2.GC_PR_FGD,cv2.GC_BGD).astype('uint8')
 labels[seed>0]=cv2.GC_FGD
 cv2.grabCut(np.array(image.convert('RGB')),labels,None,np.zeros((1,65)),np.zeros((1,65)),5,cv2.GC_INIT_WITH_MASK)
 selected=((labels==cv2.GC_FGD)|(labels==cv2.GC_PR_FGD)).astype('uint8')
 count,components,stats,_=cv2.connectedComponentsWithStats(selected,8)
 if count>1:
  main=1+np.argmax(stats[1:,cv2.CC_STAT_AREA]);selected=(components==main).astype('uint8')
 mask=Image.fromarray(selected*255)
 if name=='sweeper':
  ImageDraw.Draw(mask).polygon([(x-left,y-top) for x,y in [(291,282),(299,285),(295,298),(291,311),(285,319),(273,320),(272,312),(282,300),(288,294)]],fill=255)
 image.putalpha(mask)
 x=(i%3)*160;y=(i//3)*180;atlas.paste(image,(x,y))
 records.append({'id':name,'standing':standing,'crop':[x,y,width,height],'anchor':[foot[0]-left,foot[1]-top],'sourceBodyHeight':foot[1]-top-image.getbbox()[1] if standing else 114,'destination':destination,'originalFoot':foot,'sourcePolygon':polygon})
atlas.save(out/'villagers-v3.webp',lossless=True,exact=True,method=6)
assert Image.open(out/'villagers-v3.webp').convert('RGBA').tobytes()==atlas.tobytes()
(out/'villagers-v3.json').write_text(json.dumps({'source':'source-master.png','characters':records},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
atlas.save(root/'outputs/villagers-extracted.png')
print('Extracted nine original villagers into an RGBA atlas.')
