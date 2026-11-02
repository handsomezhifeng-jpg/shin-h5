import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
const {chromium}=createRequire(import.meta.url)('C:/Users/zhfzhang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
const errors=[],missing=[];
try{
 const page=await browser.newPage({viewport:{width:750,height:1624}});
 page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=400&&!r.url().endsWith('favicon.ico'))missing.push(r.url());});
 await page.addInitScript(()=>{window.__textureSizes=[];const original=WebGLRenderingContext.prototype.texImage2D;WebGLRenderingContext.prototype.texImage2D=function(...args){if(args.length===6&&args[5])window.__textureSizes.push([args[5].width,args[5].height]);return original.apply(this,args);};});
 await page.goto(process.env.SHIN_PREVIEW_URL||'http://127.0.0.1:4483/dist/?boardSkin=sanguo',{waitUntil:'networkidle'});
 await page.waitForFunction(()=>window.__SHIN?.scene?.environment?.villagers?.length===9);
 const result=await page.evaluate(()=>{const s=__SHIN.scene;s.draw();return {scale:s.environment.artScale,panels:s.environment.panels.map(p=>({url:p.url,width:s.images[p.url].width,height:s.images[p.url].height})),uploaded:window.__textureSizes,glError:s.boardRenderer.gl.getError(),tiles:s.data.squares.length};});
 assert.equal(result.scale,2);assert.equal(result.tiles,40);assert.equal(result.glError,0);
 for(const [i,height]of [960,1040,1072].entries()){assert.equal(result.panels[i].width,2048);assert.equal(result.panels[i].height,height);assert(result.uploaded.some(([w,h])=>w===2048&&h===height),'Full resolution must reach WebGL');}
 for(const width of [750,375]){await page.setViewportSize({width,height:Math.round(width*1624/750)});for(const side of ['left','right']){await page.evaluate(side=>{const s=__SHIN.scene,b=s.environment.cameraBounds(s.zoom);s.stopFollow();s.setView({x:side==='left'?b.left:b.right,y:7,z:-10},s.zoom);s.cast.timeOverride=0;if(s.environment.residents)s.environment.residents.timeOverride=0;s.draw();},side);await page.screenshot({path:`outputs/ink-hd-${side}-${width}.png`});}}
 assert.deepEqual(errors,[]);assert.deepEqual(missing,[]);
 await fs.writeFile('outputs/ink-resolution-checks.json',JSON.stringify({result,errors,missing},null,2));console.log(JSON.stringify({scale:result.scale,panels:result.panels,fullResolutionUploaded:true,errors,missing}));
}finally{await browser.close();}
