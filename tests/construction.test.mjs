import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import{BoardGame}from '../src/engine.mjs';
import{ConstructionProgress,CONSTRUCTION_BUILDINGS}from '../src/construction-progress.mjs';
const context={window:{}};vm.runInNewContext(fs.readFileSync(new URL('../game-data.js',import.meta.url),'utf8'),context);
const fresh=()=>new BoardGame(context.window.GAME_DATA);
test('装修确认沿用棋盘原成本/等级/招募奖励，预览不改存档',()=>{
 const e=fresh(),p=new ConstructionProgress(e),before=e.snapshot(),cost=e.buildingCost(0),preview=p.scene({index:0,skin:2});
 assert.equal(preview.skins[CONSTRUCTION_BUILDINGS[0].unit],2);assert.deepEqual(e.snapshot(),before);
 const r=p.commit(0,2);assert.equal(r.cost,cost);assert.equal(e.state.coins,before.coins-cost);assert.equal(e.state.buildings[0].level,1);assert.equal(e.state.gacha,before.gacha+1);assert.equal(p.skin(0),2);
 const restored=new BoardGame(context.window.GAME_DATA,e.snapshot());assert.equal(new ConstructionProgress(restored).skin(0),2);
});
test('余额不足、棋盘事件、错误选择和满级都不扣款',()=>{
 const e=fresh(),p=new ConstructionProgress(e);e.state.coins=0;let before=e.snapshot();assert.ok(p.commit(0,1).error);assert.deepEqual(e.snapshot(),before);
 e.state.coins=100000;e.state.pending={kind:'chance',bet:1,card:{type:3,param:10}};before=e.snapshot();assert.ok(p.commit(0,1).error);assert.deepEqual(e.snapshot(),before);
 e.state.pending=null;for(const args of [[-1,1],[0,0],[5,1],[0,4],[0.5,1]]){before=e.snapshot();assert.ok(p.commit(...args).error);assert.deepEqual(e.snapshot(),before);}
 e.state.buildings[0].level=e.maxBuildLevel;before=e.snapshot();assert.ok(p.commit(0,3).error);assert.deepEqual(e.snapshot(),before);
});
test('修缮沿用原维修折扣且不会重复增加建筑等级或招募币',()=>{
 const e=fresh(),p=new ConstructionProgress(e);e.state.buildings[0]={level:2,damaged:true};const before=e.snapshot(),cost=e.buildingCost(0),r=p.commit(0,3);assert.equal(r.repaired,true);assert.equal(e.state.coins,before.coins-cost);assert.equal(e.state.buildings[0].level,2);assert.equal(e.state.buildings[0].damaged,false);assert.equal(e.state.gacha,before.gacha);assert.equal(p.skin(0),3);
});
test('旧存档可用；外观按地图隔离；坏外观值不污染游戏进度',()=>{
 const e=fresh();e.state.buildings[0].level=1;const p=new ConstructionProgress(e);assert.equal(p.skin(0),1);p.map.skins[CONSTRUCTION_BUILDINGS[0].unit]=3;e.state.map=2;assert.equal(p.skin(0),1);e.state.map=1;assert.equal(p.skin(0),3);
 e.state.construction.maps['1'].skins[CONSTRUCTION_BUILDINGS[0].unit]='<invalid>';assert.equal(p.skin(0),1);assert.equal(e.state.buildings[0].level,1);
});
test('完成原五栋建筑后仍可按原条件换图',()=>{
 const e=fresh(),p=new ConstructionProgress(e);e.state.coins=10000000;for(let i=0;i<5;i++)for(let j=0;j<e.maxBuildLevel;j++)assert.ok(!p.commit(i,j%3+1).error);assert.equal(p.next,null);assert.ok(e.canUpgradeMap);assert.ok(e.upgradeMap());assert.equal(e.state.map,2);assert.equal(p.next,0);assert.equal(p.skin(0),0);assert.equal(e.state.construction.maps['1'].skins[CONSTRUCTION_BUILDINGS[0].unit],3);
});
