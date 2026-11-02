// Direct port of MapRoleMgr.ShowCurMainQuestRoles / IdleNpcMgr spawn selection.
// Source tables and Lua identities are recorded in scene-npcs/animations.json.
const list=value=>value===undefined||value===null||value===''?[]:String(value).split(';');
const point=value=>String(value).split(',').map(Number);
const mul=(p,q)=>[p[0]*q[0]+p[2]*q[1],p[1]*q[0]+p[3]*q[1],p[0]*q[2]+p[2]*q[3],p[1]*q[2]+p[3]*q[3],p[0]*q[4]+p[2]*q[5]+p[4],p[1]*q[4]+p[3]*q[5]+p[5],(p[6]||0)+(q[6]||0)];
export function resolveConstructionQuestScene(data,state={}){
 const questId=Number(state.questId??state.currentQuestId??1),quests=data.quests||data.firstChapter.quests,standpoints=data.standpoints||data.firstChapter.standpoints,quest=quests.find(q=>q.id===questId),standPoint=standpoints.find(p=>p.id===quest?.plotId);
 if(!standPoint)return{questId,quest,standPoint:null,actors:[],camera:null};
 const roles=list(standPoint.roleIds),positions=list(standPoint.positions).map(point),actions=list(standPoint.actionNames??standPoint.actionIds),dirs=list(standPoint.orient),scales=list(standPoint.roleScales??standPoint.roleScale),floors=list(standPoint.roleFloors),sameWorld=Number(state.worldId??1)===standPoint.worldId;
 const actors=sameWorld?roles.map((id,i)=>({id:'plot:'+id,role:'q_npc_'+id,roleId:Number(id),x:positions[i][0],y:positions[i][1],z:positions[i][2]||0,action:actions[i],dir:Number(dirs[i])||2,rootScale:Number(scales[i])>0?Number(scales[i]):1,floor:Number(floors[i])||1,source:{table:'PlotStandPointVo',id:standPoint.id,index:i}})):[];
 const center=standPoint.camPos?point(standPoint.camPos):positions.reduce((v,p)=>[v[0]+p[0]/positions.length,v[1]+p[1]/positions.length],[0,0]),camera={x:sameWorld?center[0]:0,y:sameWorld?center[1]:0,orthographicSize:data.rules.cameraAPP.orthographicSize};
 return{questId,quest,standPoint,actors,camera};
}
export function constructionUnitNpcPoint(scene,unitId,pointId){
 const state=scene.state||{},visible=state.visible;if(Array.isArray(visible)?!visible.includes(unitId):visible&&typeof visible==='object'?!visible[unitId]:false)return null;if(state.prefabs?.[unitId]===false)return null;const unit=scene.data.units[unitId];if(!unit)return null;let path=typeof state.prefabs?.[unitId]==='string'?state.prefabs[unitId]:unit.prefabPath;if(state.skins?.[unitId]!==undefined)path=path.replace(/_skin\d+/i,'_skin'+String(state.skins[unitId]).padStart(2,'0'));const prefab=scene.data.prefabs[path.toLowerCase()];if(!prefab)return null;const p=point(unit.transform.localPosition),s=point(unit.transform.localScale),q=point(unit.transform.rotation),angle=2*Math.atan2(q[2],q[3]),c=Math.cos(angle),sn=Math.sin(angle),base=[s[0]*c,s[0]*sn,-s[1]*sn,s[1]*c,p[0],p[1],p[2]],matrices=[];
 for(const node of prefab.nodes){const matrix=node.parent===null?base:mul(matrices[node.parent],node.matrix);matrices.push(matrix);if(node.name==='npcPoint_'+pointId)return{x:matrix[4],y:matrix[5],z:matrix[6]};}return null;
}
export function spawnConstructionIdleNPCs(data,scene,state={},random=Math.random){
 const quest=resolveConstructionQuestScene(data,state);if(!quest.standPoint)return[];const currentQuest=quest.questId,currentView=Number(state.viewQuestId??state.currentViewQuestId??currentQuest),rows=(data.idleNpcs||data.firstChapter.idleNpcs).filter(r=>r.status===1&&((r.unlockType===4&&currentQuest>=r.unlockNum)||(r.unlockType===6&&currentView>=r.unlockNum)||!r.unlockType));const randomDict=new Map(),fixedDict=new Map();
 for(const row of rows){const ids=list(row.npcIds),actions=list(row.actionNames);for(let j=0;j<(row.type===1?ids.length:Math.min(1,ids.length));j++){const id=Number(ids[j]),dict=row.type===1?randomDict:fixedDict;if(!dict.has(id))dict.set(id,[]);dict.get(id).push({unitId:String(row.unitId),actions:actions[j].split(','),pointNum:Number(row.pointNum),pointId:row.type===1?undefined:Number(row.pointId),sourceId:row.id});}}
 const usedUnits=new Set(),actors=[],positions=list(quest.standPoint.positions).map(point),pick=values=>values[Math.min(values.length-1,Math.floor(random()*values.length))];
 const spawn=(dict,maximum)=>{const ids=[...dict.keys()];for(let i=ids.length-1;i>=0;i--){const j=Math.min(i,Math.floor(random()*(i+1)));[ids[i],ids[j]]=[ids[j],ids[i]];}for(const id of ids){if(maximum<=0)break;const available=dict.get(id).filter(p=>!usedUnits.has(p.unitId)),final=[];
   // Preserve the source loop's weighting: a point may be added once per distant
   // plot role. Do not replace it with a different "far from every role" rule.
   for(const rolePos of positions)for(const candidate of available){const unit=scene.data.units[candidate.unitId];if(!unit)continue;const p=point(unit.transform.localPosition);if((rolePos[0]-p[0])**2+(rolePos[1]-p[1])**2>data.rules.npcAvoidDistance**2)final.push(candidate);}if(!final.length)continue;const selected=pick(final),action=pick(selected.actions),pointId=selected.pointId||1+Math.min(selected.pointNum-1,Math.floor(random()*selected.pointNum)),p=constructionUnitNpcPoint(scene,selected.unitId,pointId);usedUnits.add(selected.unitId);maximum--;if(!p)continue;actors.push({id:'idle:'+id,role:'q_npc_'+id,roleId:id,...p,action,dir:1,rootScale:1,floor:1,source:{table:'MapIdleNpcVo',id:selected.sourceId,unitId:selected.unitId,pointId}});
  }};spawn(fixedDict,data.rules.fixedNpcMax);spawn(randomDict,data.rules.randomNpcMax);return actors;
}
