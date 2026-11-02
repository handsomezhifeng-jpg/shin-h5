// Original Dott.DOTweenTimeline + DOTweenAnimation unit-entry sequences.
// Native scheduling: current-GameObject component order, CreateTween(true,true),
// then Sequence.Insert(0,tween). Child delays remain the insertion offsets.
const ROOT=new URL('../assets/construction/',import.meta.url).href;
const clamp=t=>Math.max(0,Math.min(1,t));
const vector=v=>[Number(v.x),Number(v.y),Number(v.z)];
const color=v=>[Number(v.r),Number(v.g),Number(v.b),Number(v.a)];
const lerp=(a,b,t)=>a.map((v,i)=>v+(b[i]-v)*t);
const copy=v=>Array.isArray(v)?[...v]:v;
const keyOf=value=>{
 if(typeof value==='number'&&!Number.isSafeInteger(value))throw Error('原Timeline目标PathID必须无损导出为字符串');
 return String(value);
};
export function constructionUnitTimelineEase(type,t){
 t=clamp(t);
 if(Number(type)===1)return t;
 if(Number(type)===6)return t*(2-t);
 if(Number(type)===30){const n=7.5625,d=2.75;if(t<1/d)return n*t*t;if(t<2/d)return n*(t-=1.5/d)*t+.75;if(t<2.5/d)return n*(t-=2.25/d)*t+.9375;return n*(t-=2.625/d)*t+.984375;}
 throw Error('未核准的原Timeline Ease '+type);
}
/** Compile the serialized target references without name or bounding-box guesses. */
export function compileConstructionUnitTimeline(record,prefab,{sequenceEase,initialFor}={}){
 if(sequenceEase===undefined)throw Error('原Dott Sequence默认Ease尚未核准');
 const nodes=new Map(prefab.nodes.map((node,index)=>[keyOf(node.sourceGameObjectPathID),{node,index}])),tracks=[],groups=[];
 for(const timeline of record.nodes.filter(n=>n.class==='DOTweenTimeline'&&n.fields.m_Enabled)){
  const group={sourceObject:timeline.sourceObject,nodeIndex:timeline.nodeIndex,path:timeline.path,ease:Number(sequenceEase),tracks:[],duration:0};
  for(const row of record.nodes){
   if(row.class!=='DOTweenAnimation'||row.nodeIndex!==timeline.nodeIndex)continue;
   const f=row.fields;if(!f.m_Enabled||!f.isActive||!f.isValid)continue;
   for(const[event,value]of Object.entries(f))if(value?.m_PersistentCalls?.m_Calls?.length)throw Error('原Timeline含未核准UnityEvent '+event+' '+row.sourceObject);
   if(f.isSpeedBased||f.useTargetAsV3)throw Error('原Timeline含尚未实现的速度/Transform目标配置 '+row.sourceObject);
   const targetId=keyOf(f.targetIsSelf?f.m_GameObject.m_PathID:f.targetGO.m_PathID),target=nodes.get(targetId);
   if(!target)throw Error('原Timeline目标节点未导出 '+targetId);
   const type=Number(f.animationType),trs=target.node.trs,initial=initialFor?.(targetId);let property,base,endpoint,nativeMeshTarget=null;
   if(type===2){property='position';base=initial?vector(initial.localPosition):copy(trs.position);endpoint=vector(f.endValueV3);}
   else if(type===5){property='scale';base=initial?vector(initial.localScale):copy(trs.scale);endpoint=f.optionalBool0?Array(3).fill(Number(f.endValueFloat)):vector(f.endValueV3);}
   else if(type===7){property='color';base=initial?color(initial.color):copy(target.node.sprite?.color);endpoint=base&&[...base.slice(0,3),Number(f.endValueFloat)];}
   else if(type===8){
    // Runtime custom MapUnitFade follows this exact original SRP mapping:
    // target.GetComponent<SRPBatchingSpriteRenderer>().srpBatchingGO
    //   .GetComponent<MeshRenderer>().material.DOFade(...).
    // The H5 scene draws that mesh's original Sprite directly; its own alpha
    // represents this one mapped material, without tinting other descendants.
    const mapped=target.node.srpBatchingGOPathID&&nodes.get(keyOf(target.node.srpBatchingGOPathID));
    if(!mapped?.node.meshRenderer)continue;
    nativeMeshTarget=keyOf(mapped.node.sourceGameObjectPathID);property='color';base=initial?color(initial.color):copy(target.node.sprite?.color);endpoint=base&&[...base.slice(0,3),Number(f.endValueFloat)];
   }
   else throw Error('未实现的原Timeline AnimationType '+type);
   if(!base||!base.every(Number.isFinite)||!endpoint.every(Number.isFinite))throw Error('原Timeline目标属性缺失 '+row.sourceObject);
   let from,to;
   if(f.isFrom){from=endpoint.map((v,i)=>v+(f.isRelative?base[i]:0));to=base;}
   else{from=base;to=endpoint.map((v,i)=>v+(f.isRelative?base[i]:0));}
   if(type===7||type===8){from=[...base.slice(0,3),from[3]];to=[...base.slice(0,3),to[3]];}
   const loops=Number(f.loops)||1;if(loops<1||!Number.isInteger(loops))throw Error('原Timeline无限循环不能用于有限解锁队列');
   const track={sourceObject:row.sourceObject,targetId,nativeMeshTarget,nodeIndex:target.index,property,type,from,to,delay:Number(f.delay)||0,duration:Number(f.duration)||0,loops,loopType:Number(f.loopType),ease:Number(f.easeType),isFrom:!!f.isFrom,isRelative:!!f.isRelative,optionalBool0:!!f.optionalBool0};
   if(track.duration<0||track.delay<0)throw Error('原Timeline时间无效');
   group.duration=Math.max(group.duration,track.delay+track.duration*loops);group.tracks.push(track);tracks.push(track);
  }
  groups.push(group);
 }
 return{groups,tracks,duration:Math.max(0,...groups.map(g=>g.duration)),source:'Dott.TryGenerateSequence: Insert(0) in source component order; no Append/Join or hierarchy sorting.'};
}
export function sampleConstructionUnitTimeline(plan,seconds){
 const result={};
 for(const group of plan.groups){
  const time=constructionUnitTimelineEase(group.ease,group.duration?seconds/group.duration:1)*group.duration;
  for(const track of group.tracks){
   const elapsed=Math.max(0,time-track.delay),total=track.duration*track.loops,done=elapsed>=total;
   let cycle=track.duration?Math.floor(elapsed/track.duration):0,fraction=track.duration?(elapsed%track.duration)/track.duration:1;
   if(done){cycle=track.loops-1;fraction=1;}
   if(track.loopType===1&&cycle%2)fraction=1-fraction;
   const eased=constructionUnitTimelineEase(track.ease,fraction),offset=track.loopType===2?cycle:0,value=lerp(track.from,track.to,eased).map((v,i)=>v+(track.to[i]-track.from[i])*offset);
   (result[track.targetId]||={})[track.property]=value;
  }
 }
 return result;
}
export async function loadConstructionUnitTimeline(){
 const response=await fetch(ROOT+'unit-timelines.json');if(!response.ok)throw Error('原建筑Timeline读取失败');const data=await response.json(),active=new Set();let disposed=false;
 const cancel=()=>{for(const session of [...active])session.cancel();};
 return{data,
  async play(scene,unitId,{signal,timeScale=5/3}={}){
   if(disposed||signal?.aborted)return{completed:false,cancelled:true};
   if(!(timeScale>0&&Number.isFinite(timeScale)))throw Error('原建筑Timeline时间倍率必须为正');
   const graph=scene.unitHierarchy(String(unitId)),record=graph&&data.prefabs[graph.key.toLowerCase()];
   if(!record)return{completed:true,skipped:true,duration:0};
   if(!scene.setUnitNodeOverrides||!scene.clearUnitNodeOverrides)throw Error('场景尚未支持原Timeline节点变换');
   for(const session of [...active])if(session.scene===scene&&session.unitId===String(unitId))session.cancel();
   const plan=compileConstructionUnitTimeline(record,graph.prefab,{sequenceEase:data.nativeRules?.sequenceEase,initialFor:id=>scene.getNodeState?.(String(unitId),id)});
   const start=performance.now();
   return new Promise((resolve,reject)=>{
    let raf=0,finished=false;
    const finish=(completed,error)=>{if(finished)return;finished=true;cancelAnimationFrame(raf);signal?.removeEventListener('abort',onAbort);active.delete(session);scene.clearUnitNodeOverrides(String(unitId));if(error){reject(error);return;}resolve({completed,cancelled:!completed,unitId:String(unitId),duration:plan.duration,wallDuration:plan.duration/timeScale,timeScale,tracks:plan.tracks.length,sequences:plan.groups.length});};
    const onAbort=()=>finish(false),session={scene,unitId:String(unitId),cancel:onAbort};active.add(session);signal?.addEventListener('abort',onAbort,{once:true});
    const tick=now=>{if(finished)return;if(signal?.aborted)return onAbort();try{const time=Math.min(plan.duration,(now-start)/1000*timeScale);scene.setUnitNodeOverrides(String(unitId),sampleConstructionUnitTimeline(plan,time));if(time<plan.duration)raf=requestAnimationFrame(tick);else finish(true);}catch(error){finish(false,error);}};
    tick(start);
   });
  },cancel,
  dispose(){cancel();disposed=true;}
 };
}
