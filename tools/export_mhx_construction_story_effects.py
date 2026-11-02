"""Extract source-matched CG/BG/audio/Spine and ColorOverlay shader/settings, without substitute art."""
from pathlib import Path
import hashlib,json,struct,zipfile,subprocess,tempfile
import UnityPy
from UnityPy.helpers import TypeTreeHelper
from UnityPy.helpers.CompressionHelper import decompress_lz4
from UnityPy.export.ShaderConverter import ShaderProgram
from UnityPy.streams import EndianBinaryReader
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'assets/construction';IMAGES=OUT/'images-story-effects';SHADERS=OUT/'shaders-story'
IMAGES.mkdir(exist_ok=True);SHADERS.mkdir(exist_ok=True)
index=json.loads(Path(r'C:\dev\mhxcz-analysis\scene-bundle-index.json').read_text(encoding='utf8'))
cdn_file=Path(r'C:\dev\mhxcz-analysis\story-cdn-assets.json')
cdn=json.loads(cdn_file.read_text(encoding='utf8'))if cdn_file.exists()else None
if cdn:
 if cdn['version']!='1.4.93.1':raise ValueError('Do not mix source APK and newer resource catalogs')
 for item in cdn['assets']:
  if item.get('sources'):index.append({'source':item['sources'][-1],'containers':['Assets/BundleResources/'+item['path']]})
archive=zipfile.ZipFile(r'C:\Users\zhfzhang\Downloads\梦幻消除战.apk')
digest=lambda b:hashlib.sha256(b).hexdigest()
metadata={'source':'Original APK and its matching 1.4.93.1 public resource catalog: CG/BG/audio/Spine, globalgamemanagers ColorOverlayFeature and Custom/ColorOverlay GLES shader','cg':{},'bg':{},'sounds':{},'fx':{},'memory':{},'sources':[]}
if cdn:metadata['catalog']={'version':cdn['version'],'sha256':cdn['manifestSha256'],'source':'Original public endpoints read from APK UpdateSetting; files verified against the APK-matched catalog MD5 and size; no URLs or credentials serialized'}
for kind,table,field in [('cg','PlotCGVo','cgPath'),('bg','PlotBGVo','bgPath')]:
 for row in json.loads((OUT/('config/Data/Plot/'+table+'.json')).read_text(encoding='utf8'))['rows']:
  cg_id=row['id'];name=str(row[field]).split(':')[-1]
  entry=next((row for row in index if any(path.lower().endswith('/'+name.lower()+'.png')for path in row['containers'])),None)
  if entry is None:
   metadata[kind][str(cg_id)]={field:row[field],'available':False,'sourceWarning':'Original referenced image is absent from the indexed APK/download bundles. Native RawImageAlterable waits for OnFinish; load failure does not invoke that callback, so preflight must block before charging.'}
   continue
  source=entry['source'];raw=archive.read(source[4:])if source.startswith('apk:')else Path(source).read_bytes();env=UnityPy.load(raw)
  obj=next(obj for obj in env.objects if obj.type.name=='Texture2D'and obj.peek_name()==name)
  tex=obj.read();target=IMAGES/(name+'.png');tex.image.save(target)
  metadata[kind][str(cg_id)]={field:row[field],'available':True,'url':'images-story-effects/'+target.name,'width':tex.m_Width,'height':tex.m_Height,'sha256':digest(target.read_bytes()),'source':source,'sourceObject':obj.assets_file.name+':'+str(obj.path_id),'sourceSha256':digest(raw)}
