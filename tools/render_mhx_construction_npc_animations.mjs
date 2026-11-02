// Sample the shipped NPC normal animation at 30 Hz for an offline pixel audit.
// No source artwork is repainted. Atlas page sizing is restored by the UI exporter.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {chromium}=require('C:/Users/zhfzhang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(import.meta.dirname,'..');
const source=path.join(root,'assets/construction/portraits');
const output=path.join(root,'../经验/outputs/梦幻消除战-资源核查/npc-animation-check');
const origin=process.env.MHXC_ASSET_ORIGIN||'http://127.0.0.1:3782';
const width=450,height=875,fps=30,columns=8,rows=4,perSheet=columns*rows;
await fs.mkdir(path.join(output,'normal'),{recursive:true});
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
try{
 const page=await browser.newPage({viewport:{width,height},deviceScaleFactor:1});
 await page.goto(origin+'/assets/construction/ui.json');
 await page.setContent(`<style>body{margin:0}canvas{display:block;width:100%;height:100%}.spine-player-controls{display:none}</style><div id="portrait" style="width:${width}px;height:${height}px"></div>`);
 await page.addScriptTag({url:origin+'/vendor/spine-player-4.0.js'});
 await page.evaluate(origin=>{window.p=new spine40.SpinePlayer('portrait',{binaryUrl:origin+'/assets/construction/portraits/npc_1016.skel',atlasUrl:origin+'/assets/construction/portraits/npc_1016.atlas',alpha:true,backgroundColor:'00000000',showControls:false,showLoading:false,preserveDrawingBuffer:true,premultipliedAlpha:false,success:()=>window.ready=true,error:(_,e)=>window.err=e});},origin);
 await page.waitForFunction(()=>window.ready||window.err,{timeout:15000});
 const metadata=await page.evaluate(({fps,width,height})=>{
  if(window.err)throw Error(window.err);const p=window.p;p.stopRendering();p.pause();
  const animation=p.skeleton.data.findAnimation('normal'),duration=animation.duration,frames=Math.round(duration*fps);let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity;
  // Union bounds keep the original hair/hand motion inside one fixed viewport.
  for(let i=0;i<=frames*2;i++){p.animationState.clearTracks();p.skeleton.setToSetupPose();p.animationState.setAnimation(0,'normal',true);p.animationState.update(i*duration/(frames*2));p.animationState.apply(p.skeleton);p.skeleton.updateWorldTransform();const offset=new spine40.Vector2(),size=new spine40.Vector2();p.skeleton.getBounds(offset,size,[]);minX=Math.min(minX,offset.x);minY=Math.min(minY,offset.y);maxX=Math.max(maxX,offset.x+size.x);maxY=Math.max(maxY,offset.y+size.y);}
  window.normalViewport={x:minX,y:minY,width:maxX-minX,height:maxY-minY,padLeft:0,padRight:0,padTop:0,padBottom:0};
  return{animation:'normal',duration,frames,fps:frames/duration,width,height,viewport:window.normalViewport,availableAnimations:p.skeleton.data.animations.map(a=>({name:a.name,duration:a.duration}))};
 },{fps,width,height});
 const sheets=[];
 for(let first=0;first<metadata.frames;first+=perSheet){
  const count=Math.min(perSheet,metadata.frames-first);
  const url=await page.evaluate(({first,count,columns,rows,width,height,duration,frames})=>{
   const sheet=document.createElement('canvas');sheet.width=columns*width;sheet.height=Math.ceil(count/columns)*height;const c=sheet.getContext('2d'),p=window.p;
   for(let n=0;n<count;n++){const t=(first+n)*duration/frames;p.animationState.clearTracks();p.skeleton.setToSetupPose();p.animationState.setAnimation(0,'normal',true);p.animationState.update(t);p.animationState.apply(p.skeleton);p.skeleton.updateWorldTransform();p.currentViewport={...window.normalViewport};p.previousViewport=null;p.drawFrame(false);c.drawImage(p.canvas,(n%columns)*width,Math.floor(n/columns)*height,width,height);}
   return sheet.toDataURL('image/png');
  },{first,count,columns,rows,width,height,duration:metadata.duration,frames:metadata.frames});
  const file=`normal/npc_1016-normal-${String(sheets.length).padStart(2,'0')}.png`,bytes=Buffer.from(url.split(',')[1],'base64');await fs.writeFile(path.join(output,file),bytes);sheets.push({url:file,first,count,columns,rows:Math.ceil(count/columns),sha256:crypto.createHash('sha256').update(bytes).digest('hex')});console.log('rendered',first+count,'/',metadata.frames);
 }
 const sources=[];for(const file of ['npc_1016.skel','npc_1016.atlas','npc_1016.png']){const bytes=await fs.readFile(path.join(source,file));sources.push({file,sha256:crypto.createHash('sha256').update(bytes).digest('hex')});}
 const result={format:1,roles:{npc_1016:{source:sources,animations:{normal:{...metadata,sheets,loop:true}},placement:{taskPortrait:'Original TaskDailog RoleGroup/NpcMask; controller supplies its original RectTransform position.',scene:'No verified runtime NPC identity/position binding has been recovered.'}}}};
 await fs.writeFile(path.join(output,'npc-animations.json'),JSON.stringify(result,null,2)+'\n');
 const runtimeResult=structuredClone(result);delete runtimeResult.roles.npc_1016.animations.normal.sheets;runtimeResult.roles.npc_1016.rendering='Live original Spine 4.0 skeleton, animation timing and loop; the offline frame audit is not a runtime dependency.';
 await fs.writeFile(path.join(source,'npc-animations.json'),JSON.stringify(runtimeResult,null,2)+'\n');console.log(JSON.stringify({duration:metadata.duration,frames:metadata.frames,sheets:sheets.length,width,height}));
}finally{await browser.close();}
