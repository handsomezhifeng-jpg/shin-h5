import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {NativeConstructionProgress} from '../src/construction-native-progress.mjs';
import {NativeConstructionPlot,createNativeConstructionPlotPlan,loadNativeConstructionPlotStage,normalizeNativeDialogue} from '../src/construction-native-plot.mjs';
const read=name=>JSON.parse(fs.readFileSync(new URL('../assets/construction/config/'+name+'.json',import.meta.url),'utf8')).rows;
const DATA={quests:read('Data/Common/MainQuestVo'),playerExp:read('Common/PlayerExp'),playerExpGroups:read('Common/PlayerExpIDGroup'),baseParams:read('Data/Common/BaseParamsVo'),schedule:read('Data/Common/MainQuestScheduleVo'),unitUnlock:read('Data/Map/world_1/UnitUnlockVo'),unit31:read('Data/Map/world_1/Unit31Vo'),unitSkin:read('Data/Map/world_1/UnitSkinVo'),plotIndex:read('Data/Plot/Main/PlotIndexVo')};
const STAGE={plot:read('Data/Plot/Main/stage_1/PlotVo'),dialogue:read('Data/Plot/Main/stage_1/PlotDialogueVo'),animation:read('Data/Plot/Main/stage_1/PlotAnimationVo'),standPoints:read('Data/Plot/Main/stage_1/PlotStandPointVo')};
const clock=()=>Date.parse('2026-11-01T04:00:00Z');
const fresh=()=>{const engine={state:{coins:10000,level:1}},progress=new NativeConstructionProgress(engine,DATA,{clock});return{engine,progress};};
const hooks=extra=>({pause:async()=>{},loadStage:async()=>STAGE,dialogue:async(lines,{onAdvance})=>onAdvance(lines.length),animation:async()=>{},choice:async()=>2,unlock:async()=>{},chapterPopup:async()=>{},effect:async()=>{},...extra});
const customStage=type=>({...STAGE,plot:[{id:999,groupId:100001,subId:1,plotType:type,performId:74,performParams:'',status:1}]});

test('原解锁后固定等待.25秒；收尾黑幕完成才推进viewQuest，收尾中断可续且不重发奖',async()=>{
 const{engine,progress}=fresh();progress.submit(1);const coins=engine.state.coins,waits=[];let entered,release;
 const arrived=new Promise(resolve=>entered=resolve),footer=new Promise(resolve=>release=resolve);
 const first=new NativeConstructionPlot(progress,hooks({pause:async seconds=>waits.push(seconds),finish:async()=>{entered();await footer;}}));
 const playing=first.play();await arrived;assert.deepEqual(waits,[.25]);assert.equal(progress.viewQuestId,1);assert.equal(progress.pending.cursor,4);first.dispose();assert.equal((await playing).cancelled,true);assert.equal(progress.viewQuestId,1);assert.equal(engine.state.coins,coins);release();
 let footerCount=0;const resumed=new NativeConstructionPlot(progress,hooks({finish:async()=>footerCount++}));assert.equal((await resumed.play()).ok,true);assert.equal(footerCount,1);assert.equal(progress.viewQuestId,2);assert.equal(progress.pending,null);assert.equal(engine.state.coins,coins);
 const reviewWaits=[];await new NativeConstructionPlot(progress,hooks({pause:async seconds=>reviewWaits.push(seconds)})).play({reviewQuestId:1});assert.deepEqual(reviewWaits,[]);assert.equal(engine.state.coins,coins);
});

