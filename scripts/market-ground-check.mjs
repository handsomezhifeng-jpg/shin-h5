import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const {chromium}=createRequire(import.meta.url)('C:/Users/zhfzhang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const output=process.env.SHIN_GROUND_AUDIT_DIR||'outputs/market-ground';await fs.mkdir(output,{recursive:true});
const preview=process.env.SHIN_PREVIEW_URL||'http://127.0.0.1:4472/';
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
const errors=[],missing=[],records=[];
try{
 for(const viewport of [{width:750,height:1624},{width:375,height:812},{width:1440,height:900}]){
  const p=await browser.newPage({viewport});
  p.on('pageerror',e=>errors.push(e.message));p.on('response',r=>{if(r.status()>=400&&!r.url().endsWith('favicon.ico'))missing.push(r.url());});
  await p.goto(preview,{waitUntil:'networkidle'});await p.waitForFunction(()=>window.__SHIN);
  const result=await p.evaluate(async()=>{
   const h=__SHIN,s=h.scene,e=s.environment;
   const [raw,prefabSource,hookSource]=await Promise.all(['grid-meshes.json','grid-prefabs.json','grid-hooks.json'].map(n=>fetch('assets/scene/'+n).then(r=>r.json())));
   const cells=s.data.squares.map(tile=>{
    const source=s.prefabs[String(tile.id)],mesh=s.meshes[source.meshName],native=raw[source.meshName];
    const ys=mesh.positions.filter((_,i)=>i%3===1),nativeYs=native.positions.filter((_,i)=>i%3===1);
    const bounds=m=>[0,2].flatMap(axis=>{const values=m.positions.filter((_,i)=>i%3===axis);return [Math.min(...values),Math.max(...values)];});
    return {id:tile.id,mesh:source.meshName,top:Math.max(...ys),bottom:Math.min(...ys),thickness:Math.max(...ys)-Math.min(...ys),nativeTop:Math.max(...nativeYs),foot:s.centerWorld(tile.id-1),footprint:e.marketGround.footprint(source.meshName).length,bounds:bounds(mesh),nativeBounds:bounds(native)};
   });
   const fund=document.querySelector('#world-ui [data-action="fund"]'),image=s.images['assets/scene/skins/ink/market-ground-v1.webp'];
   const world=Object.fromEntries(['x','y','z'].map(k=>[k,s.cameraWorld[k]]));
   s.draw();
   return {cells,world,zoom:s.zoom,sourcePrefabsUnchanged:JSON.stringify(s.prefabs)===JSON.stringify(prefabSource.prefabs),sourceHooksUnchanged:JSON.stringify(s.hooks)===JSON.stringify(hookSource),terrainSize:[image.naturalWidth,image.naturalHeight],terrainTriangles:e.marketGround.mesh.indices.length/3,fundHidden:getComputedStyle(fund).display==='none',fundShortcuts:document.querySelectorAll('.sanguo-side-entry[data-action="fund"]').length,glError:s.boardRenderer.gl.getError()};
  });
  assert.equal(result.cells.length,40);assert.equal(result.sourcePrefabsUnchanged,true);assert.equal(result.sourceHooksUnchanged,true);assert.equal(result.zoom,6.8);assert.equal(result.glError,0);
  assert(result.terrainSize.every(n=>n>=1024));assert.equal(result.fundHidden,true);assert(result.fundShortcuts>0);
  for(const cell of result.cells){
   assert(cell.thickness>.24&&cell.thickness<.27,'raised tile thickness '+cell.id);
   if(!['checkerboard_04','checkerboard_05'].includes(cell.mesh))assert.equal(cell.top,cell.nativeTop,'original top surface '+cell.id);
   assert(cell.foot.y>=cell.top*.9-.01,'player stays above tile '+cell.id);
   if(!['checkerboard_04','checkerboard_05'].includes(cell.mesh))assert(cell.foot.y<cell.top*.9+.12,'player landing height '+cell.id);
   assert(cell.footprint>=4,'contact shadow footprint '+cell.id);
   cell.bounds.forEach((v,i)=>assert(Math.abs(v-cell.nativeBounds[i])<1e-6,'tile footprint '+cell.id));
  }
  await p.screenshot({path:`${output}/after-${viewport.width}.png`});
  if(viewport.width===750)for(const id of [6,16,26,36]){
   const point=await p.evaluate(id=>{const s=__SHIN.scene,w=s.centerWorld(id-1);return s.project(w.x,w.y,w.z);},id);
   await p.screenshot({path:`${output}/tile-${id}.png`,clip:{x:Math.max(0,Math.min(450,point.x-150)),y:Math.max(0,Math.min(1404,point.y-110)),width:300,height:220}});
  }
  // Exercise the retained shortcut through the actual UI, rather than directly
  // calling the engine after removing its former central hit target.
  const coins=await p.evaluate(()=>{const e=__SHIN.engine;e.state.pending=null;e.state.fund=1234;return e.state.coins;});
  await p.locator('.sanguo-side-entry[data-action="fund"]').first().click();
  await p.waitForFunction(before=>__SHIN.engine.state.coins===before+1234,coins);
  assert.equal(await p.evaluate(()=>__SHIN.engine.state.fund),0);
  records.push({viewport,...result,sidebarFundCollected:true});await p.close();
 }
 const p=await browser.newPage({viewport:{width:375,height:812}});
 const originalURL=new URL(preview);originalURL.searchParams.set('boardSkin','original');
 await p.goto(originalURL.href,{waitUntil:'networkidle'});await p.waitForFunction(()=>window.__SHIN);
 assert.equal(await p.evaluate(()=>__SHIN.scene.environment===undefined),true);
 assert.equal(await p.locator('#world-ui [data-action="fund"]').isVisible(),true);
 await p.close();
 assert.deepEqual(errors,[]);assert.deepEqual(missing,[]);
 await fs.writeFile(`${output}/checks.json`,JSON.stringify({records,originalSceneRetained:true,errors,missing},null,2));
 console.log(JSON.stringify({viewports:records.length,raisedTiles:40,originalTopSurfacesAndPrefabsRetained:true,sidebarFundCollected:true,originalSceneRetained:true,errors,missing}));
}finally{await browser.close();}
