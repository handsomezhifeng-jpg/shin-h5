"""Export original hammer particle renderer/material/texture/shader dependencies."""
from pathlib import Path
import hashlib
import json
import math
import re
import zipfile
import UnityPy
from UnityPy.files import SerializedFile
from UnityPy.helpers import TypeTreeHelper
from UnityPy.helpers.CompressionHelper import decompress_lz4
from UnityPy.streams import EndianBinaryReader
from UnityPy.export.ShaderConverter import ShaderProgram

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets'/'construction'
EVIDENCE=ROOT.parent/'经验'/'outputs'/'梦幻消除战-资源核查'
HAMMER=OUT/'hammer.json'
data=json.loads(HAMMER.read_text(encoding='utf8'))
cab_sources=dict(globals()['additional_cabinet_sources'])if 'additional_cabinet_sources'in globals()else json.loads((EVIDENCE/'cab-source-index.json').read_text(encoding='utf8'))
apk=zipfile.ZipFile(r'C:\Users\zhfzhang\Downloads\梦幻消除战.apk')
env=UnityPy.Environment();loaded=set();source_records={}
native_reader=TypeTreeHelper.read_typetree_boost
def tree(obj):
    TypeTreeHelper.read_typetree_boost=None
    try:return obj.read_typetree()
    finally:TypeTreeHelper.read_typetree_boost=native_reader
def serialized(file,name=None):
    if isinstance(file,SerializedFile):
        if not file.name:file.name=name
        yield file;return
    for k,v in (getattr(file,'files',None) or {}).items():yield from serialized(v,k)
def load(source):
    if source in loaded:return
    loaded.add(source);raw=apk.read(source) if source.startswith('assets/') else Path(source).read_bytes();source_records[source]={'sha256':hashlib.sha256(raw).hexdigest()};outer=env.load_file(raw,name=source)
    for f in serialized(outer):
        for ext in f.externals:
            dep=cab_sources.get(ext.path.rsplit('/',1)[-1].lower())
            if dep:load(dep)
def resolve(ref,file):
    if not ref or not ref.get('m_PathID'):return None
    target=file if ref['m_FileID']==0 else env.get_cab(file.externals[ref['m_FileID']-1].path)
    return target.objects.get(ref['m_PathID']) if target else None
def identity(obj):return obj.assets_file.name+':'+str(obj.path_id)
def safe(v):
    if isinstance(v,float) and not math.isfinite(v):return str(v)
    if isinstance(v,dict):return{k:safe(x) for k,x in v.items()}
    if isinstance(v,(tuple,list)):return[safe(x) for x in v]
    if isinstance(v,bytes):return{'byteLength':len(v),'sha256':hashlib.sha256(v).hexdigest()}
    return v
load(data['source'])
textures={};materials={};shaders={};renderers={};sprite_renderers={}
image_dir=OUT/'images-hammer';image_dir.mkdir(exist_ok=True)
def export_texture(obj):
    key=identity(obj)
    if key not in textures:
        t=obj.read();name=t.m_Name;image=t.image;filename=name+'-'+hashlib.sha256(key.encode()+image.tobytes()).hexdigest()[:12]+'.png';p=image_dir/filename;image.save(p)
        textures[key]={'name':name,'url':'assets/construction/images-hammer/'+filename,'width':t.m_Width,'height':t.m_Height,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'sourceObject':key,'colorSpace':tree(obj).get('m_ColorSpace'),'filterMode':tree(obj).get('m_TextureSettings')}
    return key
