from pathlib import Path
import json
helper=Path(__file__).with_name('inspect_board_scene.py').read_text(encoding='utf8').split('slots={};issues=[];font_names=set()')[0]
exec(compile(helper,'original board helpers','exec'))
slots={};fonts={};allnodes=[];normal_layers=set()
for obj in env.objects:
 if obj.type.name=='GameObject':
  g=obj.read()
  if g.m_Name=='model'and g.m_IsActive:
   ch=chain_of(obj)
   if ch[0]['name']=='NormalChessboard_01':normal_layers.add(g.m_Layer)
 if obj.type.name!='MonoBehaviour':continue
 try:t=obj.read_typetree()
 except:continue
 if '_Center'not in t or not t.get('_TextMeshPro',{}).get('m_PathID'):continue
 chain=chain_of(raw_pointer(obj,t['m_GameObject']))
 if chain[0]['name']!='NormalChessboard_01':continue
 ii,instance=next((i,r)for i,r in enumerate(chain[1:],1)if r['name'].isdigit());sid=instance['name']
 text=raw_pointer(obj,t['_TextMeshPro']);tt=text.read_typetree();go=raw_pointer(text,tt['m_GameObject']).read();components=[]
 for c in go.m_Component:
  co=c.component.deref();row={'type':co.type.name}
  if co.type.name=='MonoBehaviour':
   ct=co.read_typetree();script=raw_pointer(co,ct['m_Script']);row['script']=script.read().m_ClassName if script else None
  components.append(row)
 allnodes.append({'id':int(sid),'layer':go.m_Layer,'components':components})
 if sid not in ['1','2']:continue
 font=raw_pointer(text,tt['m_fontAsset']);ft=font.read_typetree();fontname=ft['m_Name'];face=ft['m_FaceInfo']
 fontdata={k:ft[k]for k in ['m_Name','m_FaceInfo','m_GlyphTable','m_CharacterTable','m_AtlasWidth','m_AtlasHeight','m_AtlasPadding','m_AtlasRenderMode','normalStyle','normalSpacingOffset','boldStyle','boldSpacing','italicStyle','tabSize']if k in ft};fonts[fontname]=fontdata
 settings={k:v for k,v in tt.items()if any(n in k.lower()for n in ['fontsize','fontweight','fontstyle','alignment','margin','spacing','orthographic','autosizing','width','height','pivot'])or k=='m_text'}
 h=hook(obj,t['_TextMeshPro'],ii)
 slots[sid]={'layer':go.m_Layer,'components':components,'hook':h,'settings':settings,'font':fontname,'baseFontScale':tt['m_fontSize']/face['m_PointSize']*face['m_Scale']*(1 if tt['m_isOrthographic']else .1),'originalMesh':None,'meshEvidence':'No MeshFilter component and no m_mesh/sharedMesh field serialized. TMP generates a new hidden runtime Mesh in Awake (TMPro_Private.cs:97-114).'}
result={'source':a['AssetPath'],'sourceBundle':primary['FileHash']+'.bundle','slots':slots,'fonts':fonts,'allTextNodes':sorted(allnodes,key=lambda n:n['id']),'normalModelLayers':sorted(normal_layers),'runtimeEvidence':{'meshGeneration':'client/SHIN/Packages/com.unity.textmeshpro@3.0.6/Scripts/Runtime/TMPro_Private.cs:97-114','baseScale':'client/SHIN/Packages/com.unity.textmeshpro@3.0.6/Scripts/Runtime/TMPro_Private.cs:1621','baseScaleFormula':'fontSize / faceInfo.pointSize * faceInfo.scale * (isOrthographic ? 1 : 0.1)','businessTransform':'SquareBase does not modify TMP position/rotation/layer; subclasses update its text/material. The original nodes have no Billboard component.'},'notes':['These are original serialized font metrics and transform evidence, not synthesized glyph geometry.','TMP nodes and normal model nodes are all layer0(Default) in the bundle; no serialized HUD layer separation was found.','Font scale is relative to TMP local units. The RectTransform scale and all parent transforms still apply.','No original 123 vertex buffers were available to export, so originalMesh is explicitly null rather than reconstructed and mislabeled.']}
path=SCENE/'board-text-evidence.json';path.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n',encoding='utf8');print(json.dumps({'output':str(path),'fonts':[(n,len(f['m_GlyphTable']),len(f['m_CharacterTable']),f['m_FaceInfo'])for n,f in fonts.items()],'slots':[(sid,r['baseFontScale'])for sid,r in slots.items()],'allTextNodes':len(allnodes),'normalLayers':sorted(normal_layers)},ensure_ascii=False))