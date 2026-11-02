// Source: MainQuestMgr, PlayerDojo/ConfigModule, MapMgr/MapConfigMgr,
// PerformScripts.PlayMainPlot, and the APK's recovered SettingV2 tables.
const CONFIG_ROOT = new URL('../assets/construction/config/', import.meta.url);
const TABLES = {
  quests:'Data/Common/MainQuestVo', playerExp:'Common/PlayerExp',
  playerExpGroups:'Common/PlayerExpIDGroup', baseParams:'Data/Common/BaseParamsVo',
  schedule:'Data/Common/MainQuestScheduleVo', unitUnlock:'Data/Map/world_1/UnitUnlockVo',
  unit31:'Data/Map/world_1/Unit31Vo', unitSkin:'Data/Map/world_1/UnitSkinVo',
  plotIndex:'Data/Plot/Main/PlotIndexVo', items:'Data/Common/CommonItemVo',
  unitBounds:'Data/Map/world_1/UnitBoundsVo',avatars:'Data/Common/AvatarVo'
};
const clone = value => JSON.parse(JSON.stringify(value));
const positive = (value, fallback=0) => Number.isSafeInteger(Number(value)) && Number(value)>=0 ? Number(value) : fallback;
const active = rows => (Array.isArray(rows) ? rows : rows?.rows || []).filter(row=>row.status!==0);
const rewardsOf = row => {
  if (!row || row.rewardId==='' || row.rewardId==null) return [];
  const ids=String(row.rewardId).split(';'), counts=String(row.rewardNum ?? '').split(';');
  return ids.map((id,i)=>({itemId:positive(id),goodsId:positive(id),count:positive(counts[i]),goodsNum:positive(counts[i])})).filter(r=>r.itemId>0&&r.count>0);
};
// Original CN client dates carry no timezone suffix; interpret them as Beijing time.
export function nativeScheduleTime(value) {
  const match=/^(\d{4})\/(\d{1,2})\/(\d{1,2})\s+(\d{1,2}):(\d{2})$/.exec(String(value));
  return match ? Date.UTC(+match[1],+match[2]-1,+match[3],+match[4]-8,+match[5]) : NaN;
}
export async function loadNativeConstructionData({fetch:fetcher=globalThis.fetch,root=CONFIG_ROOT}={}) {
  const entries=await Promise.all(Object.entries(TABLES).map(async([key,path])=>{
    const response=await fetcher(new URL(path+'.json',root));
    if(!response.ok)throw Error('建设原配置读取失败：'+path);
    return [key,active(await response.json())];
  }));
  return Object.fromEntries(entries);
}

