"""Export original BustRole prefab transforms and type-2 RawImage textures."""
import hashlib,json,re
from pathlib import Path
from export_mhx_construction_scene import load_environment,make_index

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/construction/portraits'

def export():
    env,chosen,missing=load_environment(make_index(),lambda n:'/spines/bustroleprefab/' in n.lower())
    prefabs={};static={}
    for path,ptr in env.container.items():
        if '/spines/bustroleprefab/' not in path.lower() or not path.lower().endswith('.prefab'):continue
        role=ptr.read().m_Name
        if not re.fullmatch(r'npc_\d+',role):continue
        nodes=[]
        def walk(go_ptr,parent=None):
            go=go_ptr.read();index=len(nodes);node={'name':go.m_Name,'active':go.m_IsActive,'parent':parent};nodes.append(node);children=[]
            for pair in go.m_Component:
                obj=pair.component.deref();tree=obj.read_typetree()
                if obj.type.name=='RectTransform':
                    node['transform']={k:v for k,v in tree.items()if k not in ['m_GameObject','m_Children','m_Father']};children=pair.component.read().m_Children
                elif obj.type.name=='MonoBehaviour' and 'skeletonDataAsset' in tree:node['skeletonGraphic']={k:v for k,v in tree.items()if k not in ['m_GameObject','m_Script']}
                elif obj.type.name=='MonoBehaviour' and tree.get('m_Texture',{}).get('m_PathID'):
                    raw=pair.component.read();texture=raw.m_Texture.read();image=texture.image;target=OUT/role;target.mkdir(exist_ok=True);dest=target/(texture.m_Name+'.png');image.save(dest)
                    node['rawImage']={'url':role+'/'+dest.name,'size':list(image.size),'uvRect':tree['m_UVRect'],'color':tree['m_Color'],'textureName':texture.m_Name,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}
            for child in children:walk(child.read().m_GameObject,index)
        walk(ptr)
        prefabs[role]={'nodes':nodes,'sourceObject':ptr.deref().assets_file.name+':'+str(ptr.m_PathID)}
        imageNode=next((n for n in nodes if 'rawImage' in n),None)
        if imageNode:static[role]={'role':role,'roleId':int(role[4:]),'kind':'static','animations':{},'image':imageNode['rawImage'],'uiPrefab':prefabs[role]}
    (OUT/'prefabs.json').write_text(json.dumps({'prefabs':prefabs,'missingDependencies':missing},ensure_ascii=False,indent=2),encoding='utf8')
    (OUT/'static-portraits.json').write_text(json.dumps({'roles':static},ensure_ascii=False,indent=2),encoding='utf8')
    metadata=json.loads((OUT/'npc-animations.json').read_text('utf8'))
    metadata['roles'].update(static)
    for role,record in metadata['roles'].items():
        if role in prefabs:record['uiPrefab']=prefabs[role]
    (OUT/'npc-animations.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'prefabs':len(prefabs),'static':len(static),'bundles':len(chosen),'missing':missing}))

if __name__=='__main__':export()