test('首章7个原任务的完整plot subId顺序与建设目标一致',()=>{
 const{progress}=fresh(),types=[[2,1,2,3],[2,3,2,1,2,1,2,1,2],[2,1,2,1,2,3],[2,3,2,1,2,1,2,1],[2,3,2,1,2,1],[2,1,2,3],[2,1,2,1,2,1,2,1,2,10,4]],units=['0_11833','0_11749','0_11754','0_11753','0_13010','0_13009','1_12939'];
 for(let i=0;i<7;i++){const plan=createNativeConstructionPlotPlan(progress,i+1,STAGE);assert.equal(plan.stageId,1);assert.deepEqual(plan.steps.map(step=>step.type),types[i]);assert.equal(plan.steps.find(step=>step.unlocks)?.unlocks[0].unitId,units[i]);assert.equal(plan.standPoint.id,100001+i);}
});
test('三选一数字130按UnlockVo.index、空参数按type6下个阈值，复合ID保留',()=>{
 const{progress}=fresh();let plan=createNativeConstructionPlotPlan(progress,1,STAGE);assert.equal(plan.steps.at(-1).unlock.index,130);assert.equal(plan.steps.at(-1).unlock.unitId,'0_11833');
 plan=createNativeConstructionPlotPlan(progress,2,STAGE);assert.equal(plan.steps.find(step=>step.type===3).unlock.index,85);
 const stage={...STAGE,plot:STAGE.plot.map(row=>row.groupId===100001&&row.plotType===3?{...row,performParams:'0_11749'}:row)};assert.equal(createNativeConstructionPlotPlan(progress,1,stage).steps.at(-1).unlock.unitId,'0_11749');
});
test('runner逐步执行动画/逐句对话/选择/锤子，完整结束才更新viewQuest',async()=>{
 const{engine,progress}=fresh();progress.submit(1);const coins=engine.state.coins,events=[];
 const runner=new NativeConstructionPlot(progress,hooks({animation:async(lines,ctx)=>events.push('animation:'+ctx.step.performId),dialogue:async(lines,{startIndex,onAdvance})=>{assert.equal(startIndex,0);for(let i=1;i<=lines.length;i++)onAdvance(i);events.push('dialogue');},choice:async unlock=>{events.push('choice:'+unlock.unitId);return 3;},unlock:async(unlocks,ctx)=>{events.push('hammer:'+unlocks[0].unitId);assert.equal(ctx.fromChoice,true);assert.equal(progress.viewQuestId,1);},onChange:()=>events.push('save')}));
 const result=await runner.play();assert.equal(result.ok,true);assert.equal(progress.viewQuestId,2);assert.equal(progress.pending,null);assert.equal(progress.recordSkin('0_11833'),3);assert.equal(engine.state.coins,coins);assert.deepEqual(events.filter(event=>event!=='save'),['animation:10100','dialogue','animation:10101','choice:0_11833','hammer:0_11833']);
});
test('首章连续7任务均可完成，章节popup先于固定区域解锁',async()=>{
 const{progress}=fresh(),events=[];const runner=new NativeConstructionPlot(progress,hooks({chapterPopup:async ctx=>events.push(['chapter',ctx.questId]),unlock:async(unlocks,ctx)=>events.push(['unlock',ctx.questId,unlocks[0].unitId])}));
 for(let quest=1;quest<=7;quest++){assert.equal(progress.submit(quest).ok,true);assert.equal((await runner.play()).ok,true);}assert.equal(progress.questId,8);assert.equal(progress.viewQuestId,8);assert.deepEqual(events.slice(-2),[['chapter',7],['unlock',7,'1_12939']]);
});
test('逐句对话取消保留原step和下一句下标，刷新从该句续播',async()=>{
 const{engine,progress}=fresh();progress.submit();let runner;
 runner=new NativeConstructionPlot(progress,hooks({dialogue:async(lines,{onAdvance})=>{onAdvance(1);runner.cancel();}}));assert.equal((await runner.play()).cancelled,true);assert.equal(progress.pending.cursor,1);assert.equal(progress.pending.dialogueIndex,1);
 const restored=new NativeConstructionProgress(engine,DATA,{clock});let resumed=-1;
 const next=new NativeConstructionPlot(restored,hooks({dialogue:async(lines,{startIndex,onAdvance})=>{resumed=startIndex;onAdvance(lines.length);}}));assert.equal((await next.play()).ok,true);assert.equal(resumed,1);assert.equal(restored.viewQuestId,2);
});
test('选择确认后锤子中断会恢复选择，刷新只续锤子且不重复选择或扣费',async()=>{
 const{engine,progress}=fresh();progress.submit();let runner,choices=0;
 runner=new NativeConstructionPlot(progress,hooks({choice:async()=>{choices++;return 3;},unlock:async()=>runner.cancel()}));assert.equal((await runner.play()).cancelled,true);assert.equal(choices,1);assert.equal(progress.pending.choice.style,3);const coins=engine.state.coins;
 const restored=new NativeConstructionProgress(engine,DATA,{clock});const next=new NativeConstructionPlot(restored,hooks({choice:async()=>assert.fail('confirmed choice must not reopen')}));assert.equal((await next.play()).ok,true);assert.equal(restored.recordSkin('0_11833'),3);assert.equal(engine.state.coins,coins);
});
test('review不扣费、不奖励、不更新任何任务或选择状态，历史三选一跳过',async()=>{
 const{engine,progress}=fresh();progress.submit();progress.finishPlot();const before=structuredClone(engine.state);let choices=0;
 const runner=new NativeConstructionPlot(progress,hooks({choice:async()=>{choices++;return 2;}}));const result=await runner.play({reviewQuestId:1});assert.equal(result.review,true);assert.equal(choices,0);assert.deepEqual(engine.state,before);
});
test('缺少执行hook或未知type会带任务/step上下文报错并停留原step',async()=>{
 const{progress}=fresh();progress.submit();let runner=new NativeConstructionPlot(progress,{loadStage:async()=>STAGE});await assert.rejects(runner.play(),error=>error.questId===1&&error.plotType===2&&/animation/.test(error.message));assert.equal(progress.pending.cursor,0);
 runner=new NativeConstructionPlot(progress,hooks({loadStage:async()=>customStage(99)}));await assert.rejects(runner.play(),error=>error.questId===1&&error.stepId===999&&error.plotType===99);assert.equal(progress.pending.cursor,0);assert.equal(progress.viewQuestId,1);
});
test('原type12音乐必须通过effect执行，不能默默跳过',async()=>{
 const{progress}=fresh();progress.submit();let called;
 const runner=new NativeConstructionPlot(progress,hooks({loadStage:async()=>customStage(12),effect:async(step,ctx)=>{called={id:step.bgmId,kind:step.kind,quest:ctx.questId};}}));await runner.play();assert.deepEqual(called,{id:74,kind:'bgm',quest:1});assert.equal(progress.viewQuestId,2);
});
test('原空建设/空动画按已核实的Lua返回，空对话仍经过UI hook',async()=>{
 for(const type of [2,3,4]){
  const{engine}=fresh(),progress=new NativeConstructionProgress(engine,{...DATA,unitUnlock:[]},{clock});progress.submit();
  const stage={...customStage(type),animation:[]};const plan=createNativeConstructionPlotPlan(progress,1,stage);assert.equal(plan.warnings.length,1);
  const runner=new NativeConstructionPlot(progress,{loadStage:async()=>stage});assert.equal((await runner.play()).ok,true);assert.equal(progress.viewQuestId,2);
 }
 const{progress}=fresh();progress.submit();let entered=false;
 const runner=new NativeConstructionPlot(progress,{loadStage:async()=>({...customStage(1),dialogue:[]}),dialogue:async lines=>{entered=true;assert.deepEqual(lines,[]);}});assert.equal((await runner.play()).ok,true);assert.equal(entered,true);
});
test('原task136空三选一保留warning并正常完成，不虚构建设选择',async()=>{
 const{progress}=fresh();progress.state.questId=136;progress.state.viewQuestId=136;progress.submit(136);let choices=0;
 const runner=new NativeConstructionPlot(progress,hooks({choice:async()=>{choices++;return 2;}}));assert.equal((await runner.play()).ok,true);assert.equal(choices,0);assert.equal(progress.viewQuestId,137);assert.equal(runner.plan.warnings.length,1);
});
test('已核实的原type5/6空分支明确标记sourceNoop，其他未知类型仍报错',async()=>{
 for(const type of [5,6]){const{progress}=fresh();progress.submit();const runner=new NativeConstructionPlot(progress,{loadStage:async()=>customStage(type)});assert.equal((await runner.play()).ok,true);assert.equal(runner.plan.steps[0].sourceNoop,true);assert.equal(progress.viewQuestId,2);}
});
test('dispose能中止忽略signal的异步hook，迟到resolve和onAdvance不推进',async()=>{
 const{progress}=fresh();progress.submit();let entered,resolveHook;const started=new Promise(resolve=>entered=resolve);
 const runner=new NativeConstructionPlot(progress,hooks({animation:()=>new Promise(resolve=>{resolveHook=resolve;entered();})}));const playing=runner.play();await started;runner.dispose();assert.equal((await playing).cancelled,true);assert.equal(progress.pending.cursor,0);resolveHook();await Promise.resolve();assert.equal(progress.pending.cursor,0);assert.equal((await runner.play()).cancelled,true);
});
test('同runner或同progress重复play受保护，原调用仍可安全取消',async()=>{
 const{progress}=fresh();progress.submit();let entered;const started=new Promise(resolve=>entered=resolve);
 const runner=new NativeConstructionPlot(progress,hooks({animation:()=>new Promise(()=>entered())}));const playing=runner.play();await started;await assert.rejects(runner.play(),/正在播放/);await assert.rejects(new NativeConstructionPlot(progress,hooks()).play(),/正在播放/);runner.cancel();assert.equal((await playing).cancelled,true);
});
test('已结束对话的迟到回调不会污染后续动画/选择位置',async()=>{
 const{progress}=fresh();progress.submit();let oldAdvance;
 const runner=new NativeConstructionPlot(progress,hooks({dialogue:async(lines,{onAdvance})=>{oldAdvance=onAdvance;onAdvance(lines.length);},animation:async(lines,{step})=>{if(step.performId===10101){oldAdvance(1);assert.equal(progress.pending.cursor,2);assert.equal(progress.pending.dialogueIndex,0);}}}));await runner.play();assert.equal(progress.viewQuestId,2);
});
test('原对话效果type和参数按并列分号解析，动画保持原rows并附坐标',()=>{
 const row=normalizeNativeDialogue({desc_zh_CN:'原文',effectTypesBefore:'14;15',effectParamsBefore:'bg_path;74'});assert.deepEqual(row.effectsBefore,[{type:14,name:'BG',params:'bg_path'},{type:15,name:'BGM',params:'74'}]);
 const{progress}=fresh(),plan=createNativeConstructionPlotPlan(progress,1,STAGE);const animation=plan.steps[0].rows.find(row=>row.camPos!=='');assert.ok(Array.isArray(animation.cameraPosition));
});
test('按stageId读取四张源表，读取失败不能推进任务',async()=>{
 const paths=[];await loadNativeConstructionPlotStage(2,{fetch:async(url,{signal})=>{paths.push(String(url));return{ok:true,json:async()=>({rows:[]})};}});assert.equal(paths.length,4);assert.ok(paths.every(path=>path.includes('stage_2/')));
 const{progress}=fresh();progress.submit();const runner=new NativeConstructionPlot(progress,hooks({loadStage:async()=>{throw Error('missing table');}}));await assert.rejects(runner.play(),/missing table/);assert.equal(progress.pending.cursor,0);
});
test('对话skip成为整段剧情状态，后续只保留最后BGM、动画传skip，建设仍执行',async()=>{
 const{progress}=fresh();progress.submit();const stage={...STAGE,plot:[
  {id:1,groupId:100001,subId:1,plotType:1,performId:1,performParams:''},
  {id:2,groupId:100001,subId:2,plotType:2,performId:2,performParams:''},
  {id:3,groupId:100001,subId:3,plotType:1,performId:3,performParams:''},
  {id:4,groupId:100001,subId:4,plotType:3,performId:'',performParams:130},
  {id:5,groupId:100001,subId:5,plotType:4,performId:'',performParams:130}],
  dialogue:[{id:1,groupId:1,dialogueId:1,desc:'skip here'},{id:2,groupId:3,dialogueId:1,effectTypesBefore:15,effectParamsBefore:74},{id:3,groupId:3,dialogueId:2,effectTypesBefore:15,effectParamsBefore:75,effectTypesOn:15,effectParamsOn:76}],animation:[{id:1,groupId:2,order:1,blackSwitch:1}]};
 const calls=[];const runner=new NativeConstructionPlot(progress,hooks({loadStage:async()=>stage,dialogue:async()=>{calls.push('dialogue');return{skipped:true};},animation:async(rows,ctx)=>{assert.equal(ctx.skip,true);calls.push('animation-black-only');},effect:async step=>calls.push('bgm:'+step.bgmId),choice:async()=>{calls.push('choice');return 1;},unlock:async()=>calls.push('unlock')}));
 assert.equal((await runner.play()).ok,true);assert.deepEqual(calls,['dialogue','animation-black-only','bgm:76','choice','unlock','unlock']);
});
test('skip中断后刷新仍保持源skip，不重新显示后续对话',async()=>{
 const{engine,progress}=fresh();progress.submit();let runner;
 runner=new NativeConstructionPlot(progress,hooks({dialogue:async()=>({skipped:true}),animation:async(rows,ctx)=>{if(ctx.step.performId===10101)runner.cancel();}}));assert.equal((await runner.play()).cancelled,true);assert.equal(progress.pending.skip,true);
 const restored=new NativeConstructionProgress(engine,DATA,{clock});assert.equal(restored.pending.skip,true);let skipped;
 const resumed=new NativeConstructionPlot(restored,hooks({dialogue:async()=>assert.fail('source skip must survive reload'),animation:async(rows,ctx)=>skipped=ctx.skip}));assert.equal((await resumed.play()).ok,true);assert.equal(skipped,true);
});
