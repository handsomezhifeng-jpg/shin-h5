import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {NativeConstructionProgress,loadNativeConstructionData,nativeScheduleTime} from '../src/construction-native-progress.mjs';
const read=name=>JSON.parse(fs.readFileSync(new URL('../assets/construction/config/'+name+'.json',import.meta.url),'utf8')).rows;
const DATA={quests:read('Data/Common/MainQuestVo'),playerExp:read('Common/PlayerExp'),playerExpGroups:read('Common/PlayerExpIDGroup'),baseParams:read('Data/Common/BaseParamsVo'),schedule:read('Data/Common/MainQuestScheduleVo'),unitUnlock:read('Data/Map/world_1/UnitUnlockVo'),unit31:read('Data/Map/world_1/Unit31Vo'),unitSkin:read('Data/Map/world_1/UnitSkinVo'),plotIndex:read('Data/Plot/Main/PlotIndexVo'),items:read('Data/Common/CommonItemVo'),unitBounds:read('Data/Map/world_1/UnitBoundsVo')};
const clock=()=>Date.parse('2026-11-01T04:00:00Z');
const fresh=(data=DATA,saved={})=>{const engine={state:{coins:10000,level:1,buildings:[{level:4}],construction:{version:1,maps:{'1':{skins:{'0_11749':3}}}},...structuredClone(saved)}};return{engine,p:new NativeConstructionProgress(engine,data,{clock})};};

