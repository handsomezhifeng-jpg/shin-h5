"""Keep full environment evidence; lazy-load actual source emitter packets."""
import hashlib,json
from export_mhx_construction_scene import OUT,write_json

def export():
    data=json.loads((OUT/'environment-particles.json').read_text('utf8'));directory=OUT/'ambient';directory.mkdir(exist_ok=True);files={}
    for key,profile in data['prefabs'].items():
        raw=json.dumps(profile,ensure_ascii=True,separators=(',',':'),allow_nan=False).encode();digest=hashlib.sha256(raw).hexdigest();target=directory/(digest+'.json')
        if not target.exists():target.write_bytes(raw)
        files[key]={'url':'ambient/'+target.name,'sha256':digest}
    runtime={'format':1,'runtimeFormat':1,'prefabs':{},'prefabFiles':files,'textures':data['textures'],'materials':{k:{'name':v['name'],'sourceObject':v['sourceObject'],'shader':v['shader'],'textures':v['textures'],'fields':{'m_SavedProperties':v['fields']['m_SavedProperties']}}for k,v in data['materials'].items()},'shaders':{k:{'name':v['name'],'sourceObject':v['sourceObject']}for k,v in data['shaders'].items()},'sourcePacketSHA256':hashlib.sha256((OUT/'environment-particles.json').read_bytes()).hexdigest()}
    write_json(OUT/'environment-runtime.json',runtime,ensure_ascii=True);print(json.dumps({'runtimeBytes':(OUT/'environment-runtime.json').stat().st_size,'fullBytes':(OUT/'environment-particles.json').stat().st_size,'prefabChunks':len(files)}))

if __name__=='__main__':export()
