import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {chromium}=require('C:/Users/zhfzhang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const origin=process.env.MHXC_ASSET_ORIGIN||'http://127.0.0.1:3578';
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
const page=await browser.newPage({viewport:{width:1142,height:2218},deviceScaleFactor:1});
await page.goto(origin+'/assets/construction/ui.json');
await page.setContent('<div id="portrait" style="width:1142px;height:2218px"></div><style>body{margin:0}canvas{width:100%;height:100%;display:block}.spine-player-controls{display:none}</style>');
await page.addScriptTag({url:origin+'/vendor/spine-player-4.0.js'});
await page.evaluate(origin=>{
 window.p=new spine40.SpinePlayer('portrait',{binaryUrl:origin+'/assets/construction/portraits/npc_1016.skel',atlasUrl:origin+'/assets/construction/portraits/npc_1016.atlas',alpha:true,backgroundColor:'00000000',showControls:false,showLoading:false,preserveDrawingBuffer:true,premultipliedAlpha:false,success:()=>window.ready=true,error:(p,e)=>window.err=e});
},origin);
await page.waitForFunction(()=>window.ready||window.err,{timeout:15000});
const result=await page.evaluate(()=>{
 if(window.err)return{error:window.err};
 const p=window.p;p.stopRendering();p.pause();p.animationState.clearTracks();p.skeleton.setToSetupPose();p.animationState.setAnimation(0,'normal',true);p.animationState.update(.5);p.animationState.apply(p.skeleton);p.skeleton.updateWorldTransform();
 const offset=new spine40.Vector2(),size=new spine40.Vector2();p.skeleton.getBounds(offset,size,[]);p.currentViewport={x:offset.x,y:offset.y,width:size.x,height:size.y,padLeft:0,padRight:0,padTop:0,padBottom:0};p.previousViewport=null;p.drawFrame(false);
 return{animation:'normal',time:.5,premultipliedAlpha:false,bounds:{x:offset.x,y:offset.y,width:size.x,height:size.y},dataURL:p.canvas.toDataURL('image/png')};
});
if(result.error)throw new Error(result.error);
await fs.writeFile('assets/construction/portraits/npc_1016-preview.png',Buffer.from(result.dataURL.split(',')[1],'base64'));
delete result.dataURL;
await fs.writeFile('assets/construction/portraits/npc_1016-preview.json',JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result));
await browser.close();
