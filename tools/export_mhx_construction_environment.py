"""Export actual ambient Unity particle packets; no replacement animation."""
import hashlib,json,math,re,zipfile
from pathlib import Path
from export_mhx_construction_scene import load_environment,make_index,OUT,write_json,package_bytes,APK
from UnityPy.helpers import TypeTreeHelper
from UnityPy.helpers.CompressionHelper import decompress_lz4
from UnityPy.export.ShaderConverter import ShaderProgram
from UnityPy.streams import EndianBinaryReader

def safe(v):
    if isinstance(v,float)and not math.isfinite(v):return str(v)
    if isinstance(v,dict):return{k:safe(x)for k,x in v.items()}
    if isinstance(v,(list,tuple)):return[safe(x)for x in v]
    if isinstance(v,bytes):return{'length':len(v),'sha256':hashlib.sha256(v).hexdigest()}
    return v
def tree(o):
    native=TypeTreeHelper.read_typetree_boost;TypeTreeHelper.read_typetree_boost=None
    try:return o.read_typetree()
    finally:TypeTreeHelper.read_typetree_boost=native
def identity(o):return o.assets_file.name+':'+str(o.path_id)

def export():
    data=json.loads((OUT/'scene.json').read_text('utf8'));names={'assets/bundleresources/'+n for n in data['prefabs']};env,chosen,missing=load_environment(make_index(),lambda n:n.lower()in names)
    lookup={p.lower().removeprefix('assets/bundleresources/'):o for p,o in env.container.items()if p.lower()in names};textures={};materials={};shaders={};profiles={};clips={}
    images=OUT/'images-environment';images.mkdir(exist_ok=True);shaderdir=OUT/'shaders-environment';shaderdir.mkdir(exist_ok=True)
    def resolve(ref,file):
        if not ref or not ref.get('m_PathID'):return None
        cab=file if not ref['m_FileID']else env.get_cab(file.externals[ref['m_FileID']-1].path)
        return cab.objects.get(ref['m_PathID'])if cab else None
    def texture(o):
        key=identity(o)
        if key not in textures:
            d=o.read();name=re.sub(r'[^\w.-]','_',d.m_Name)+'-'+hashlib.sha256(key.encode()).hexdigest()[:8]+'.png';p=images/name;d.image.save(p);t=tree(o);textures[key]={'name':d.m_Name,'url':'images-environment/'+name,'size':[d.m_Width,d.m_Height],'filter':t.get('m_TextureSettings'),'colorSpace':t.get('m_ColorSpace'),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'sourceObject':key}
        return key
    def shader(o):
        key=identity(o)
        if key in shaders:return key
        t=tree(o);parsed=t['m_ParsedForm'];name=parsed['m_Name'];programs=[];seen=set()
        shaders[key]={'name':name,'sourceObject':key,'parsedForm':parsed,'platforms':t['platforms'],'programs':programs}
        for i,platform in enumerate(t['platforms']):
            for segment,(off,cl,dl)in enumerate(zip(t['offsets'][i],t['compressedLengths'][i],t['decompressedLengths'][i])):
                raw=decompress_lz4(bytes(t['compressedBlob'][off:off+cl]),dl);program=ShaderProgram(EndianBinaryReader(raw,endian='<'),o.version)
                for j,sub in enumerate(program.m_SubPrograms):
                    code=bytes(sub.m_ProgramCode);start=code.find(b'#ifdef VERTEX')
                    if start<0:start=code.find(b'#version')
                    if start<0:continue
                    code=code[start:].split(b'\0',1)[0];digest=hashlib.sha256(code).hexdigest()
                    if digest in seen:continue
                    try:text=code.decode('utf8')
                    except UnicodeDecodeError:continue
                    seen.add(digest);filename=re.sub(r'[^\w.-]','_',name)+'-'+str(platform)+'-'+str(j)+'.glsl';p=shaderdir/filename;p.write_text(text,'utf8');programs.append({'platform':platform,'segment':segment,'subProgram':j,'keywords':[k for k in sub.m_Keywords if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',k)],'keywordParserInvalidEntries':sum(not bool(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',k))for k in sub.m_Keywords),'url':'shaders-environment/'+filename,'sha256':digest})
        return key
    def material(o):
        key=identity(o)
        if key not in materials:
            t=tree(o);r={'name':t['m_Name'],'fields':t,'textures':{},'sourceObject':key};materials[key]=r;sh=resolve(t.get('m_Shader'),o.assets_file)
            if sh:r['shader']=shader(sh)
            for field,prop in t.get('m_SavedProperties',{}).get('m_TexEnvs',[]):
                tx=resolve(prop.get('m_Texture'),o.assets_file)
                if tx:r['textures'][field]={'texture':texture(tx),'scale':prop['m_Scale'],'offset':prop['m_Offset']}
        return key
    for path,ptr in lookup.items():
        nodes=[];systems=[];animations=[]
        def walk(go_ptr,parent=None,active=True,path=''):
            go=go_ptr.read();ni=len(nodes);active=active and bool(go.m_IsActive);path=path+'/'+go.m_Name if path else go.m_Name;node={'name':go.m_Name,'path':path,'parent':parent,'active':bool(go.m_IsActive),'activeInHierarchy':active,'layer':go.m_Layer,'sourceObject':identity(go_ptr.deref())};nodes.append(node);children=[];particle=None;renderer=None
            for pair in go.m_Component:
                o=pair.component.deref()
                if o.type.name not in ['Transform','ParticleSystem','ParticleSystemRenderer','Animation','Animator']:continue
                t=tree(o)
                if o.type.name=='Transform':node['transform']={k:v for k,v in t.items()if k in ['m_LocalPosition','m_LocalRotation','m_LocalScale']};children=pair.component.read().m_Children
                elif o.type.name=='ParticleSystem':particle={'node':ni,'path':path,'activeInHierarchy':active,'fields':t,'sourceObject':identity(o)}
                elif o.type.name=='ParticleSystemRenderer':renderer={'fields':t,'materials':[material(m)for ref in t['m_Materials']if(m:=resolve(ref,o.assets_file))],'sourceObject':identity(o)}
                else:
                    animations.append({'node':ni,'type':o.type.name,'fields':t,'sourceObject':identity(o)})
                    for ref in t.get('m_Animations',[]):
                        clip=resolve(ref,o.assets_file)
                        if clip:clips[identity(clip)]={'fields':tree(clip),'sourceObject':identity(clip)}
            if particle:particle['renderer']=renderer;particle['enabled']=active and bool(renderer and renderer['fields'].get('m_Enabled'));systems.append(particle)
            for ch in children:walk(ch.read().m_GameObject,ni,active,path)
        walk(ptr)
        if systems:profiles[path]={'nodes':nodes,'systems':systems,'animations':animations,'sourceObject':identity(ptr.deref()),'unitIds':[k for k,v in data['units'].items()if v['prefabPath'].lower()==path]}
    with zipfile.ZipFile(APK)as archive:packages=[{'source':s,'sha256':hashlib.sha256(package_bytes(s,archive)).hexdigest()}for s in chosen]
    result={'format':1,'prefabs':profiles,'materials':materials,'textures':textures,'shaders':shaders,'clips':clips,'sourcePackages':packages,'missingDependencies':missing,'clockRule':'Each ParticleSystem retains original looping, lengthInSec, prewarm, playOnAwake, startDelay, simulationSpeed, randomSeed and all modules. Unit prefab root transform is reset by MapMgr; parent units use UnitViewConfig. No synthesized loop or replacement clock.','replayStatus':'Source packets exported. Environment particle replay is not wired into the scene renderer yet.'}
    write_json(OUT/'environment-particles.json',safe(result),ensure_ascii=True);print(json.dumps({'prefabs':len(profiles),'systems':sum(len(p['systems'])for p in profiles.values()),'enabledSystems':sum(s['enabled']for p in profiles.values()for s in p['systems']),'materials':len(materials),'textures':len(textures),'shaders':len(shaders),'clips':len(clips),'missingDependencies':missing}))

if __name__=='__main__':export()
