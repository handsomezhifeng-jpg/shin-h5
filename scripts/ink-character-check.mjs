import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const {chromium}=createRequire(import.meta.url)('C:/Users/zhfzhang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
try{
 const page=await browser.newPage({viewport:{width:750,height:1624}}),errors=[],missing=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=400&&!r.url().endsWith('favicon.ico'))missing.push(r.url());});
 await page.goto(process.env.SHIN_PREVIEW_URL||'http://127.0.0.1:4483/?boardSkin=sanguo',{waitUntil:'networkidle'});
 await page.waitForFunction(()=>window.__SHIN?.scene?.environment?.villagers?.length===9);
 const result=await page.evaluate(()=>{
  const h=__SHIN,s=h.scene,p=h.player,c=h.sanguoCast;
  c.timeOverride=0;p.animationState.timeScale=0;s.stopFollow();s.setPiece(12,document.querySelector('#piece'));s.follow(12,true);
  const poseHeights=[];
  for(const name of ['idle_f','idle_b']){p.setAnimation(name,true);p.render();const data=p.ctx.getImageData(0,0,300,340).data;let first=340,last=0;for(let y=0;y<340;y++)for(let x=0;x<300;x++)if(data[(y*300+x)*4+3]>127){first=Math.min(first,y);last=Math.max(last,y);}poseHeights.push({name,referencePixels:(last-first+1)/2});}
  s.draw();
  const distance=(x,z)=>Math.min(...Array.from({length:40},(_,i)=>{const q=s.centerWorld(i);return Math.hypot(q.x-x,q.z-z);}));
  return {poseHeights,npcs:c.npcs.map(n=>({id:n.id,height:n.h,x:n.x,z:n.z})),villagers:s.environment.villagers,oldClearance:distance(-3.3,1.7),newClearance:distance(c.npcs[2].x,c.npcs[2].z),tiles:s.data.squares.length};
 });
 for(const p of result.poseHeights)assert(Math.abs(p.referencePixels-133)<5,JSON.stringify(p));
 assert(result.npcs.every(n=>n.height===104));assert(result.villagers.every(n=>n.referenceHeight===104));assert.equal(result.villagers.length,9);assert.equal(result.tiles,40);
 assert(result.newClearance>result.oldClearance+.5,'General must stand farther from the board');
 const produce=result.villagers.find(p=>p.id==='produce-customer');assert(produce.position[1]<610);
 await page.screenshot({path:'outputs/ink-character-left-750.png'});
 await page.setViewportSize({width:375,height:812});await page.screenshot({path:'outputs/ink-character-left-375.png'});
 assert.deepEqual(errors,[]);assert.deepEqual(missing,[]);
 await fs.writeFile('outputs/ink-character-checks.json',JSON.stringify({result,errors,missing},null,2));
 console.log(JSON.stringify({people:13,playerHeight:133,surroundingHeight:104,playerPoses:result.poseHeights,oldClearance:result.oldClearance,newClearance:result.newClearance,errors,missing}));
}finally{await browser.close();}
