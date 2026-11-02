// Reconstructed from PlotMgr.AwaitPlay and PerformScripts.PlayMainPlot.
const ROOT=new URL('../assets/construction/config/',import.meta.url);
const rows=value=>(Array.isArray(value)?value:value?.rows||[]).filter(row=>row.status!==0);
const list=value=>value===''||value==null?[]:String(value).split(';');
const vector=value=>{if(value===''||value==null||value==='nil')return null;const v=Array.isArray(value)?value:String(value).split(',').map(Number);return v.length===2&&v.every(Number.isFinite)?v:null;};
const clone=value=>JSON.parse(JSON.stringify(value));
const KINDS={1:'dialogue',2:'animation',3:'choice',4:'unlock',5:'source-noop',6:'source-noop',7:'world',8:'plot-good',9:'cg',10:'chapter-popup',11:'activity-skin',12:'bgm'};
const activeRunners=new WeakMap();
const EFFECT_NAMES={1:'Memory',2:'CameraShake',3:'EyesOpen',4:'EyesClose',5:'EyesCloseOpen',6:'BlackFadeIn',7:'BlackFadeOut',8:'BlackFadeInOut',9:'SmallRain',10:'BigRain',11:'BlackFade',12:'SpineFx',13:'CG',14:'BG',15:'BGM'};

export class NativeConstructionPlotError extends Error {
  constructor(message,context={},cause){super(message,{cause});this.name='NativeConstructionPlotError';this.context=context;Object.assign(this,context);}
}
const abortError=()=>Object.assign(new Error('建设剧情已取消'),{name:'AbortError'});
function effects(types,params){const values=list(params);return list(types).map((type,index)=>({type:Number(type),name:EFFECT_NAMES[Number(type)]||null,params:values[index]??''}));}
export function normalizeNativeDialogue(row){return {...row,text:String(row.desc_zh_CN??row.desc??''),alias:String(row.alias_zh_CN??row.alias??''),effectsBefore:effects(row.effectTypesBefore,row.effectParamsBefore),effectsOn:effects(row.effectTypesOn,row.effectParamsOn)};}
export function normalizeNativeAnimation(row){return {...row,cameraPosition:vector(row.camPos),rolePosition:vector(row.rolePos),roleTargetPosition:vector(row.roleTargetPos),roleFloorNum:Number(row.floor)||1,roleActionTime:row.roleActionTime===''||row.roleActionTime==null?-1:Number(row.roleActionTime),blackSwitch:Number(row.blackSwitch)||0};}

export async function loadNativeConstructionPlotStage(stageId,{fetch:fetcher=globalThis.fetch,root=ROOT,signal}={}){
  stageId=Number(stageId);if(!Number.isSafeInteger(stageId)||stageId<1)throw new NativeConstructionPlotError('原剧情阶段无效',{stageId});
  const paths={plot:`Data/Plot/Main/stage_${stageId}/PlotVo`,dialogue:`Data/Plot/Main/stage_${stageId}/PlotDialogueVo`,animation:`Data/Plot/Main/stage_${stageId}/PlotAnimationVo`,standPoints:`Data/Plot/Main/stage_${stageId}/PlotStandPointVo`};
  return Object.fromEntries(await Promise.all(Object.entries(paths).map(async([key,path])=>{
    const response=await fetcher(new URL(path+'.json',root),{signal});
    if(!response.ok)throw new NativeConstructionPlotError('原剧情表读取失败：'+path,{stageId,table:path});
    return [key,rows(await response.json())];
  })));
}

