// PerformScripts.PlayUnitsUnlockByUnlockVo: original non-hammer unlock effects.
import {loadConstructionNewLook} from './construction-newlook.mjs';
const SOURCE={
  1:{name:'NormalStar',file:'unitfx-star.json',duration:2,soundId:22,phase:'after-show'},
  2:{name:'Dust',file:'unitfx-dust.json',duration:1.5,soundId:27,phase:'with-hide'},
  4:{name:'FireClean',file:'unitfx-fire-clean.json',duration:1.5,soundId:75,phase:'with-hide'},
  5:{name:'WindClean',file:'unitfx-wind-clean.json',duration:1.5,soundId:76,phase:'with-hide'},
  6:{name:'StarClean',file:'unitfx-star-clean.json',duration:1.5,soundId:77,phase:'with-hide'},
  7:{name:'DustClean',file:'unitfx-dust-clean.json',duration:2,soundId:21,phase:'before-reload'}
};
const number=(v,label)=>{if(!Number.isFinite(v))throw Error('原施工特效缺少'+label);return v;};
/** Apply the exact runtime shape overrides from PerformScripts.lua:643-674. */
export function prepareConstructionUnitFx(kind,source,{unitBounds,sceneUnit={}}={}){
  kind=Number(kind);const specification=SOURCE[kind];if(!specification)throw Error('未接入原解锁特效类型 '+kind);
  const data=structuredClone(source);data.duration=specification.duration;
  if(kind!==1)return data;
  const system=data.particleSettings[0];if(!system)throw Error('缺少原NormalStar粒子系统');
  const shape=system.fields.ShapeModule,initial=system.fields.InitialModule;
  if(sceneUnit.emissionMesh){
    shape.type=13;shape.m_Scale={x:1,y:1,z:1};shape.m_Position={x:0,y:0,z:0};
    shape._emissionMesh=sceneUnit.emissionMesh;
    initial.startSize.scalar=1;
    data.runtimeShape={type:'MeshRenderer',source:sceneUnit.emissionMesh.source||sceneUnit.sourceObject||null,startSizeMultiplier:1};
  }
  if(sceneUnit.tilemap){
    const bounds=unitBounds||sceneUnit.unitBounds;
    const width=number(bounds?.size?.x,'Tilemap bounds.width'),height=number(bounds?.size?.y,'Tilemap bounds.height');
    const x=number(bounds?.center?.x,'Tilemap bounds.center.x'),y=number(bounds?.center?.y,'Tilemap bounds.center.y');
    shape.type=18;shape.m_Scale={x:width,y:height,z:1};shape.m_Position={x,y,z:0};delete shape._emissionMesh;
    initial.startSize.scalar=Math.ceil(width*height/100);
    data.runtimeShape={type:'Rectangle',bounds,startSizeMultiplier:initial.startSize.scalar};
  }
  if(!data.runtimeShape)throw Error('原NormalStar需要单位MeshRenderer三角形或Tilemap边界');
  return data;
}
export async function loadConstructionUnitFx(){
  const loaders=new Map(),active=new Set();let disposed=false,generation=0;
  const load=kind=>{if(!loaders.has(kind))loaders.set(kind,loadConstructionNewLook({file:SOURCE[kind].file}));return loaders.get(kind);};
  const cancelAll=()=>{generation++;for(const instance of active)instance.dispose();active.clear();};
  return{
    source:SOURCE,
    async preload(kinds=Object.keys(SOURCE)){return Promise.all(kinds.map(kind=>load(Number(kind))));},
    async play(kind,parent,options={}){
      kind=Number(kind);if(!SOURCE[kind])throw Error('未接入原解锁特效类型 '+kind);
      if(disposed||options.signal?.aborted)return{completed:false,cancelled:true,kind};
      const startedGeneration=generation,base=await load(kind);if(disposed||startedGeneration!==generation||options.signal?.aborted)return{completed:false,cancelled:true,kind};
      const data=prepareConstructionUnitFx(kind,base.data,options),instance=base.fork(data),cancel=()=>instance.dispose();
      active.add(instance);options.signal?.addEventListener('abort',cancel,{once:true});
      try{return{...await instance.play(parent,options),kind,name:SOURCE[kind].name,sourcePhase:SOURCE[kind].phase,sourceSoundId:SOURCE[kind].soundId};}
      finally{options.signal?.removeEventListener('abort',cancel);active.delete(instance);instance.dispose();}
    },
    cancel:cancelAll,
    dispose(){disposed=true;cancelAll();for(const promise of loaders.values())promise.then(loader=>loader.dispose(),()=>{});loaders.clear();}
  };
}