def export_shader(obj):
    key=identity(obj)
    if key not in shaders:
        t=tree(obj);parsed=t.get('m_ParsedForm',{});name=parsed.get('m_Name') or t.get('m_Name');serialized_hash=hashlib.sha256(obj.get_raw_data()).hexdigest();shaders[key]={'name':name,'parsedForm':parsed,'platforms':t.get('platforms'),'sourceObject':key,'serializedSha256':serialized_hash}
        try:
            shader_dir=OUT/'shaders-hammer';shader_dir.mkdir(exist_ok=True);prefix=name.replace('/','-')+'-'+hashlib.sha256((key+serialized_hash).encode()).hexdigest()[:12];filename=prefix+'.shader';text=obj.read().export();p=shader_dir/filename;p.write_text(text,encoding='utf8');shaders[key]['exportUrl']='assets/construction/shaders-hammer/'+filename;shaders[key]['exportSha256']=hashlib.sha256(p.read_bytes()).hexdigest()
        except Exception as exc:shaders[key]['exportError']=str(exc)
        programs=[];seen=set()
        for i,platform in enumerate(t.get('platforms',[])):
            for segment,(offset,compressed,decompressed) in enumerate(zip(t['offsets'][i],t['compressedLengths'][i],t['decompressedLengths'][i])):
                raw=decompress_lz4(bytes(t['compressedBlob'][offset:offset+compressed]),decompressed)
                program=ShaderProgram(EndianBinaryReader(raw,endian='<'),obj.version)
                for index,sub in enumerate(program.m_SubPrograms):
                    code=bytes(sub.m_ProgramCode);start=code.find(b'#ifdef VERTEX')
                    if start<0:start=code.find(b'#version')
                    if start<0:continue
                    code=code[start:].split(b'\x00',1)[0];digest=hashlib.sha256(code).hexdigest()
                    if digest in seen:continue
                    try:text=code.decode('utf8')
                    except UnicodeDecodeError:continue
                    seen.add(digest);filename=prefix+'-'+str(platform)+'-'+str(index)+'.glsl';p=shader_dir/filename;p.write_text(text,encoding='utf8');keywords=[word for word in sub.m_Keywords if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',word)];programs.append({'platform':platform,'segment':segment,'subProgram':index,'keywords':keywords,'keywordParserInvalidEntries':len(sub.m_Keywords)-len(keywords),'url':'assets/construction/shaders-hammer/'+filename,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
        shaders[key]['programs']=programs
    return key
def export_material(obj):
    key=identity(obj)
    if key not in materials:
        t=tree(obj);record={'name':t['m_Name'],'properties':t.get('m_SavedProperties'),'renderQueue':t.get('m_CustomRenderQueue'),'keywords':t.get('m_ShaderKeywords'),'validKeywords':t.get('m_ValidKeywords',[]),'invalidKeywords':t.get('m_InvalidKeywords',[]),'fields':t,'sourceObject':key,'textures':{}}
        shader=resolve(t.get('m_Shader'),obj.assets_file)
        if shader:record['shader']=export_shader(shader)
        for field,prop in t.get('m_SavedProperties',{}).get('m_TexEnvs',[]):
            tex=resolve(prop.get('m_Texture'),obj.assets_file)
            if tex:record['textures'][field]={'texture':export_texture(tex),'scale':prop['m_Scale'],'offset':prop['m_Offset']}
        materials[key]=record
    return key
def walk(node):
    yield node
    for child in node.get('children',[]):yield from walk(child)
for node in walk(data['prefab']):
    for c in node['components']:
        if c['type'] not in ('ParticleSystemRenderer','SpriteRenderer'):continue
        cab,pid=c['sourceObject'].rsplit(':',1);obj=env.get_cab(cab).objects[int(pid)];t=tree(obj)
        target=renderers if c['type']=='ParticleSystemRenderer'else sprite_renderers
        target[node['path']]={'fields':t,'materials':[export_material(m) for ref in t.get('m_Materials',[]) if (m:=resolve(ref,obj.assets_file))]}
data['particleRenderers']=renderers;data['spriteRenderers']=sprite_renderers;data['particleMaterials']=materials;data['particleTextures']=textures;data['particleShaders']=shaders;data['particleSources']=source_records
data['particleReplay']={'systemCount':18,'integrationStep':1/240,'implementedModules':['InitialModule','ShapeModule (source Cone only)','EmissionModule','SizeModule','ColorModule','UVModule','ClampVelocityModule'],'shaderEvidence':[p['url']for shader in shaders.values()for p in shader['programs']if not p['keywords']],'shaderFormula':'rgb=pow(max(texture.rgb,0),Contrast)*Brightness*MainColor.rgb*vertex.rgb; a=clamp(texture.a*MainColor.a*vertex.a); add outputs (rgb*a,0) with One/One, normal outputs (rgb,a) with SrcAlpha/OneMinusSrcAlpha.','remainingDifferences':['The source uses autoRandomSeed. H5 uses a deterministic Mulberry32 random stream for reproducible QA; its random sequence is not the Unity native sequence.','Unity native cone random distribution, speed dampening/drag integration, and stretched-billboard pivot implementation are closed. The H5 implementation uses the recorded parameters with a 240 Hz integration step and records this numerical approximation.','H5 projects the original hierarchy onto the construction screen plane. It does not reproduce the full Unity camera/depth pipeline or active color-space conversion bit for bit.','Canvas output alpha for non-additive primitives uses One/OneMinusSrcAlpha to maintain DOM-compositing coverage, while the source Unity framebuffer stores SrcAlpha/OneMinusSrcAlpha in its alpha channel too. Visible RGB uses the source blend factors.']}
data['limitations']=data['particleReplay']['remainingDifferences']
HAMMER.write_text(json.dumps(safe(data),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({'renderers':len(renderers),'materials':[(v['name'],v.get('shader'),v['textures']) for v in materials.values()],'textures':list(textures.values()),'shaders':[(k,v['name']) for k,v in shaders.items()]},ensure_ascii=True))
