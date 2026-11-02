"""Retain original Dott component data for construction unit timeline replay."""
import json,hashlib
from export_mhx_construction_scene import OUT,make_index,load_environment,write_json

def export():
    scene=json.loads((OUT/'scene.json').read_text('utf8'));names={'assets/bundleresources/'+p for p in scene['prefabs']};env,chosen,missing=load_environment(make_index(),lambda n:n.lower()in names);lookup={p.lower().removeprefix('assets/bundleresources/'):o for p,o in env.container.items()if p.lower()in names};scripts={};records={}
    for key,ptr in lookup.items():
        nodes=[];index=0
        def walk(ptr,parentPath=''):
            nonlocal index
            go=ptr.read();path=parentPath+'/'+go.m_Name if parentPath else go.m_Name;nodeIndex=index;index+=1;children=[]
            for pair in go.m_Component:
                obj=pair.component.deref()
                if obj.type.name=='Transform':children=pair.component.read().m_Children
                if obj.type.name!='MonoBehaviour':continue
                tree=obj.read_typetree()
                if 'srpBatchingGO'in tree:continue
                component=pair.component.read();script=component.m_Script
                if not script:continue
                ident=script.deref().assets_file.name+':'+str(script.m_PathID)
                if ident not in scripts:
                    s=script.read();scripts[ident]=(s.m_ClassName,s.m_Namespace,s.m_AssemblyName)
                name,namespace,assembly=scripts[ident]
                if 'DOTween'in name or namespace=='Dott':nodes.append({'nodeIndex':nodeIndex,'path':path,'class':name,'namespace':namespace,'assembly':assembly,'sourceObject':obj.assets_file.name+':'+str(obj.path_id),'fields':tree})
            for child in children:walk(child.read().m_GameObject,path)
        walk(ptr)
        if nodes:records[key]={'nodes':nodes,'unitIds':[id for id,u in scene['units'].items()if u['prefabPath'].lower()==key]}
    rules={'sequenceEase':1,'animationTypes':{'LocalMove':2,'Scale':5,'Color':6,'Fade':7,'MapUnitFade':8},'mapUnitFade':'Runtime target SRPBatchingSpriteRenderer.srpBatchingGO MeshRenderer.material.DOFade; missing mapping returns without a tween. H5 applies alpha only to the original Sprite representing this exact mapped SRP mesh.','sequenceEaseName':'Linear','insertAt':0,'componentOrder':'Serialized current-GameObject component array; no hierarchy traversal or id sorting.','childCreation':'DOTweenAnimation.CreateTween(true,true); From sets the original target immediately, before SetDelay.','sourceMethods':{'Dott.DOTweenTimeline.TryGenerateSequence':'0x3889b40','Dott.DOTweenTimeline.InsertCall':'0x3889d74','Sequence.Setup':'0x19b49a8','Sequence.Setup.easeTypeWrite':'0x19b4a5c','DOTweenAnimation.CreateTween.From':'0x388b048','From.setImmediately':'0x194abe4'},'evidence':'outputs/construction-story-fx/unit-timeline-native-evidence.json'}
    write_json(OUT/'unit-timelines.json',{'version':'1.4.93.1','prefabs':records,'missingDependencies':missing,'nativeRules':rules,'replayStatus':'Implemented in src/construction-unit-timeline.mjs from native Insert(0) scheduling and original DOTweenAnimation parameters. Scene overrides use exact original target GameObject PathID strings.'},ensure_ascii=True);print(json.dumps({'prefabs':len(records),'components':sum(len(r['nodes'])for r in records.values()),'examples':list(records)[:8]}))

if __name__=='__main__':export()
