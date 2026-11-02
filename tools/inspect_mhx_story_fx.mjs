// Sample the original non-looping Spine animation directly; no emulator involved.
import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url),{chromium}=require('C:/Users/zhfzhang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const origin=process.env.MHXC_ASSET_ORIGIN||'http://127.0.0.1:3782';
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
try{
 const page=await browser.newPage({viewport:{width:1024,height:1024}});
 await page.goto(origin+'/assets/construction/ui.json');
 await page.setContent('<div id="fx" style="width:1024px;height:1024px"></div>');
 await page.addScriptTag({url:origin+'/vendor/spine-player-4.0.js'});
 await page.evaluate(origin=>{
  window.ready=false;window.error=null;
  window.player=new spine40.SpinePlayer('fx',{binaryUrl:origin+'/assets/construction/story-fx/hit.skel',atlasUrl:origin+'/assets/construction/story-fx/hit.atlas',animation:'animation',alpha:true,premultipliedAlpha:false,showControls:false,showLoading:false,success:()=>window.ready=true,error:(_,e)=>window.error=e});
 },origin);
 await page.waitForFunction(()=>window.ready||window.error);
 const profile=await page.evaluate(()=>{
  if(window.error)throw Error(window.error);
  const p=window.player;p.stopRendering();p.pause();
  const animation=p.skeleton.data.findAnimation('animation');
  if(!animation)throw Error('Original hit animation is missing');
  let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity;
  const steps=Math.max(1,Math.ceil(animation.duration*120));
  for(let step=0;step<=steps;step++){
   p.animationState.clearTracks();p.skeleton.setToSetupPose();p.animationState.setAnimation(0,animation.name,false);p.animationState.update(animation.duration*step/steps);p.animationState.apply(p.skeleton);p.skeleton.updateWorldTransform();
   const offset=new spine40.Vector2(),size=new spine40.Vector2();p.skeleton.getBounds(offset,size,[]);
   if(size.x>0&&size.y>0){minX=Math.min(minX,offset.x);minY=Math.min(minY,offset.y);maxX=Math.max(maxX,offset.x+size.x);maxY=Math.max(maxY,offset.y+size.y);}
  }
  return{duration:animation.duration,viewport:{x:minX,y:minY,width:maxX-minX,height:maxY-minY,padLeft:0,padRight:0,padTop:0,padBottom:0}};
 });
 if(![profile.viewport.x,profile.viewport.y,profile.viewport.width,profile.viewport.height].every(Number.isFinite))throw Error('Original hit animation bounds are empty');
 const output=path.resolve(import.meta.dirname,'../assets/construction/story-fx/hit-profile.json');
 await fs.writeFile(output,JSON.stringify(profile,null,2)+'\n');
 console.log(JSON.stringify(profile));
}finally{await browser.close();}
