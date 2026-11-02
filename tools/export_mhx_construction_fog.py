"""Retain original fog renderer/camera/material and compiled GLES alpha formula."""
import hashlib,json
from pathlib import Path
from export_mhx_construction_scene import load_environment,make_index,Exporter,OUT,vec,color,write_json
from UnityPy.export.ShaderConverter import ShaderProgram
from UnityPy.helpers import CompressionHelper
from UnityPy.streams import EndianBinaryReader

def export():
    env,chosen,missing=load_environment(make_index(),lambda n:'/mask/world_1/maskcomp.prefab' in n.lower())
    result={'format':1,'source':'MapGame/Prefab/Mask/world_1/MaskComp.prefab','maskLayer':26,'shaderName':'Custom/FogOfWar','sourceAlphaFormula':'out.a = (1 - texture(_MaskTex, uv).a) * _FogColor.a','missingDependencies':missing,'programs':[]}
    for path,ptr in env.container.items():
        if '/mask/world_1/maskcomp.prefab' not in path.lower():continue
        go=ptr.read()
        for pair in go.m_Component:
            obj=pair.component.deref();tree=obj.read_typetree()
            if obj.type.name=='Transform':result['rootTransform']={k:v for k,v in tree.items()if k in ['m_LocalPosition','m_LocalRotation','m_LocalScale']}
            if obj.type.name=='MonoBehaviour'and 'fogTextureSize'in tree:result['runtimeFields']={k:v for k,v in tree.items()if k not in ['m_GameObject','m_Script']}
            if obj.type.name=='SpriteRenderer':
                r=pair.component.read();ex=Exporter(env);ident=ex.sprite(r.m_Sprite);result['renderer']={'sprite':ex.sprites[ident],'enabled':r.m_Enabled,'layer':r.m_SortingLayer,'order':r.m_SortingOrder,'color':color(r.m_Color)}
        result['sourceObject']=ptr.deref().assets_file.name+':'+str(ptr.m_PathID)
    for obj in env.objects:
        if obj.type.name=='Camera':
            t=obj.read_typetree();result['camera']={'orthographicSize':t['orthographic size'],'clearColor':t['m_BackGroundColor'],'cullingMask':t['m_CullingMask']['m_Bits']}
        if obj.type.name=='Material' and obj.peek_name()=='FogOfWar':result['material']=obj.read_typetree()
        if obj.type.name!='Shader':continue
        shader=obj.read()
        if shader.m_ParsedForm.m_Name!='Custom/FogOfWar':continue
        for i,platform in enumerate(shader.platforms):
            for j,offset in enumerate(shader.offsets[i]):
                raw=CompressionHelper.decompress_lz4(bytes(shader.compressedBlob)[offset:offset+shader.compressedLengths[i][j]],shader.decompressedLengths[i][j]);program=ShaderProgram(EndianBinaryReader(raw,endian='<'),obj.version)
                for sub in program.m_SubPrograms:
                    code=bytes(sub.m_ProgramCode)
                    if b'void main'in code:result['programs'].append({'platform':platform,'code':code.decode('utf8'),'sha256':hashlib.sha256(code).hexdigest()})
    write_json(OUT/'fog.json',result);print(json.dumps({'source':result['source'],'programs':len(result['programs']),'textureSize':result['runtimeFields']['fogTextureSize'],'orthoSize':result['camera']['orthographicSize']}))

if __name__=='__main__':export()
