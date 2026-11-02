// Batch-check source references without opening an emulator or advancing saves.
import fs from'node:fs/promises';import path from'node:path';
import{NativeConstructionProgress,loadNativeConstructionData}from'../src/construction-native-progress.mjs';
import{loadNativeConstructionPlotStage}from'../src/construction-native-plot.mjs';
import{NativeConstruction}from'../src/construction-native.mjs';
import{preflightConstructionStoryEffects}from'../src/construction-story-effects.mjs';
const root=path.resolve(import.meta.dirname,'..'),read=async p=>JSON.parse(await fs.readFile(path.join(root,p),'utf8'));
const fetcher=async url=>{try{const value=JSON.parse(await fs.readFile(url,'utf8'));return{ok:true,json:async()=>value};}catch{return{ok:false};}};
const[data,scene,portraits,npcs,effects]=await Promise.all([loadNativeConstructionData({fetch:fetcher}),read('assets/construction/scene.json'),read('assets/construction/portraits/npc-animations.json'),read('assets/construction/scene-npcs/animations.json'),read('assets/construction/story-effects.json')]);
const progress=new NativeConstructionProgress({state:{coins:60000,level:1,inventory:{},pending:null}},data),stages=new Map(),context={progress,scene:{data:scene,prefab:p=>scene.prefabs[p.toLowerCase()]},npcs:{data:{roles:{...portraits.roles,...npcs.roles}}},effects:{preflight:plan=>preflightConstructionStoryEffects(effects,plan)}},tasks=[];
for(const quest of data.quests){const id=Number(quest.id),stageId=progress.plotStageId(id);progress.state.questId=progress.state.viewQuestId=id;let result;
 try{if(stageId<1)throw Error('源PlotIndex没有该任务阶段');if(!stages.has(stageId))stages.set(stageId,await loadNativeConstructionPlotStage(stageId,{fetch:fetcher}));const checked=NativeConstruction.prototype.preflight.call(context,id,stages.get(stageId));result={questId:id,chapter:Number(quest.chapte),stageId,referencesAvailable:checked.ok,missing:checked.missing,warnings:checked.warnings};}
 catch(error){result={questId:id,chapter:Number(quest.chapte),stageId,referencesAvailable:false,missing:[error.message]};}tasks.push(result);
}
const first=tasks.find(row=>!row.referencesAvailable),report={scope:'Static reference availability only; does not certify unplayed tasks or native particle arithmetic.',quests:tasks.length,plotStages:stages.size,referencesAvailable:tasks.filter(row=>row.referencesAvailable).length,firstUnavailable:first,availableConsecutiveBeforeFirst:tasks.findIndex(row=>!row.referencesAvailable),tasks};
await fs.mkdir(path.join(root,'outputs/construction-audit'),{recursive:true});await fs.writeFile(path.join(root,'outputs/construction-audit/all-task-availability.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({...report,tasks:undefined}));
