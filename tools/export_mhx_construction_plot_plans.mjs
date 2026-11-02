// Compact, source-linked plans for static checks; no game state or secrets included.
import fs from 'node:fs';
import path from 'node:path';
import{fileURLToPath}from 'node:url';
import{NativeConstructionProgress}from '../src/construction-native-progress.mjs';
import{createNativeConstructionPlotPlan}from '../src/construction-native-plot.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const config=path.join(root,'assets/construction/config');
const read=name=>JSON.parse(fs.readFileSync(path.join(config,name+'.json'),'utf8')).rows;
const data={quests:read('Data/Common/MainQuestVo'),unitUnlock:read('Data/Map/world_1/UnitUnlockVo'),unit31:read('Data/Map/world_1/Unit31Vo'),unitSkin:read('Data/Map/world_1/UnitSkinVo'),plotIndex:read('Data/Plot/Main/PlotIndexVo')};
const progress=new NativeConstructionProgress({state:{coins:0,level:1}},data);
const output=path.join(root,'assets/construction/plot-plans');fs.mkdirSync(output,{recursive:true});
const manifest={source:'SettingV2 original TSV/JSON; PlotMgr.AwaitPlay + PerformScripts.PlayMainPlot',stages:[],unmappedQuestIds:[],errors:[],warnings:[]};
for(const index of data.plotIndex){
 const stageId=Number(index.id),prefix=`Data/Plot/Main/stage_${stageId}/`;
 const stage={plot:read(prefix+'PlotVo'),dialogue:read(prefix+'PlotDialogueVo'),animation:read(prefix+'PlotAnimationVo'),standPoints:read(prefix+'PlotStandPointVo')};
 const plans=[];
 for(const quest of data.quests.filter(quest=>progress.plotStageId(quest.id)===stageId)){
  try{
   const plan=createNativeConstructionPlotPlan(progress,quest.id,stage);
   plans.push({questId:plan.questId,stageId,plotId:plan.plotId,name:quest.name_zh_CN??quest.name,chapter:quest.chapte,coinConsume:quest.coinConsume,exp:quest.exp,
    steps:plan.steps.map(step=>({stepId:step.stepId,subId:step.subId,type:step.type,kind:step.kind,performId:step.performId,performParams:step.performParams,
     ...(step.rows?{rowIds:step.rows.map(row=>row.id)}:{}),...(step.unlocks?{unlockIndexes:step.unlocks.map(unlock=>unlock.index),unitIds:step.unlocks.map(unlock=>String(unlock.unitId))}:{}),...(step.error?{error:step.error}:{}),...(step.warnings?.length?{warnings:step.warnings}:{}),...(step.type===10?{popupId:step.popupId,showSeconds:step.showSeconds,afterSeconds:step.afterSeconds}:{})})),errors:plan.errors,warnings:plan.warnings});
   manifest.errors.push(...plan.errors);
   manifest.warnings.push(...plan.warnings);
  }catch(error){manifest.errors.push({message:error.message,context:error.context||{questId:Number(quest.id),stageId}});}
 }
 fs.writeFileSync(path.join(output,`stage_${stageId}.json`),JSON.stringify({stageId,plans},null,2)+'\n');
 manifest.stages.push({stageId,file:`stage_${stageId}.json`,quests:plans.length,steps:plans.reduce((sum,plan)=>sum+plan.steps.length,0),errors:plans.reduce((sum,plan)=>sum+plan.errors.length,0),warnings:plans.reduce((sum,plan)=>sum+plan.warnings.length,0)});
}
manifest.unmappedQuestIds=data.quests.filter(quest=>progress.plotStageId(quest.id)<0).map(quest=>Number(quest.id));
fs.writeFileSync(path.join(output,'first-chapter.json'),JSON.stringify({stageId:1,plans:JSON.parse(fs.readFileSync(path.join(output,'stage_1.json'),'utf8')).plans.filter(plan=>Number(plan.chapter)===1)},null,2)+'\n');
fs.writeFileSync(path.join(output,'manifest.json'),JSON.stringify(manifest,null,2)+'\n');
console.log(JSON.stringify({stages:manifest.stages.length,quests:manifest.stages.reduce((sum,stage)=>sum+stage.quests,0),steps:manifest.stages.reduce((sum,stage)=>sum+stage.steps,0),sourceReferenceErrors:manifest.errors.length,sourceWarnings:manifest.warnings.length,unmappedQuestIds:manifest.unmappedQuestIds.length}));
