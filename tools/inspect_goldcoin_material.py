from pathlib import Path
import json
from PIL import Image,ImageChops,ImageStat
helper=Path(__file__).with_name('inspect_board_scene.py').read_text(encoding='utf8').split('slots={};issues=[];font_names=set()')[0]
exec(compile(helper,'original board helpers','exec'))
for obj in env.objects:
 if obj.type.name!='Material':continue
 mat=obj.read()
 if mat.m_Name!='checkerboard_goldcoin_01':continue
 st=mat.m_Shader.deref().read_typetree();shader=st.get('m_ParsedForm',{}).get('m_Name')or st.get('m_Name');print('SHADER',shader,'queue',mat.m_CustomRenderQueue)
 print('COLORS',{n:{k:getattr(v,k)for k in 'rgba'}for n,v in mat.m_SavedProperties.m_Colors});print('FLOATS',mat.m_SavedProperties.m_Floats)
 for n,t in mat.m_SavedProperties.m_TexEnvs:
  if not t.m_Texture.path_id:continue
  tex=t.m_Texture.read();print('TEX',n,tex.m_Name,'ST',t.m_Scale,t.m_Offset,'format',tex.m_TextureFormat)
  original=Image.open(ROOT/'client/SHIN/Assets/Art/City/Chessboard/LuckyCoin/Textures/checkerboard_goldcoin_01_d.tga').convert('RGBA');exported=Image.open(SCENE/'grid-atlas-goldcoin.png').convert('RGBA');built=tex.image.convert('RGBA')
  print('TEXTURE SOURCE EXPORT EXACT',original.size,original.tobytes()==exported.tobytes(),'alpha source extrema',original.getchannel('A').getextrema(),'alpha export extrema',exported.getchannel('A').getextrema(),'alpha source nonopaque',sum(v<255 for v in original.getchannel('A').getdata()),'bundle alpha extrema',built.getchannel('A').getextrema(),'bundle/source diffRGBA means',ImageStat.Stat(ImageChops.difference(original,built)).mean)