audio_dir=OUT/'audio-story';audio_dir.mkdir(exist_ok=True)
ffmpeg=Path(r'D:\bark2\bark-with-voice-clone\Retrieval-based-Voice-Conversion-WebUI\ffmpeg.exe')
for row in json.loads((OUT/'config/Data/Common/SoundPathVo.json').read_text(encoding='utf8'))['rows']:
 if row['id']not in [1,20,21,22,27,74,75,76,77,110,111]:continue
 entry=next((entry for entry in index if any(path.lower().endswith('/'+row['soundPath'].lower())for path in entry['containers'])),None)
 if not entry:metadata['sounds'][str(row['id'])]={**row,'available':False};continue
 source=entry['source'];raw=archive.read(source[4:])if source.startswith('apk:')else Path(source).read_bytes();env=UnityPy.load(raw)
 obj=next(obj for obj in env.objects if obj.type.name=='AudioClip');clip=obj.read();sample_name,pcm=next(iter(clip.samples.items()));extension='.flac'if ffmpeg.exists()else'.wav';target=audio_dir/(clip.m_Name+extension)
 if extension=='.flac':
  result=subprocess.run([str(ffmpeg),'-hide_banner','-loglevel','error','-f','wav','-i','pipe:0','-c:a','flac','-compression_level','8','-y',str(target)],input=pcm,capture_output=True)
  if result.returncode:raise RuntimeError('lossless source audio export failed: '+result.stderr.decode('utf8','replace')[:200])
 else:target.write_bytes(pcm)
 metadata['sounds'][str(row['id'])]={'id':row['id'],'soundPath':row['soundPath'],'soundType':row['soundType'],'available':True,'url':'audio-story/'+target.name,'duration':clip.m_Length,'channels':clip.m_Channels,'frequency':clip.m_Frequency,'sha256':digest(target.read_bytes()),'decodedWavSha256':digest(pcm),'encoding':'lossless FLAC of original decoded Unity AudioClip PCM'if extension=='.flac'else'original decoded Unity AudioClip PCM','source':source,'sourceSha256':digest(raw)}
env=UnityPy.Environment()
for stem in ['globalgamemanagers.assets','sharedassets0.assets','Resources/unity_builtin_extra']:
 names=sorted(n for n in archive.namelist()if n=='assets/bin/Data/'+stem or n.startswith('assets/bin/Data/'+stem+'.split'))
 if names:
  raw=b''.join(archive.read(name)for name in names);env.load_file(raw,name=Path(stem).name)
  if stem=='globalgamemanagers.assets':metadata['sources'].append({'source':names,'sha256':digest(raw)})
for obj in env.objects:
 if obj.type.name=='MonoBehaviour':
  raw=obj.get_raw_data()
  if len(raw)<32:continue
  length=struct.unpack_from('<I',raw,28)[0]
  if raw[32:32+length]!=b'ColorOverlayFeature':continue
  offset=(32+length+3)&~3
  # Serialized ScriptableRendererFeature.m_Active precedes inline ColorOverlayParameters.
  color=struct.unpack_from('<4f',raw,offset+4);intensity,desaturation=struct.unpack_from('<2f',raw,offset+20)
  metadata['memory'].update({'overlayColor':color,'intensity':intensity,'desaturation':desaturation,'luminance':[.298999995,.587000012,.114],'sourceObject':obj.assets_file.name+':'+str(obj.path_id),'serializedBytesSha256':digest(raw),'serializedOffsets':{'active':offset,'overlayColor':offset+4,'intensity':offset+20,'desaturation':offset+24},'formula':'gray=dot(rgb,luminance); desaturated=mix(rgb,gray,desaturation); out=mix(desaturated,desaturated*overlayColor.rgb,intensity); alpha unchanged','cameraEvidence':'ColorOverlayFeature.AddRenderPasses requires the rendering camera ColorOverlaySettings.enableColorOverlay; PlotDialogue.PlotUICamera carries it','browserColorSpace':'sRGB DOM framebuffer; exact recovered shader coefficients; Unity render-target transfer is not independently reproduced'})
 if obj.type.name=='Shader':
  tree=obj.read_typetree();name=tree.get('m_ParsedForm',{}).get('m_Name')
  if name!='Custom/ColorOverlay':continue
  metadata['memory']['shaderSourceObject']=obj.assets_file.name+':'+str(obj.path_id)
  for i,platform in enumerate(tree['platforms']):
   for offset,compressed,decompressed in zip(tree['offsets'][i],tree['compressedLengths'][i],tree['decompressedLengths'][i]):
    raw=decompress_lz4(bytes(tree['compressedBlob'][offset:offset+compressed]),decompressed)
    program=ShaderProgram(EndianBinaryReader(raw,endian='<'),obj.version)
    for sub in program.m_SubPrograms:
     code=bytes(sub.m_ProgramCode);start=code.find(b'#ifdef VERTEX')
     if start<0:continue
     code=code[start:].split(b'\0',1)[0]
     if b'_Desaturation'not in code:continue
     target=SHADERS/'ColorOverlay.glsl';target.write_bytes(code);metadata['memory'].update({'shaderUrl':'shaders-story/ColorOverlay.glsl','shaderSha256':digest(code),'platform':platform})
