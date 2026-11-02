import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
const {chromium}=createRequire(import.meta.url)('C:/Users/zhfzhang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
const errors=[],missing=[],records=[];
try{
 for(const viewport of [{width:375,height:812},{width:390,height:844},{width:1440,height:900}]){
  const page=await browser.newPage({viewport});
  page.on('pageerror',e=>errors.push(e.message));
  page.on('response',r=>{if(r.status()>=400&&!r.url().endsWith('favicon.ico'))missing.push(r.url());});
  await page.goto(process.env.SHIN_PREVIEW_URL||'http://127.0.0.1:4483/dist/?boardSkin=sanguo',{waitUntil:'networkidle'});
  await page.waitForFunction(()=>window.__SHIN?.scene);
  const result=await page.evaluate(()=>{
   const s=__SHIN.scene,measure=()=>{
    const points=s.environment.panels.flatMap(p=>{
     const v=p.mesh.positions,out=[];for(let i=0;i<v.length;i+=3)out.push(s.project(v[i],v[i+1]-.08,v[i+2]));return out;
    });
    const bounds={left:Math.min(...points.map(p=>p.x)),right:Math.max(...points.map(p=>p.x)),top:Math.min(...points.map(p=>p.y)),bottom:Math.max(...points.map(p=>p.y))};
    return {...bounds,covered:bounds.left<=.01&&bounds.right>=749.99&&bounds.top<=.01&&bounds.bottom>=1623.99,camera:{...s.cameraWorld}};
   };
   const initial=measure(),follow=[];s.stopFollow();
   for(let i=0;i<40;i++){s.setPiece(i,document.querySelector('#piece'));s.follow(i,true);s.draw();follow.push({slot:i+1,...measure()});}
   const pans=[];
   for(const dx of [-100000,0,100000])for(const dy of [-100000,0,100000]){s.panFrom({x:0,y:7,z:-10},dx,dy);pans.push({dx,dy,...measure()});}
   // Exercise smoothed follow after a real drag, not only immediate snaps.
   s.beginFollow();for(let i=0;i<60;i++)s.updateCamera(1/60,performance.now()/1000+1);
   const smoothed=measure();s.follow(0,true);s.setPiece(0,document.querySelector('#piece'));s.draw();
   return {zoom:s.zoom,tiles:s.data.squares.length,initial,follow,pans,smoothed,error:s.boardRenderer.gl.getError()};
  });
  assert.equal(result.zoom,6.8);assert.equal(result.tiles,40);assert.equal(result.error,0);
  assert(result.initial.covered,'initial artwork must cover the whole game canvas');
  for(const x of [...result.follow,...result.pans,result.smoothed])assert(x.covered,JSON.stringify(x));
  await page.screenshot({path:`outputs/ink-cover-${viewport.width}.png`});
  records.push({viewport,...result});await page.close();
 }
 assert.deepEqual(errors,[]);assert.deepEqual(missing,[]);
 await fs.writeFile('outputs/ink-cover-checks.json',JSON.stringify({records,errors,missing},null,2));
 console.log(JSON.stringify({viewports:records.length,followCases:120,panBoundaryCases:27,fullCanvasCovered:true,errors,missing}));
}finally{await browser.close();}
