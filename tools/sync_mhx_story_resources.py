"""Reproduce the source-matched CG/BG/Spine/audio dependency cache from the original public catalog."""
from pathlib import Path
import argparse,json
from mhx_public_resources import PublicBundleSource,DEFAULT_APK,ANALYSIS

ROOT=Path(__file__).resolve().parents[1]
EXPECTED_MANIFEST_SHA256='37ef8886b6d0cbdc2d860d16f00158e52cab9e7e06a6be5eb55bc75811d8f3d6'
SOUND_IDS={1,20,21,22,27,74,75,76,77,110,111}

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--download',action='store_true')
 parser.add_argument('--apk',type=Path,default=DEFAULT_APK)
 parser.add_argument('--cache',type=Path,default=ANALYSIS)
 args=parser.parse_args();source=PublicBundleSource(args.apk,'1.4.93.1',args.cache/'downloaded',args.cache)
 if source.catalog['sha256']!=EXPECTED_MANIFEST_SHA256:raise ValueError('Source catalog differs from the verified APK-matched manifest')
 config=ROOT/'assets/construction/config/Data';targets=[]
 for table,field in [('PlotCGVo','cgPath'),('PlotBGVo','bgPath')]:
  for row in json.loads((config/'Plot'/(table+'.json')).read_text('utf8'))['rows']:
   name=str(row[field]).split(':')[-1]
   matches=[asset['path']for asset in source.catalog['assets']if asset['path'].lower().endswith('/'+name.lower()+'.png')]
   if len(matches)>1:raise ValueError('Original image reference is ambiguous: '+name)
   targets.append(matches[0]if matches else'Assets/BundleResources/Arts/Textures/Cg/'+name+'.png')
 targets.append('Assets/BundleResources/Spines/FXPrefab/slap.prefab')
 for row in json.loads((config/'Common/SoundPathVo.json').read_text('utf8'))['rows']:
  if row['id']in SOUND_IDS:targets.append('Assets/BundleResources/'+row['soundPath'])
 records=[]
 for path in dict.fromkeys(targets):
  item={'path':path.removeprefix('Assets/BundleResources/')}
  try:
   asset=source.asset(path)
   item['bundleIds']=source.closure(asset)
   if args.download:item['sources']=source.ensure_asset(path)
  except KeyError:item['error']='Original asset absent from the source-matched catalog'
  records.append(item)
 report={'version':source.version,'manifestSha256':source.catalog['sha256'],'downloaded':args.download,'assets':records}
 if args.download:(args.cache/'story-cdn-assets.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(json.dumps({'version':source.version,'targets':len(records),'available':sum('error'not in item for item in records),'absent':[item['path']for item in records if'error'in item],'downloaded':args.download}))

if __name__=='__main__':main()
