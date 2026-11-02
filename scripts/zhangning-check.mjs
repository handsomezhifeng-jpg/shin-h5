import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
const {chromium}=createRequire(import.meta.url)('C:/Users/zhfzhang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
const out='outputs/zhangning';await fs.mkdir(out,{recursive:true});const records=[],errors=[],missing=[];
try{
 for(const key of ['a','b','c']){
  const page=await browser.newPage({viewport:{width:375,height:812}});page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=400&&!r.url().endsWith('favicon.ico'))missing.push(r.url());});
  await page.goto(`http://127.0.0.1:3577/dist/?boardSkin=sanguo&hero=${key}`,{waitUntil:'networkidle'});await page.waitForFunction(()=>window.__SHIN?.player?.character==='张宁');
  const record=await page.evaluate(()=>{const h=__SHIN,p=h.player,s=h.scene;const unique=new Set(p.frames.map(f=>f.canvas.toDataURL())).size;const directions=[];p.animationState.timeScale=0;
   for(const sign of [1,-1])for(let i=0;i<40;i++){const from=s.centerWorld(i),to=s.centerWorld((i+sign+40)%40),d=p.setTravel(from,to);p.setAnimation('walk_'+(d.back?'b':'f'));p.animationState.tracks[0].trackTime=.2;p.render();directions.push({...d,frame:p.frameIndex});}
   const poses=[];for(const name of ['idle_f','idle_b','walk_f','walk_b','jump_f']){p.direction={back:name.endsWith('_b'),flip:false};p.setAnimation(name);p.animationState.tracks[0].trackTime=0;p.render();const data=p.ctx.getImageData(0,0,300,340).data;let top=340,bottom=0,left=300,right=0;for(let y=0;y<340;y++)for(let x=0;x<300;x++)if(data[(y*300+x)*4+3]>127){top=Math.min(top,y);bottom=Math.max(bottom,y);left=Math.min(left,x);right=Math.max(right,x);}poses.push({name,height:(bottom-top+1)/2,screenHeight:(bottom-top+1)/2*5.5/s.zoom/2,left,right,top,bottom});}
   return {variant:p.variant,character:p.character,unique,poses,directions,portrait:h.sanguoCast.portraitURLs[3],squares:s.data.squares.length};});
  assert.equal(record.variant,key);assert.equal(record.unique,4);assert.equal(record.squares,40);assert(record.portrait.endsWith(`/zhangning/${key}-portrait.png`));
  for(const d of record.directions){assert.equal(d.back,d.dz>0);assert.equal(d.frame>=4,d.back);assert.equal(d.back?!d.flip:d.flip,d.dx>0);}
  for(const p of record.poses){assert(Math.abs(p.height-133)<4,JSON.stringify(p));assert(p.left>0&&p.right<299&&p.top>0,'Character must not clip');}
  for(const sign of [1,-1])await page.evaluate(async sign=>{const h=__SHIN,s=h.scene,p=h.player;h.engine.state.position=8;s.moving=false;s.setPiece(8,document.querySelector('#piece'));s.follow(8,true);p.animationState.timeScale=1.5;await s.move([8+sign,8+sign*2,8+sign*3],document.querySelector('#piece'),i=>h.engine.state.position=i);},sign);
  for(const pose of ['idle_f','idle_b','walk_f']){await page.evaluate(pose=>{const s=__SHIN.scene,p=__SHIN.player;s.stopFollow();s.setPiece(12,document.querySelector('#piece'));s.follow(12,true);s.cast.timeOverride=0;if(s.environment.residents)s.environment.residents.timeOverride=0;p.animationState.timeScale=0;p.direction={back:pose.endsWith('_b'),flip:false};p.setAnimation(pose);p.animationState.tracks[0].trackTime=0;p.render();s.draw();},pose);await page.screenshot({path:`${out}/${key}-${pose}-375.png`});}
  await page.setViewportSize({width:750,height:1624});await page.screenshot({path:`${out}/${key}-750.png`});records.push(record);await page.close();
 }
 const original=await browser.newPage();original.on('pageerror',e=>errors.push(e.message));await original.goto('http://127.0.0.1:3577/dist/?boardSkin=original',{waitUntil:'networkidle'});await original.waitForFunction(()=>window.__SHIN);assert.equal(await original.evaluate(()=>!!__SHIN.player.isSanguo),false);await original.close();
 assert.deepEqual(errors,[]);assert.deepEqual(missing,[]);await fs.writeFile(`${out}/verification.json`,JSON.stringify({records,errors,missing},null,2));console.log(JSON.stringify({variants:3,uniquePosesEach:4,directionCases:240,movementPaths:6,portraitAndOriginal:true,errors,missing}));
}finally{await browser.close();}