test('原表loader使用全部必要表，CN排期按北京时间解释',async()=>{
 const calls=[],data=await loadNativeConstructionData({fetch:async url=>{calls.push(String(url));return{ok:true,json:async()=>({rows:[{id:1}]})};}});
 assert.equal(calls.length,12);assert.equal(data.quests[0].id,1);assert.ok(calls.some(url=>url.includes('PlayerExpIDGroup')));assert.ok(calls.some(url=>url.includes('AvatarVo')));
 assert.equal(nativeScheduleTime('2026/11/1 12:00'),clock());assert.ok(Number.isNaN(nativeScheduleTime('bad')));
});
test('旧存档独立创建原任务状态，保留已有建设与棋盘等级',()=>{
 const{engine,p}=fresh(DATA,{level:31});assert.equal(p.questId,1);assert.equal(p.viewQuestId,1);assert.equal(p.cost,26);assert.equal(engine.state.level,31);
 assert.deepEqual(engine.state.buildings,[{level:4}]);assert.equal(engine.state.construction.maps['1'].skins['0_11749'],3);assert.deepEqual(p.state.skins,{});
 assert.equal(p.state.unlockChapterSource,'local-cn-schedule');assert.ok(p.state.unlockChapterId>3);
});
test('提交即时扣费用和经验，保留原viewQuest直到整个剧情结束',()=>{
 const{engine,p}=fresh(),before=engine.state.coins,r=p.submit(1);assert.equal(r.ok,true);assert.equal(r.cost,26);assert.equal(engine.state.coins,before-26);assert.equal(p.mainExp,15);assert.equal(p.questId,2);assert.equal(p.viewQuestId,1);
 assert.deepEqual(p.pending,{completedQuestId:1,plotId:100001,cursor:0,dialogueIndex:0});assert.equal(p.advancePlot(2,3),true);assert.equal(p.advancePlot(1,0),false);
 p.finishPlot();assert.equal(p.viewQuestId,2);assert.equal(p.pending,null);assert.equal(p.chapter,1);
});
test('pending刷新、重复提交和迟到回调均不会再扣费或发奖',()=>{
 const{engine,p}=fresh();p.submit(1);p.advancePlot(3,2);p.confirmSkin('0_11833',2);const before=structuredClone(engine.state);
 const restored=new NativeConstructionProgress(engine,DATA,{clock});assert.deepEqual(restored.pending,{completedQuestId:1,plotId:100001,cursor:3,dialogueIndex:2});assert.equal(restored.recordSkin('0_11833'),2);assert.equal(restored.submit(1).reason,'pending');assert.deepEqual(engine.state,before);
 restored.finishPlot();const coins=engine.state.coins,exp=restored.mainExp;assert.equal(restored.submit(1).reason,'stale-quest');assert.equal(engine.state.coins,coins);assert.equal(restored.mainExp,exp);
});
test('剧情呈现快照随同一步恢复，保留角色与已解锁摆件；异步旧步快照不采用',()=>{
 const{engine,p}=fresh();p.submit(1);p.advancePlot(3,0);p.confirmSkin('0_11833',2);p.pending.choice={cursor:3,unitId:'0_11833',style:2,previousStyle:0};
 p.pending.presentation={version:1,cursor:3,camera:{x:-5.1,y:-8.57,orthographicSize:7},plotOverrides:{'1_12939':{visible:true},bad:{visible:true}},npcs:{version:1,storyMode:true,actors:[{binding:{id:'plot:1002',role:'q_npc_1002',roleId:1002,x:-4.57,y:-9.75,z:0,action:'happy',dir:1,rootScale:1,floor:1},animation:'happy',currentAnimation:'happy_loop',trackTime:1.25,timeScale:1},{binding:{id:'bad',role:'http://invalid'},trackTime:0}]}};
 const coins=engine.state.coins,restored=new NativeConstructionProgress(engine,DATA,{clock});assert.equal(restored.pending.choice.previousStyle,0);assert.deepEqual(restored.pending.presentation.camera,{x:-5.1,y:-8.57,orthographicSize:7});assert.deepEqual(restored.pending.presentation.plotOverrides,{'1_12939':{visible:true}});assert.equal(restored.pending.presentation.npcs.actors.length,1);assert.equal(restored.pending.presentation.npcs.actors[0].trackTime,1.25);assert.equal(engine.state.coins,coins);
 restored.pending.presentation.cursor=2;const again=new NativeConstructionProgress(engine,DATA,{clock});assert.equal(again.pending.presentation,undefined);assert.equal(again.submit().reason,'pending');assert.equal(engine.state.coins,coins);
});
test('原nextId链允许非连续任务id，章节取原chapte，最后任务只可提交一次',()=>{
 const data={...DATA,quests:[{id:1,nextId:8,chapte:1,plotId:1,coinConsume:1,exp:1},{id:8,nextId:0,chapte:4,plotId:2,coinConsume:2,exp:1}]};
 const{p}=fresh(data);p.submit();p.finishPlot();assert.equal(p.questId,8);assert.equal(p.chapter,4);p.submit();p.finishPlot();assert.equal(p.allFinished,true);assert.equal(p.submit().reason,'finished');
});
test('金币不足、棋盘事件和无效任务不修改余额、经验、库存',()=>{
 const{engine,p}=fresh();engine.state.coins=25;let before=structuredClone(engine.state);assert.equal(p.submit().reason,'insufficient-coins');assert.deepEqual(engine.state,before);
 engine.state.coins=100;engine.state.pending={kind:'chance'};before=structuredClone(engine.state);assert.equal(p.submit().reason,'board-event');assert.deepEqual(engine.state,before);
});
test('费用完整遵循BaseParams18=2、19=3，首章原价26/16/24/46/25/24/24',()=>{
 const{p}=fresh();assert.deepEqual(DATA.quests.slice(0,7).map(q=>p.questCost(q.id)),[26,16,24,46,25,24,24]);p.state.unlockChapterId=2;assert.equal(p.questCost(1),78);p.state.unlockChapterId=3;assert.equal(p.questCost(1),26);
});
test('预览不写存档；复合单位ID确认与重装修均零消耗，刷新保留选择',()=>{
 const{engine,p}=fresh();const before=structuredClone(engine.state),scene=p.sceneState({preview:{unitId:'0_11749',style:3}});assert.equal(scene.skins['0_11749'],3);assert.deepEqual(engine.state,before);
 assert.equal(p.confirmSkin('0_11749',2).cost,0);assert.equal(p.confirmSkin('0_11749',3).cost,0);assert.equal(engine.state.coins,before.coins);assert.equal(p.mainExp,0);assert.equal(p.questId,1);
 const restored=new NativeConstructionProgress(engine,DATA,{clock});assert.equal(restored.recordSkin('0_11749'),3);assert.equal(restored.sceneState().skins['0_11749'],3);assert.equal(restored.confirmSkin('11749',2).ok,false);assert.equal(restored.confirmSkin('0_11749',4).ok,false);
});
test('MapMgr默认皮肤保持原prefab；阈值后3选1默认1、参数0保留skin0',()=>{
 const{p}=fresh();let scene=p.sceneState();assert.equal(scene.units['0_11749'].visible,true);assert.equal(scene.units['0_11749'].sourceDefault,true);assert.equal('0_11749'in scene.skins,false);
 p.state.viewQuestId=3;scene=p.sceneState();assert.equal(scene.skins['0_11749'],1);
 const data={...DATA,unitUnlock:[{index:1,unitId:'0_11749',unlockType:6,unlockNum:1,unlockActive:2,unlockActiveParam:'0'}]};const q=fresh(data).p;assert.equal(q.sceneState().skins['0_11749'],0);
});
test('同unit多条解锁按viewQuest选择，active0出现/active1消失/type7剧情物品持久化',()=>{
 const data={...DATA,unit31:[],unitSkin:[],unitUnlock:[{index:1,unitId:'0_a',unlockType:6,unlockNum:2,unlockActive:0},{index:2,unitId:'0_a',unlockType:6,unlockNum:4,unlockActive:1},{index:3,unitId:'0_b',unlockType:7,unlockNum:500001,unlockActive:0}]};
 const{engine,p}=fresh(data);assert.equal(p.sceneState().visible['0_a'],false);p.state.viewQuestId=2;assert.equal(p.sceneState().visible['0_a'],true);p.state.viewQuestId=4;assert.equal(p.sceneState().visible['0_a'],false);assert.equal(p.sceneState().prefabs['0_a'],false);
 p.recordPlotGood(500001);assert.equal(p.sceneState().visible['0_b'],true);assert.equal(new NativeConstructionProgress(engine,data,{clock}).sceneState().visible['0_b'],true);
});
test('累计经验边界30/75与多档跳升遵循原oldLevel一行奖励，host等级不降低',()=>{
 const{engine,p}=fresh(DATA,{level:40});assert.equal(p.addExp(29).newLevel,1);const r=p.addExp(1);assert.equal(r.newLevel,2);assert.equal(p.levelProgress().exp,0);assert.equal(p.levelProgress().required,45);assert.equal(engine.state.inventory['31101'],1);
 const rewardBefore=structuredClone(engine.state.inventory);const jump=p.addExp(200);assert.equal(jump.oldLevel,2);assert.equal(jump.newLevel,5);assert.equal(engine.state.inventory['30601'],1);assert.equal(engine.state.inventory['10201'],1);assert.equal(engine.state.inventory['30403'],undefined);assert.equal(engine.state.level,40);assert.equal(engine.state.inventory['31101'],rewardBefore['31101']);
});
test('首章配置奖励进入原itemId库存，不伪造服务端随机掉落',()=>{
 const{engine,p}=fresh();for(let id=1;id<=4;id++){assert.equal(p.submit(id).ok,true);p.finishPlot();}assert.equal(engine.state.inventory['20601'],1);assert.equal(engine.state.nativeConstruction.rewardSource,'offline-static-config');
});
test('升级事件先发奖再保留pending弹窗，刷新及已展示标记不重复奖励',()=>{
 const{engine,p}=fresh();p.submit(1);p.finishPlot();const result=p.submit(2);assert.equal(result.levelUp.newLevel,2);assert.deepEqual(p.pending.levelUp,result.levelUp);assert.equal(p.pending.levelUpShown,false);const inventory=structuredClone(engine.state.inventory);
 let restored=new NativeConstructionProgress(engine,DATA,{clock});assert.equal(restored.pending.levelUp.newLevel,2);assert.deepEqual(engine.state.inventory,inventory);restored.pending.levelUpShown=true;restored=new NativeConstructionProgress(engine,DATA,{clock});assert.equal(restored.pending.levelUpShown,true);assert.deepEqual(engine.state.inventory,inventory);
});
