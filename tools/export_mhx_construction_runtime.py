"""Make small lazy runtime manifests without changing the full audit scene."""
import hashlib,json
from pathlib import Path
from export_mhx_construction_scene import OUT,write_json

def export():
    scene=json.loads((OUT/'scene.json').read_text('utf8'));directory=OUT/'prefabs';directory.mkdir(exist_ok=True);files={};masks=[]
    for key,prefab in scene['prefabs'].items():
        ids={n['emissionMeshSprite']for n in prefab['nodes']if n.get('emissionMeshSprite')};ids.update(n['sprite']['id']for n in prefab['nodes']if n.get('sprite'))
        mesh_ids={n['emissionMesh']for n in prefab['nodes']if n.get('emissionMesh')};packet={'prefab':prefab,'spriteMeshes':{sid:scene['sprites'][sid]['mesh']for sid in ids},'emissionMeshes':{mid:scene['emissionMeshes'][mid]for mid in mesh_ids}}
        raw=json.dumps(packet,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf8');digest=hashlib.sha256(raw).hexdigest();target=directory/(digest+'.json')
        if not target.exists():target.write_bytes(raw)
        files[key]={'url':'prefabs/'+target.name,'sha256':digest}
        if any(n['layer']==26 for n in prefab['nodes']):masks.append(key)
    runtime={k:scene[k]for k in ['format','units','unitBounds','coordinateSystem','tileGrid','runtimePrefabRoot','cameraAPP','transparencySort','excludedMainCameraLayers','unresolvedUnitPrefabs']if k in scene};runtime.update(runtimeFormat=1,prefabs={},prefabFiles=files,maskPrefabs=masks,emissionMeshes={},sprites={key:{k:v for k,v in s.items()if k in ['name','url','pixelsToUnits','imageSize','bounds']}for key,s in scene['sprites'].items()},sourceSceneSHA256=hashlib.sha256((OUT/'scene.json').read_bytes()).hexdigest())
    write_json(OUT/'scene-runtime.json',runtime);print(json.dumps({'runtimeBytes':(OUT/'scene-runtime.json').stat().st_size,'fullBytes':(OUT/'scene.json').stat().st_size,'prefabChunks':len(files),'maskPrefabs':len(masks)}))

if __name__=='__main__':export()