if not metadata['memory'].get('shaderSha256')or not metadata['memory'].get('overlayColor'):raise RuntimeError('Original ColorOverlay shader/settings were not recovered')
lua=Path(r'C:\dev\mhxcz-analysis\construction-lua')
metadata['luaEvidence']=[{'module':name,'sha256':digest((lua/name).read_bytes())}for name in ['Game/Plot/Effect/Scripts/CG.lua','Game/Plot/Effect/Scripts/Memory.lua','Game/Plot/Effect/Scripts/SpineFx.lua','Game/Plot/Effect/Scripts/BlackFadeOut.lua','Game/Plot/Effect/Scripts/BlackFadeIn.lua','Game/Res/ResUtil.lua']]
fx_table=json.loads((OUT/'config/Data/Plot/DialogueFxVo.json').read_text(encoding='utf8'))['rows']
for row in fx_table:
 metadata['fx'][str(row['id'])]={**row,'available':False,'sourceWarning':'Referenced Spine prefab is absent from the indexed APK/download bundles. ResUtil.AsyncLoadGameObject returns on missing resource; original SpineFx then waits fxDuration and deletes its null object. No replacement animation is rendered.','searchedBundles':len(index)}
slap=next((item for item in(cdn or{}).get('assets',[])if item['path']=='Spines/FXPrefab/slap.prefab'and item.get('sources')),None)
if slap:
 fx_dir=OUT/'story-fx';fx_dir.mkdir(exist_ok=True);env=UnityPy.Environment()
 for source in slap['sources']:env.load_file(archive.read(source[4:])if source.startswith('apk:')else Path(source).read_bytes(),name=source)
 for obj in env.objects:
  if obj.type.name=='TextAsset'and obj.peek_name()in ['hit.skel','hit.atlas']:
   asset=obj.read();raw=asset.m_Script.encode('utf8','surrogateescape')if isinstance(asset.m_Script,str)else bytes(asset.m_Script);(fx_dir/asset.m_Name).write_bytes(raw)
  if obj.type.name=='Texture2D'and obj.peek_name()=='hit':obj.read().image.save(fx_dir/'hit.png')
  if obj.type.name=='MonoBehaviour':
   tree=obj.read_typetree()
   if tree.get('m_Name')=='hit_SkeletonData':metadata['fx']['1']['skeletonData']={'scale':tree['scale'],'defaultMix':tree['defaultMix']}
 metadata['fx']['1'].update({'available':True,'binaryUrl':'story-fx/hit.skel','atlasUrl':'story-fx/hit.atlas','animation':'animation','loop':False,'timeScale':1,'background':{'color':[0,0,0,0],'fadeIn':.1,'fadeOutDelay':.3,'fadeOut':.1,'easing':'linear'},'sourcePath':'Spines/FXPrefab/slap.prefab','sources':slap['sources'],'files':{name:digest((fx_dir/name).read_bytes())for name in ['hit.skel','hit.atlas','hit.png']}})
 metadata['fx']['1'].pop('sourceWarning',None)
 profile_file=fx_dir/'hit-profile.json'
 if profile_file.exists():metadata['fx']['1']['profile']=json.loads(profile_file.read_text(encoding='utf8'))
metadata['cgRules']={'openFadeSeconds':.5,'openWaitSeconds':1,'closeFadeSeconds':.5,'closeWaitSeconds':.5,'nativeSize':True,'sourceScale':[2,2],'sourcePosition':[0,195]}
metadata['bgmRules']={'fadeOutSeconds':1,'fadeInSeconds':1,'targetVolume':1,'defaultBgmId':1,'source':'GameUtils.CrossFadeBgMusic and PlayBgMusicWithFadeIn/Out; same refId is not restarted'}
metadata['failureEvidence']={'image':'ResourceExtComponent.OnLoadAssetFailure 0x319ba74 only removes the request and logs; RawImageAlterable OnFinish is not invoked. CG/BG source waits on that callback.','prefab':'ResUtil.AsyncLoadGameObject returns when missing; SpineFx still waits fxDuration.'}
(OUT/'story-effects.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({'cg':len([v for v in metadata['cg'].values()if v.get('available')]),'missingCG':[key for key,value in metadata['cg'].items()if not value.get('available')],'bg':len(metadata['bg']),'sounds':len(metadata['sounds']),'memory':metadata['memory']['overlayColor'],'fxAvailable':bool(metadata['fx']['1']['available'])}))