export class NativeConstructionProgress {
  constructor(engine,data,{clock=Date.now}={}) {
    if(!engine?.state)throw TypeError('NativeConstructionProgress requires engine.state');
    this.engine=engine;this.clock=clock;
    this.data=Object.fromEntries(Object.keys(TABLES).map(key=>[key,active(data?.[key])]));
    this.quests=new Map(this.data.quests.map(row=>[Number(row.id),row]));
    this.unlocks=new Map();
    for(const row of this.data.unitUnlock){const id=String(row.unitId);if(!this.unlocks.has(id))this.unlocks.set(id,[]);this.unlocks.get(id).push(row);}
    this.threeChoice=new Set(this.data.unit31.map(row=>String(row.unitId)));
    this.activitySkin=new Set(this.data.unitSkin.map(row=>String(row.unitId)));
    this.expThresholds=this.data.playerExpGroups.map(row=>({level:Number(row.id),total:Number(row.total)})).filter(row=>Number.isFinite(row.total)).sort((a,b)=>a.level-b.level);
    if(!this.expThresholds.length){let total=0;this.expThresholds=this.data.playerExp.slice().sort((a,b)=>a.lv-b.lv).map(row=>{const result={level:Number(row.lv),total};total+=Number(row.exp)||0;return result;});}
    const saved=engine.state.nativeConstruction;
    const initial=this.quests.has(1)?1:Number(this.data.quests[0]?.id)||1;
    const questId=positive(saved?.questId,initial);
    const validQuest=this.quests.has(questId)||saved?.allFinished===true;
    const state={version:1,questId:validQuest?questId:initial,viewQuestId:positive(saved?.viewQuestId,initial)||initial,
      mainExp:positive(saved?.mainExp),roleLevel:1,skins:{},plotGoods:{},pending:null,completed:[],allFinished:validQuest&&saved?.allFinished===true,
      unlockChapterId:0,unlockChapterSource:'local-cn-schedule',rewardSource:'offline-static-config'};
    state.roleLevel=this.levelForExp(state.mainExp);
    if(state.viewQuestId>state.questId||!this.quests.has(state.viewQuestId))state.viewQuestId=state.questId;
    for(const[id,style]of Object.entries(saved?.skins||{}))if(this.threeChoice.has(id)&&[1,2,3].includes(style))state.skins[id]=style;
    for(const[id,count]of Object.entries(saved?.plotGoods||{}))if(positive(count))state.plotGoods[id]=positive(count);
    state.completed=[...new Set((Array.isArray(saved?.completed)?saved.completed:[]).map(Number).filter(id=>this.quests.has(id)))];
    const pending=saved?.pending, completedQuest=this.quests.get(Number(pending?.completedQuestId));
    if(completedQuest&&Number(pending.plotId)===Number(completedQuest.plotId)&&state.questId!==Number(completedQuest.id)){
      state.pending={completedQuestId:Number(completedQuest.id),plotId:Number(completedQuest.plotId),cursor:positive(pending.cursor),dialogueIndex:positive(pending.dialogueIndex)};
      if(pending.choice?.cursor===state.pending.cursor&&this.threeChoice.has(String(pending.choice.unitId))&&state.skins[String(pending.choice.unitId)]===pending.choice.style)state.pending.choice={cursor:pending.choice.cursor,unitId:String(pending.choice.unitId),style:pending.choice.style,previousStyle:[0,1,2,3].includes(pending.choice.previousStyle)?pending.choice.previousStyle:0};
      if(pending.levelUp&&positive(pending.levelUp.oldLevel)>0&&positive(pending.levelUp.newLevel)>positive(pending.levelUp.oldLevel)&&positive(pending.levelUp.newLevel)<=state.roleLevel){state.pending.levelUp=clone(pending.levelUp);state.pending.levelUpShown=pending.levelUpShown===true;}
      if(pending.skip===true)state.pending.skip=true;
      const presentation=pending.presentation;
      if(presentation?.version===1&&presentation.cursor===state.pending.cursor){
        const restored={version:1,cursor:state.pending.cursor,plotOverrides:{}};
        if([presentation.camera?.x,presentation.camera?.y,presentation.camera?.orthographicSize].every(Number.isFinite)&&presentation.camera.orthographicSize>0)restored.camera={x:presentation.camera.x,y:presentation.camera.y,orthographicSize:presentation.camera.orthographicSize};
        for(const[id,value]of Object.entries(presentation.plotOverrides||{}))if(/^\d+_\d+$/.test(id)){const v={};if(typeof value?.visible==='boolean')v.visible=value.visible;if(Number.isSafeInteger(value?.skin)&&value.skin>=0)v.skin=value.skin;restored.plotOverrides[id]=v;}
        if(presentation.npcs?.version===1&&Array.isArray(presentation.npcs.actors)){restored.npcs={version:1,storyMode:presentation.npcs.storyMode===true,actors:presentation.npcs.actors.filter(r=>/^q_npc_\d+$/.test(r.binding?.role)&&/^(?:plot|idle):\d+$/.test(r.binding?.id)&&[r.binding.x,r.binding.y,r.binding.rootScale,r.trackTime].every(Number.isFinite)).map(r=>({binding:Object.fromEntries(['id','role','roleId','x','y','z','action','dir','rootScale','floor'].map(k=>[k,r.binding[k]])),animation:String(r.animation||'idle01'),currentAnimation:typeof r.currentAnimation==='string'?r.currentAnimation:null,trackTime:Math.max(0,r.trackTime),timeScale:Number(r.timeScale)>0?Number(r.timeScale):1}))};}
        state.pending.presentation=restored;
      }
      if(!state.completed.includes(Number(completedQuest.id)))state.completed.push(Number(completedQuest.id));
    }
    const available=this.data.schedule.filter(row=>nativeScheduleTime(row.cnStartDay)<=Number(clock())).map(row=>Number(row.cnUnlock)).filter(Number.isFinite);
    state.unlockChapterId=Math.max(0,positive(saved?.unlockChapterId),...available);
    engine.state.nativeConstruction=state;
    engine.state.level=Math.max(positive(engine.state.level,1),state.roleLevel);
  }
  get state(){return this.engine.state.nativeConstruction;}
  get questId(){return this.state.questId;}
  get currentQuest(){return this.quests.get(this.questId)||null;}
  get currentQuestId(){return this.questId;}
  get viewQuestId(){return this.state.viewQuestId;}
  get pending(){return this.state.pending;}
  get chapter(){return Number(this.currentQuest?.chapte)||0;}
  get roleLevel(){return this.state.roleLevel;}
  get mainExp(){return this.state.mainExp;}
  get allFinished(){return this.state.allFinished;}
  snapshot(){return clone(this.state);}
  levelForExp(exp){let level=1;for(const row of this.expThresholds)if(exp>=row.total)level=row.level;return level;}
  levelProgress(){const row=this.expThresholds.find(row=>row.level===this.roleLevel),vo=this.data.playerExp.find(row=>Number(row.lv)===this.roleLevel);return{level:this.roleLevel,exp:this.mainExp-(row?.total||0),total:this.mainExp,required:Number(vo?.exp)||0};}
  questCost(questId=this.questId){const quest=this.quests.get(Number(questId));if(!quest)return 0;const param=id=>Number(this.data.baseParams.find(row=>Number(row.id)===id)?.num)||0;return Number(quest.coinConsume||0)*(Number(quest.chapte)+param(18)>this.state.unlockChapterId?param(19):1);}
  get cost(){return this.questCost();}
  plotStageId(questId=this.questId){return Number(this.data.plotIndex.find(row=>Number(questId)<=Number(row.toQuestId))?.id)||-1;}
  isCompleted(questId){return Number(questId)<this.questId||this.state.completed.includes(Number(questId));}
  grantItem(itemId,count){
    if(!(count>0))return;
    if(itemId===102){this.engine.state.coins+=count;return;}
    this.engine.state.inventory||={};
    const key=String(itemId);this.engine.state.inventory[key]=positive(this.engine.state.inventory[key])+count;
  }
  addExp(amount){
    const oldExp=this.mainExp,oldLevel=this.roleLevel;
    this.state.mainExp+=positive(amount);this.state.roleLevel=this.levelForExp(this.mainExp);
    this.engine.state.level=Math.max(positive(this.engine.state.level,1),this.roleLevel);
    // PlayerDojo.PlayerMainExp grants the old-level row once, even on a multi-level jump.
    const rewards=this.roleLevel!==oldLevel?rewardsOf(this.data.playerExp.find(row=>Number(row.lv)===oldLevel)):[];
    for(const reward of rewards)this.grantItem(reward.itemId,reward.count);
    return {oldExp,oldLevel,newLevel:this.roleLevel,exp:this.mainExp,rewards};
  }
  submit(expectedQuestId=this.questId){
    const fail=(reason,error)=>({ok:false,reason,error});
    if(this.pending)return fail('pending','请先完成当前剧情');
    if(this.engine.state.pending)return fail('board-event','请先完成棋盘事件');
    if(Number(expectedQuestId)!==this.questId)return fail('stale-quest','任务已更新');
    const quest=this.currentQuest;
    if(!quest||this.allFinished)return fail('finished','当前任务已全部完成');
    if(this.state.completed.includes(this.questId))return fail('already-submitted','任务已提交');
    const cost=this.questCost();
    if(!Number.isFinite(cost)||cost<0)return fail('invalid-cost','原任务费用无效');
    if(this.engine.state.coins<cost)return fail('insufficient-coins','铜钱不足');
    const completedQuestId=this.questId,next=Number(quest.nextId),rewards=rewardsOf(quest);
    this.engine.state.coins-=cost;
    const levelUp=this.addExp(Number(quest.exp)||0);
    for(const reward of rewards){if(reward.itemId===104)this.addExp(reward.count);else this.grantItem(reward.itemId,reward.count);}
    this.state.completed.push(completedQuestId);
    this.state.questId=this.quests.has(next)?next:completedQuestId+1;
    this.state.allFinished=!this.quests.has(next);
    this.state.pending={completedQuestId,plotId:Number(quest.plotId),cursor:0,dialogueIndex:0};
    if(levelUp.newLevel!==levelUp.oldLevel){this.state.pending.levelUp=clone(levelUp);this.state.pending.levelUpShown=false;}
    return {ok:true,completedQuest:quest,completedQuestId,nextQuest:this.currentQuest,cost,exp:Number(quest.exp)||0,rewards,levelUp,pending:clone(this.pending),rewardSource:'offline-static-config'};
  }
  advancePlot(cursor,dialogueIndex=0){
    if(!this.pending||!Number.isSafeInteger(cursor)||cursor<0||!Number.isSafeInteger(dialogueIndex)||dialogueIndex<0)return false;
    if(cursor<this.pending.cursor||cursor===this.pending.cursor&&dialogueIndex<this.pending.dialogueIndex)return false;
    if(cursor!==this.pending.cursor)delete this.pending.choice;
    this.pending.cursor=cursor;this.pending.dialogueIndex=dialogueIndex;return true;
  }
  finishPlot(){
    if(!this.pending)return {ok:false,reason:'no-pending'};
    const completedQuestId=this.pending.completedQuestId;
    // PerformScripts updates viewQuest only after PlayCommonPlot has finished.
    this.state.viewQuestId=this.questId;this.state.pending=null;
    return {ok:true,completedQuestId,questId:this.questId,viewQuestId:this.viewQuestId};
  }
  confirmSkin(unitId,style){
    unitId=String(unitId);
    if(!this.threeChoice.has(unitId)||![1,2,3].includes(style))return {ok:false,reason:'invalid-skin',error:'请选择原建设样式'};
    this.state.skins[unitId]=style;return {ok:true,unitId,style,skin:style,cost:0};
  }
  recordSkin(unitId){return this.state.skins[String(unitId)]||0;}
  resolveUnlockSkin(row){
    const id=String(row.unitId),record=this.recordSkin(id),param=row.unlockActiveParam,explicit=param!==''&&param!=null;
    if(Number(row.unlockActive)===0){if(explicit)return Number(param);if(record>0)return record;if(this.activitySkin.has(id))return 0;if(this.threeChoice.has(id))return 1;return null;}
    if(Number(row.unlockActive)===2)return this.threeChoice.has(id)?record:Number(param)||0;
    return null;
  }
  recordPlotGood(itemId){const id=positive(itemId);if(!id)return false;this.state.plotGoods[String(id)]=1;return true;}
  selectedUnlock(unitId){
    const rows=this.unlocks.get(String(unitId))||[];
    if(rows.length<2||Number(rows[0].unlockType)!==6)return rows[0]||null;
    const sorted=rows.slice().sort((a,b)=>Number(a.unlockNum)-Number(b.unlockNum)||Number(a.refId||0)-Number(b.refId||0));
    let selected=sorted[0];for(const row of sorted){if(this.viewQuestId>=Number(row.unlockNum))selected=row;else break;}return selected;
  }
  unlocked(row){
    if(!row)return true;
    const threshold=Number(row.unlockNum);
    switch(Number(row.unlockType)){
      case 1:return this.roleLevel>=threshold;
      case 2:return this.engine.state.coins>=threshold;
      case 3:return positive(this.engine.state.inventory?.['103'])>=threshold;
      case 4:return this.questId>=threshold;
      case 5:return positive(this.engine.state.inventory?.[String(row.unlockNum)])>0;
      case 6:return this.viewQuestId>=threshold;
      case 7:return positive(this.state.plotGoods?.[String(row.unlockNum)])>0;
      default:return false;
    }
  }
  sceneState({preview=null}={}){
    const ids=new Set([...this.unlocks.keys(),...this.threeChoice,...this.activitySkin,...this.data.unitBounds.map(row=>String(row.id))]);
    const skins={},prefabs={},visible={},units={};
    for(const id of ids){
      const unlock=this.selectedUnlock(id),unlocked=this.unlocked(unlock),choice=this.threeChoice.has(id);
      const loaded=choice&&!unlock?false:!unlock||unlocked&&Number(unlock.unlockActive)===0||!unlocked&&Number(unlock.unlockActive)===1||Number(unlock.unlockActive)===2;
      let skin=this.recordSkin(id)||null;
      if(skin===null&&unlocked&&choice&&unlock)skin=String(unlock.unlockActiveParam)==='0'?0:1;
      if(!this.recordSkin(id)&&unlocked&&this.activitySkin.has(id))skin=0;
      if(skin!==null)skins[id]=skin;
      visible[id]=!!loaded;if(!loaded)prefabs[id]=false;
      units[id]={visible:!!loaded,unlocked,skin,sourceDefault:skin===null,unlockIndex:unlock?.index??null};
    }
    const previewId=preview?.unitId??preview?.unit,previewStyle=preview?.style??preview?.skin;
    if(previewId!=null&&this.threeChoice.has(String(previewId))&&[1,2,3].includes(previewStyle)){
      const id=String(previewId);skins[id]=previewStyle;visible[id]=true;delete prefabs[id];units[id]={...units[id],visible:true,skin:previewStyle,sourceDefault:false,preview:true};
    }
    return {skins,prefabs,visible,units,questId:this.questId,viewQuestId:this.viewQuestId};
  }
}