function resolveUnlocks(progress,quest,row){
  const all=progress.data.unitUnlock,params=row.performParams==null?'':String(row.performParams),tokens=params===''?[]:params.split(',').filter(Boolean);
  if(!tokens.length){const type=Number(row.plotType)===8?7:6,target=Number(row.plotType)===8?Number(row.performId):Number(quest.id)+1;return {unlocks:all.filter(unlock=>Number(unlock.unlockType)===type&&Number(unlock.unlockNum)===target),warnings:[]};}
  const result=[],warnings=[];
  for(const token of Number(row.plotType)===3?tokens.slice(0,1):tokens){
    // Modern tokens are UnitUnlockVo.index. Legacy composite unit IDs use MapConfigMgr selection.
    const unlock=token.includes('_')&&Number(row.plotType)!==8?progress.selectedUnlock(token):all.find(unlock=>String(unlock.index)===token);
    if(!unlock){warnings.push({message:'原建设解锁记录不存在；原Lua记录错误后继续',context:{questId:Number(quest.id),stepId:Number(row.id),plotType:Number(row.plotType),token}});continue;}
    result.push(unlock);
  }
  return {unlocks:result,warnings};
}

export function createNativeConstructionPlotPlan(progress,questId,stageData){
  questId=Number(questId);const quest=progress.quests.get(questId);
  if(!quest)throw new NativeConstructionPlotError('原主线任务不存在',{questId});
  const stageId=progress.plotStageId(questId),plotId=Number(quest.plotId);
  const source=rows(stageData.plot??stageData.PlotVo).filter(row=>Number(row.groupId)===plotId).sort((a,b)=>Number(a.subId)-Number(b.subId));
  if(!source.length)throw new NativeConstructionPlotError('原剧情分组不存在',{questId,stageId,plotId});
  const dialogue=rows(stageData.dialogue??stageData.PlotDialogueVo),animation=rows(stageData.animation??stageData.PlotAnimationVo);
  const steps=source.map((row,index)=>{
    const type=Number(row.plotType),context={questId,stageId,plotId,stepIndex:index,stepId:Number(row.id),plotType:type};
    const step={...row,...context,type,kind:KINDS[type]||'unsupported',performParams:row.performParams==null?'':String(row.performParams)};
    if(type===1){step.rows=dialogue.filter(line=>Number(line.groupId)===Number(row.performId)).sort((a,b)=>Number(a.dialogueId)-Number(b.dialogueId)).map(normalizeNativeDialogue);if(!step.rows.length){step.sourceEmptyDialogue=true;step.warnings=[{message:'原对话分组为空；原Lua仍执行对话进出场',context}];}}
    if(type===2){step.rows=animation.filter(line=>Number(line.groupId)===Number(row.performId)).sort((a,b)=>Number(a.order)-Number(b.order)||Number(a.id)-Number(b.id)).map(normalizeNativeAnimation);if(!step.rows.length){step.sourceEmptyAnimation=true;step.warnings=[{message:'原动画分组为空；AnimationTimeline.AwaitPlay直接返回',context}];}}
    if([3,4,8].includes(type)){
      const resolved=resolveUnlocks(progress,quest,row);step.unlocks=resolved.unlocks;step.warnings=resolved.warnings;
      if(!step.unlocks.length){step.warnings.push({message:'原建设解锁分组为空；原Lua按空列表返回',context});step.sourceEmptyUnlock=true;}
      if(type===3)step.unlock=step.unlocks[0];
    }
    if(type===7)step.worldId=Number(row.performId);
    if(type===8)step.itemId=Number(row.performId);
    if(type===9){step.cgId=Number(row.performId);step.waitSeconds=Number(row.performParams)||0;step.cg=rows(stageData.cg??progress.data.plotCG).find(cg=>Number(cg.id)===step.cgId)||null;}
    if(type===11)step.skinGoodsId=Number(row.performId);
    if(type===12)step.bgmId=Number(row.performId);
    if(type===5||type===6){step.sourceNoop=true;step.noopReason='PlotMgr.AwaitPlay original branch has no statements';}
    if(type===10){step.popupId='TransitionNewAreaUnlockPopup';step.showSeconds=2.5;step.afterSeconds=.5;}
    return step;
  });
  return {questId,stageId,plotId,quest,standPoint:rows(stageData.standPoints??stageData.PlotStandPointVo).find(row=>Number(row.id)===plotId)||null,steps,errors:steps.filter(step=>step.error).map(step=>step.error),warnings:steps.flatMap(step=>step.warnings||[]),evidence:['PlotMgr.AwaitPlay','PerformScripts.PlayMainPlot','MainQuestMgr.GetPlotStageId']};
}

