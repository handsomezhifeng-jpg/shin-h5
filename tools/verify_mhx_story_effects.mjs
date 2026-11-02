// Run the extracted effect assets in the web renderer, without an emulator.
import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url),{chromium}=require('C:/Users/zhfzhang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const origin=process.env.MHXC_ASSET_ORIGIN||'http://127.0.0.1:3782',output='C:/dev/mhxcz-analysis/story-effects-browser-check.json',mirror=path.resolve(import.meta.dirname,'../outputs/construction-story-fx');
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--autoplay-policy=user-gesture-required']}),page=await browser.newPage({viewport:{width:750,height:1334}}),errors=[];
page.on('pageerror',error=>errors.push(error.message));
try{
 await page.goto(origin+'/assets/construction/ui.json');
 await page.setContent('<div id="stage" style="position:absolute;left:0;top:0;width:1440px;height:2560px;transform:scale(.5208333333333334);transform-origin:0 0;background:#ddd"><div data-original-prefab="PlotDialogue"><div id="fx" data-path="PlotDialogue/ForwardImgEffectRoot" style="position:absolute;inset:0"></div></div></div>');
 await page.addScriptTag({url:origin+'/vendor/spine-player-4.0.js'});
 await page.evaluate(async origin=>{
  const{ConstructionNPCs}=await import(origin+'/src/construction-npcs.mjs'),{loadConstructionStoryEffects}=await import(origin+'/src/construction-story-effects.mjs');
  const npcs=window.npcs=new ConstructionNPCs({roles:{}},spine40,{roles:{}},null),data=await fetch(origin+'/assets/construction/story-effects.json').then(r=>r.json());
  document.getElementById('fx').rect={w:1440,h:2560};
  // Inspection only: keep the native object alive while capturing a fixed source frame.
  window.sourceDuration=data.fx['1'].fxDuration;data.fx['1'].fxDuration=2;
  window.effects=await loadConstructionStoryEffects({stage:document.getElementById('stage'),npcs,data});
  window.result=effects.on({id:38},[{type:12,params:'1,1'}]);
 },origin);
 await page.waitForFunction(()=>[...window.npcs.handles].some(handle=>handle.readyState)||window.effects.errors.length>0);
 const active=await page.evaluate(()=>{const h=[...npcs.handles][0];if(!h?.readyState)throw Error(JSON.stringify(effects.errors));const p=h.player;p.pause();p.animationState.clearTracks();p.skeleton.setToSetupPose();p.animationState.setAnimation(0,'animation',false);p.animationState.update(.1);p.animationState.apply(p.skeleton);p.skeleton.updateWorldTransform();p.drawFrame(false);return{role:h.role,animation:p.animationState.getCurrent(0).animation.name,loop:p.animationState.getCurrent(0).loop,duration:h.duration,sourceWaitSeconds:window.sourceDuration,inspectedTrackTime:.1,source:h.sourceProfile.binaryUrl,sourceRect:{left:h.el.style.left,top:h.el.style.top,width:h.el.style.width,height:h.el.style.height}};});
 await page.screenshot({path:'C:/dev/mhxcz-analysis/story-effects-slap.png'});
 await page.waitForFunction(()=>window.npcs.handles.size===0);
 // DevTools evaluations carry user activation. Wait past its native lifetime
 // inside the page before testing genuine browser autoplay rejection.
 await page.evaluate(()=>new Promise(resolve=>{const NativeAudio=window.Audio;window.Audio=function(...args){return window.lastBgmAudio=new NativeAudio(...args);};setTimeout(()=>{effects.playBGM(1,{fadeIn:0});resolve();},6500);}));
 await page.waitForFunction(()=>effects.currentBGM===0&&effects.warnings.some(warning=>warning.retryable));
 await page.evaluate(()=>{const button=document.createElement('button');button.id='music-retry';button.textContent='播放原曲';button.style.cssText='position:fixed;top:0;left:0;z-index:99999';button.onclick=()=>effects.playBGM(1,{fadeIn:0});document.body.append(button);});
 await page.click('#music-retry');
 await page.waitForFunction(()=>effects.currentBGM===1&&!lastBgmAudio.paused&&lastBgmAudio.currentTime>0);
 const audio=await page.evaluate(()=>{const result={autoplayBlocked:effects.warnings.some(warning=>warning.retryable),sameTrackRetried:effects.currentBGM===1,playing:!lastBgmAudio.paused};effects.stopBGM();result.stopped=lastBgmAudio.paused&&effects.currentBGM===0;document.getElementById('music-retry').remove();return result;});
 const final=await page.evaluate(()=>({handles:npcs.handles.size,effectErrors:effects.errors,npcErrors:npcs.errors,sourceVersion:effects.data.catalog.version}));
 if(errors.length||final.effectErrors.length||final.npcErrors.length||active.loop||final.handles)throw Error(JSON.stringify({active,final,errors}));
 const report={active,audio,final,pageErrors:errors,screenshot:'C:/dev/mhxcz-analysis/story-effects-slap.png'};
 await fs.writeFile(output,JSON.stringify(report,null,2)+'\n');
 await fs.mkdir(mirror,{recursive:true});await fs.copyFile(report.screenshot,path.join(mirror,'slap-source-frame.png'));
 await fs.writeFile(path.join(mirror,'slap-source-check.json'),JSON.stringify({...report,screenshot:'slap-source-frame.png'},null,2)+'\n');console.log(JSON.stringify(report));
}finally{await browser.close();}
