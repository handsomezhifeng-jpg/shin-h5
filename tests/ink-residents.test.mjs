import test from'node:test';import assert from'node:assert/strict';import fs from'node:fs';
import{MARKET_VISITS,sampleMarketVisit,sampleSweeper,sampleMarketResidents,sampleResidentPath,sampleSweeperAnimation}from'../src/ink-resident-rules.mjs';
test('四个购买位置逐次进场、购买、离开、空档后换人，同次购物保留身份',()=>{
 for(const d of MARKET_VISITS){const total=d.arrive+d.buy+d.leave+d.gap,at=(phase,cycle=2)=>sampleMarketVisit(d,cycle*total+phase-d.offset),a=at(d.arrive/2),b=at(d.arrive+d.buy/2),l=at(d.arrive+d.buy+d.leave/2),gap=at(total-d.gap/2),next=at(d.arrive/2,3);assert.equal(a.state,'arriving');assert.equal(b.state,'buying');assert.equal(l.state,'leaving');assert.equal(gap.state,'away');assert.equal(gap.visible,false);assert.equal(a.variant,b.variant);assert.equal(b.variant,l.variant);assert.notEqual(a.variant,next.variant);assert(a.visible&&b.visible&&l.visible);assert.deepEqual([b.x,b.y],d.path.at(-1));assert(a.frame<4&&l.frame>=4);}
});
test('四条往返路均在棋盘外，边界切换位置连续，空档期间不残留顾客',()=>{
 for(const d of MARKET_VISITS){for(let t=0;t<=1;t+=.005){const p=sampleResidentPath(d.path,t);assert(Math.abs((p.x-512)/404)+Math.abs((p.y-730)/256)>1.15,d.id+' crosses board');}const cycle=d.arrive+d.buy+d.leave+d.gap,at=t=>sampleMarketVisit(d,cycle+t-d.offset),pre=at(d.arrive-.0001),post=at(d.arrive+.0001);assert(Math.hypot(pre.x-post.x,pre.y-post.y)<.1);const depart=at(d.arrive+d.buy+.0001);assert(Math.hypot(depart.x-post.x,depart.y-post.y)<.1);for(let t=d.arrive+d.buy+d.leave+.01;t<cycle;t+=.5)assert.equal(at(t).visible,false);}
});
test('扫地18秒，走入开门的房间、休息14秒，再出门继续扫；回屋路与出门路连续',()=>{
 const work=sampleSweeper(2),patch=sampleSweeper(5),home=sampleSweeper(21),indoor=sampleSweeper(29),out=sampleSweeper(39),again=sampleSweeper(43);assert.equal(work.state,'sweeping');assert.equal(patch.state,'change-patch');assert.equal(home.state,'going-home');assert(home.doorOpen>.9);assert.equal(indoor.state,'indoors');assert.equal(indoor.visible,false);assert.equal(indoor.doorOpen,0);assert.equal(out.state,'coming-out');assert(out.visible);assert.equal(again.state,'sweeping');assert.equal(again.cycle,1);for(const boundary of[18,42]){const a=sampleSweeper(boundary-.00001),b=sampleSweeper(boundary+.00001);assert(Math.hypot(a.x-b.x,a.y-b.y)<.1);}for(let t=23;t<37;t+=.05)assert.equal(sampleSweeper(t).visible,false);
});
test('摊主随顾客招呼或整理货物，动作错峰，暂停/跳时采样无副作用',()=>{
 const a=sampleMarketResidents(0),b=sampleMarketResidents(2.5),c=sampleMarketResidents(0);assert.deepEqual(a,c);assert(a.vendors.some(v=>v.state==='serving'));assert(a.vendors.some(v=>v.state==='arranging'));assert(a.vendors.some((v,i)=>v.frame!==b.vendors[i].frame));assert.equal(a.visitors.length,4);assert.equal(a.vendors.length,4);
});

test('扫地与所有行走阶段采用所选20/24帧，按原序列节奏循环并随路线镜像',()=>{
 const {atlases}=JSON.parse(fs.readFileSync(new URL('../assets/scene/skins/ink/residents-seedance-sweeper-v1.json',import.meta.url),'utf8'));
 assert.equal(atlases.sweeperSweep.frames.length,20);assert.equal(atlases.sweeperWalk.frames.length,24);
 const seen={sweeperSweep:new Set(),sweeperWalk:new Set()},states=new Set();
 for(let t=0;t<84;t+=.01){const pose=sampleSweeper(t);if(!pose.visible)continue;const a=sampleSweeperAnimation(pose,atlases),clip=atlases[a.atlas];seen[a.atlas].add(a.frame);states.add(pose.state);assert(a.frame>=0&&a.frame<clip.frames.length);assert.equal(a.atlas,pose.walking?'sweeperWalk':'sweeperSweep');assert.equal(a.flip,pose.walking&&pose.faceRight);}
 assert.equal(seen.sweeperSweep.size,20);assert.equal(seen.sweeperWalk.size,24);assert(states.has('going-home')&&states.has('coming-out')&&states.has('change-patch'));
 for(const clip of Object.values(atlases)){const period=clip.frames.length/clip.fps;for(let f=0;f<clip.frames.length;f++){const pose={walking:clip===atlases.sweeperWalk,local:(f+.2)/clip.fps,faceRight:false},a=sampleSweeperAnimation(pose,atlases),loop=sampleSweeperAnimation({...pose,local:pose.local+period},atlases);assert.equal(a.frame,f);assert.equal(a.frame,loop.frame);}assert.equal(new Set(clip.frames.map(f=>f.bodyHeight)).size,1);assert.equal(new Set(clip.frames.map(f=>JSON.stringify(f.anchor))).size,1);}
});