export class NativeConstructionPlot {
  constructor(progress,hooks={}){this.progress=progress;this.hooks=hooks;this.running=false;this.disposed=false;this.controller=null;this.cache=new Map();this.plan=null;}
  dispose(){this.disposed=true;this.controller?.abort();}
  cancel(){this.controller?.abort();}
  async wait(value,signal){
    if(signal.aborted)throw abortError();
    let listener;
    const cancelled=new Promise((_,reject)=>{listener=()=>reject(abortError());signal.addEventListener('abort',listener,{once:true});});
    try{return await Promise.race([Promise.resolve(value),cancelled]);}finally{signal.removeEventListener('abort',listener);}
  }
  async hook(name,args,context){
    const fn=this.hooks[name];if(typeof fn!=='function')throw new NativeConstructionPlotError('缺少原剧情执行接口：'+name,context.step||context);
    return this.wait(fn(...args,context),context.signal);
  }
  changed(){this.hooks.onChange?.(this.progress.snapshot());}
  async pause(seconds,context){if(typeof this.hooks.pause==='function')return this.hook('pause',[seconds],context);return this.wait(new Promise(resolve=>setTimeout(resolve,seconds*1000)),context.signal);}
  ensureActive(context){
    if(context.signal.aborted||this.disposed)throw abortError();
    if(!context.review&&this.progress.pending?.completedQuestId!==context.questId)throw new NativeConstructionPlotError('执行中的原任务剧情状态已改变',context);
  }
  async play({reviewQuestId}={}){
    if(this.disposed)return {ok:false,cancelled:true};
    if(this.running||activeRunners.has(this.progress))throw new NativeConstructionPlotError('原剧情正在播放',{reason:'already-running'});
    const review=reviewQuestId!=null,questId=review?Number(reviewQuestId):this.progress.pending?.completedQuestId;
    if(!questId)return {ok:false,reason:'no-pending'};
    this.running=true;activeRunners.set(this.progress,this);const controller=this.controller=new AbortController(),signal=controller.signal;
    let currentStep=null;
    try{
      const stageId=this.progress.plotStageId(questId),base={questId,stageId,review,signal};
      let stage=this.cache.get(stageId);
      if(!stage){stage=await this.wait((this.hooks.loadStage||loadNativeConstructionPlotStage)(stageId,{signal}),signal);this.cache.set(stageId,stage);}
      this.ensureActive(base);
      const plan=this.plan=createNativeConstructionPlotPlan(this.progress,questId,stage);
      let cursor=review?0:this.progress.pending.cursor;
      let skip=review?false:this.progress.pending.skip===true;
      if(!Number.isSafeInteger(cursor)||cursor<0||cursor>plan.steps.length)throw new NativeConstructionPlotError('原剧情存档位置无效',{...base,cursor});
      for(;cursor<plan.steps.length;cursor++){
        currentStep=plan.steps[cursor];const context={...base,plotId:plan.plotId,step:currentStep,skip},stepCursor=cursor,step=currentStep;
        this.ensureActive(context);
        const type=currentStep.type;
        if(currentStep.error&&!(type===3&&(review||questId<this.progress.viewQuestId)))throw new NativeConstructionPlotError(currentStep.error.message,currentStep.error.context);
        if(type===1){
          if(skip){
            let bgmId=null;
            for(let line=currentStep.rows.length-1;line>=0&&bgmId==null;line--){const row=currentStep.rows[line];for(const effect of [...row.effectsBefore,...row.effectsOn].reverse())if(effect.type===15){bgmId=Number(effect.params);break;}}
            if(bgmId!=null)await this.hook('effect',[{...currentStep,type:12,plotType:12,kind:'bgm',bgmId,performId:bgmId,source:'skipped-dialogue-last-bgm'}],context);
          }else{
          const startIndex=review?0:this.progress.pending.dialogueIndex;
          if(startIndex>currentStep.rows.length)throw new NativeConstructionPlotError('原对话存档位置无效',currentStep);
          if(!currentStep.rows.length||startIndex<currentStep.rows.length){const result=await this.hook('dialogue',[currentStep.rows,{...context,startIndex,onAdvance:nextIndex=>{
            if(signal.aborted||review||this.disposed||this.progress.pending?.cursor!==stepCursor)return;
            this.ensureActive(context);
            if(!Number.isSafeInteger(nextIndex)||nextIndex<startIndex||nextIndex>step.rows.length)throw new NativeConstructionPlotError('原对话回调位置无效',step);
            if(this.progress.advancePlot(stepCursor,nextIndex))this.changed();
          }}],context);if(result?.skipped===true){skip=true;if(!review){this.progress.pending.skip=true;this.changed();}}}
          }
        }else if(type===2){
          if(currentStep.rows.length)await this.hook('animation',[currentStep.rows],context);
        }else if(type===3){
          if(currentStep.unlock&&!review&&!(questId<this.progress.viewQuestId)){
            const unlock=currentStep.unlock,chosen=this.progress.pending.choice;
            const alreadyChosen=chosen?.cursor===cursor&&chosen.unitId===String(unlock.unitId)&&chosen.style===this.progress.recordSkin(unlock.unitId);
            if(!alreadyChosen){
              const previousStyle=this.progress.recordSkin(unlock.unitId);
              const result=await this.hook('choice',[unlock],context);this.ensureActive(context);
              const style=typeof result==='number'?result:result?.style??result?.skin??this.progress.recordSkin(unlock.unitId);
              const confirmed=this.progress.confirmSkin(unlock.unitId,style);
              if(!confirmed.ok)throw new NativeConstructionPlotError('原三选一尚未确认',currentStep);
              this.progress.pending.choice={cursor,unitId:String(unlock.unitId),style,previousStyle};this.changed();
            }
            // PlayUnit31Unlock always runs the source unlock / hammer after confirmation.
            await this.hook('unlock',[[unlock]],{...context,fromChoice:true});
          }
          if(!review&&!(questId<this.progress.viewQuestId))await this.pause(.25,context);
        }else if(type===4){
          if(currentStep.unlocks.length)await this.hook('unlock',[currentStep.unlocks],context);
          await this.pause(.25,context);
        }else if(type===10){
          await this.hook('chapterPopup',[],context);
        }else if(type===8){
          if(currentStep.unlocks.length)await this.hook('unlock',[currentStep.unlocks],context);this.ensureActive(context);
          if(!review){this.progress.recordPlotGood(currentStep.itemId);this.changed();}
          await this.pause(.25,context);
        }else if(type===5||type===6){
          // These two recognized branches are empty in the shipped PlotMgr.
        }else if((type===7||type===9)&&skip){
          // Original PlotMgr wraps world-switch and CG branches in `not self.skip`.
        }else if([7,9,11,12].includes(type)){
          await this.hook('effect',[currentStep],context);
          if(type===11)await this.pause(.25,context);
        }else{
          throw new NativeConstructionPlotError('尚未实现的原剧情类型',currentStep);
        }
        this.ensureActive(context);
        if(!review){this.progress.advancePlot(cursor+1,0);this.changed();}
      }
      this.ensureActive({...base,plotId:plan.plotId});
      if(typeof this.hooks.finish==='function')await this.hook('finish',[plan],{...base,plotId:plan.plotId});
      this.ensureActive({...base,plotId:plan.plotId});
      if(!review){this.progress.finishPlot();this.changed();}
      return {ok:true,review,questId,plotId:plan.plotId,steps:plan.steps.length};
    }catch(error){
      if(signal.aborted||error?.name==='AbortError')return {ok:false,cancelled:true,review,questId};
      if(error instanceof NativeConstructionPlotError)throw error;
      throw new NativeConstructionPlotError('原剧情执行失败：'+(error?.message||String(error)),currentStep||{questId},error);
    }finally{
      if(activeRunners.get(this.progress)===this)activeRunners.delete(this.progress);
      if(this.controller===controller)this.controller=null;
      this.running=false;
    }
  }
}
