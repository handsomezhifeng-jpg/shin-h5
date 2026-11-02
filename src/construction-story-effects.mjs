// Original PlotEffect scripts and extracted APK CG / ColorOverlay shader parameters.
import{resolveConstructionArtURL}from './construction-skin.mjs';
const ROOT=new URL('../assets/construction/',import.meta.url);
const read=async path=>{const response=await fetch(new URL(path,ROOT));if(!response.ok)throw Error('原剧情效果资料读取失败：'+path);return response.json();};
const abortError=()=>Object.assign(Error('原剧情效果已取消'),{name:'AbortError'});
const TWEEN_OUT_QUAD='cubic-bezier(0.3333333333,0.6666666667,0.6666666667,1)';
export function sourceMemoryMatrix(memory){
 const c=memory.overlayColor,d=memory.desaturation,i=memory.intensity,l=memory.luminance;
 return [0,1,2].flatMap(channel=>[0,1,2].map(input=>((channel===input?1-d:0)+d*l[input])*(1-i+i*c[channel])).concat([0,0])).concat([0,0,0,1,0]);
}
export function preflightConstructionStoryEffects(data,plan){const missing=[],notes=[];const checkEffect=(effect,row)=>{const type=Number(effect.type),params=String(effect.params??'');if(![1,6,7,8,11,12,13,14,15].includes(type)){missing.push({kind:'effect-handler',type,dialogueId:row?.id});return;}if(type===13||type===14){const[open,id]=params.split(',').map(Number);if(open===1){const asset=(type===13?data.cg:data.bg)?.[String(id)];if(!asset||asset.available===false)missing.push({kind:type===13?'CG':'BG',id,dialogueId:row?.id,path:asset?.cgPath??asset?.bgPath});}}if(type===12){const id=Number(params.split(',')[0]),fx=data.fx?.[String(id)];if(!id||!fx?.available)notes.push({kind:'source-spine-failure',fxId:id,dialogueId:row?.id,continues:true});else if(!fx.profile)missing.push({kind:'spine-animation-bounds',fxId:id,dialogueId:row?.id});}if(type===15){const id=Number(params.split(',')[0]);if(!data.sounds?.[String(id)]?.available)notes.push({kind:'source-sound-unavailable',soundId:id,continues:true});}};
  for(const step of plan?.steps||[]){const type=Number(step.type??step.plotType);if(type===1)for(const row of step.rows||[]){if(Number(row.type)===3)continue;for(const effect of[...(row.effectsBefore||[]),...(row.effectsOn||[])])checkEffect(effect,row);}if(type===7&&Number(step.worldId??step.performId)!==1)missing.push({kind:'world',id:Number(step.worldId??step.performId),stepId:step.stepId});if(type===9)checkEffect({type:13,params:'1,'+(step.cgId??step.performId)});if(type===11)missing.push({kind:'activity-skin-handler',id:step.skinGoodsId??step.performId,stepId:step.stepId});if(type===12&&!data.sounds?.[String(step.bgmId??step.performId)]?.available)notes.push({kind:'source-sound-unavailable',soundId:step.bgmId??step.performId,continues:true});if(![1,2,3,4,5,6,7,8,9,10,11,12].includes(type))missing.push({kind:'plot-type',type,stepId:step.stepId});}
  return{ok:missing.length===0,missing,warnings:notes};
 }

export async function loadConstructionStoryEffects({stage,scene,npcs,data}={}){
 if(!stage)throw Error('原剧情效果缺少承载节点');
 data||=await read('story-effects.json');
 const limitations=new Set([data.memory.browserColorSpace]),warnings=[],errors=[],document=stage.ownerDocument||globalThis.document;
 const memoryTarget=scene?.canvas?.parentElement?.contains(stage)?scene.canvas.parentElement:stage;
 let disposed=false,cg=null,bg=null,host=null,memory=false,screenBlack=null,heldBlack=null,lifetime=new AbortController(),music=null,musicId=0,musicSerial=0,musicController=new AbortController();
 const animations=new Set(),transients=new Set(),timers=new Set(),fxHandles=new Set(),sounds=new Set();
 const svg=document.createElementNS('http://www.w3.org/2000/svg','svg'),filterId='mhx-source-memory-'+Math.random().toString(36).slice(2);
 svg.style.cssText='position:absolute;width:0;height:0;pointer-events:none';
 svg.innerHTML=`<defs><filter id="${filterId}" color-interpolation-filters="sRGB"><feColorMatrix type="matrix" values="${sourceMemoryMatrix(data.memory).join(' ')}"/></filter></defs>`;
 document.body.append(svg);const oldFilter=memoryTarget.style.filter;
 function signalFor(signal){if(!signal)return lifetime.signal;return AbortSignal.any([signal,lifetime.signal]);}
 function check(signal){if(disposed||signal?.aborted)throw abortError();}
 function wait(seconds,signal){check(signal);return new Promise((resolve,reject)=>{const record={timer:0,abort:null};record.abort=()=>{clearTimeout(record.timer);timers.delete(record);reject(abortError());};record.timer=setTimeout(()=>{timers.delete(record);signal?.removeEventListener('abort',record.abort);resolve();},Math.max(0,seconds*1000));timers.add(record);signal?.addEventListener('abort',record.abort,{once:true});});}
 async function fade(el,from,to,seconds,signal,easing='linear'){check(signal);el.style.opacity=String(from);if(!seconds){el.style.opacity=String(to);return;}
  if(el.animate){const animation=el.animate([{opacity:from},{opacity:to}],{duration:seconds*1000,easing,fill:'forwards'});animations.add(animation);const cancel=()=>animation.cancel();signal?.addEventListener('abort',cancel,{once:true});try{await animation.finished;check(signal);el.style.opacity=String(to);}catch(error){if(signal?.aborted)throw abortError();throw error;}finally{animations.delete(animation);signal?.removeEventListener('abort',cancel);animation.cancel();}}
  else{el.style.transition=`opacity ${seconds}s linear`;requestAnimationFrame(()=>el.style.opacity=String(to));await wait(seconds,signal);el.style.transition='';}
 }
 function sourceNode(name){const modal=stage.querySelector('[data-original-prefab="PlotDialogue"]');if(modal!==host){resetVisuals();host=modal;}return modal?.querySelector(`[data-path$="/${name}"]`);}
 function setMemory(enable){memory=enable;memoryTarget.style.filter=enable?`${oldFilter||''} url(#${filterId})`.trim():oldFilter;stage.dataset.sourceMemory=String(enable);}
 function resetVisuals(){cg?.element.remove();cg=null;bg?.element.remove();bg=null;heldBlack?.remove();heldBlack=null;for(const handle of fxHandles)handle.dispose();fxHandles.clear();for(const node of transients)node.remove();transients.clear();setMemory(false);}
 function sourceWarning(message,context){if(!warnings.some(row=>row.message===message)){warnings.push({message,...context});limitations.add(message);}}
 function error(message,row,effect){const e=Error(message);e.context={dialogueId:row?.id,effectType:effect?.type,params:effect?.params};return e;}
 async function image(asset,signal){check(signal);const img=document.createElement('img');img.alt='';img.dataset.originalCG=asset.cgPath;img.style.cssText='position:absolute;inset:0;width:100%;height:100%;pointer-events:none';
  await new Promise((resolve,reject)=>{const stop=()=>{img.src='';reject(abortError());};signal?.addEventListener('abort',stop,{once:true});img.onload=()=>{signal?.removeEventListener('abort',stop);resolve();};img.onerror=()=>{signal?.removeEventListener('abort',stop);reject(Error('原CG图片读取失败：'+asset.cgPath));};img.src=resolveConstructionArtURL(new URL(asset.url,ROOT).href);});check(signal);return img;
 }
 async function cgEffect(params,signal,row){const[open,id]=String(params).split(',').map(Number);
  if(open===1){const asset=data.cg[String(id)];if(!asset||asset.available===false)throw error('原CG资源未恢复：'+id,row,{type:13,params});
   const target=sourceNode('CG/ImgCG'),root=sourceNode('CG');const img=await image(asset,signal);cg?.element.remove();
   let container=target;
   if(container){root.hidden=false;target.hidden=false;const rect=target.rect;if(rect){target.style.left=rect.x+(rect.w-asset.width)/2+'px';target.style.top=rect.y+(rect.h-asset.height)/2+'px';}target.style.width=asset.width+'px';target.style.height=asset.height+'px';target.replaceChildren(img);}
   else{container=document.createElement('div');container.dataset.originalCG=asset.cgPath;container.style.cssText=`position:absolute;left:50%;top:calc(50% - ${195*750/1440}px);width:${asset.width*2*750/1440}px;height:${asset.height*2*750/1440}px;transform:translate(-50%,-50%);pointer-events:none;z-index:61`;stage.append(container);container.append(img);transients.add(container);}
   cg={element:img,container,root,asset};const fading=fade(img,0,1,data.cgRules.openFadeSeconds,signal);await Promise.all([fading,wait(data.cgRules.openWaitSeconds,signal)]);
  }else if(cg){const old=cg;await fade(old.element,Number(old.element.style.opacity)||1,0,data.cgRules.closeFadeSeconds,signal);old.element.remove();if(old.root)old.root.hidden=true;else old.container.remove();if(cg===old)cg=null;}
  else await wait(data.cgRules.closeWaitSeconds,signal);
 }
 async function black({from=1,to=0,duration=.8,signal}={}){signal=signalFor(signal);check(signal);const root=sourceNode('UIImgEffectRoot')||stage,node=document.createElement('div');node.dataset.originalEffect=from?'Black1':'Black0';node.style.cssText='position:absolute;inset:0;background:rgb(0,0,0);pointer-events:none;z-index:9999';root.append(node);transients.add(node);try{await fade(node,from,to,Number(duration)||0,signal,TWEEN_OUT_QUAD);}finally{transients.delete(node);node.remove();}}
 async function showBlack(seconds=.4,{signal}={}){signal=signalFor(signal);check(signal);if(!screenBlack?.isConnected){screenBlack=document.createElement('div');screenBlack.dataset.originalEffect='Prefabs/Common/Black.prefab';screenBlack.style.cssText='position:absolute;inset:0;background:rgb(0,0,0);pointer-events:none;z-index:9998;opacity:0';stage.append(screenBlack);}await fade(screenBlack,Number(screenBlack.style.opacity)||0,1,seconds,signal,TWEEN_OUT_QUAD);}
 async function hideBlackImpl(seconds=.8,{signal}={}){signal=signalFor(signal);check(signal);if(!screenBlack)return;const node=screenBlack;await fade(node,Number(node.style.opacity)||1,0,seconds,signal,TWEEN_OUT_QUAD);node.remove();if(screenBlack===node)screenBlack=null;}
 function hideBlack(...args){const promise=hideBlackImpl(...args);promise.catch(failure=>{if(failure?.name!=='AbortError')errors.push({message:failure.message,context:{effect:'hideBlack'}});});return promise;}
 async function blackSwitch({fadeIn=.8,hold=.2,fadeOut=1,signal,onBlack}={}){signal=signalFor(signal);await showBlack(fadeIn,{signal});const callback=onBlack?.();callback?.catch?.(failure=>errors.push({message:failure.message,context:{effect:'blackSwitch.onBlack'}}));await wait(hold,signal);await hideBlack(fadeOut,{signal});}
 async function blackInOut(params,signal,row){const durations=String(params).split(',').map(Number);if(durations.length!==3||!durations.every(value=>Number.isFinite(value)&&value>=0)){sourceWarning('Original BlackFadeInOut rejected its three duration parameters',{dialogueId:row?.id});return;}const root=sourceNode('UIImgEffectRoot')||stage,node=document.createElement('div');node.dataset.originalEffect='Black0';node.style.cssText='position:absolute;inset:0;background:#000;pointer-events:none;z-index:9999';root.append(node);transients.add(node);try{await fade(node,0,1,durations[0],signal,TWEEN_OUT_QUAD);await wait(durations[1],signal);await fade(node,1,0,durations[2],signal,TWEEN_OUT_QUAD);}finally{transients.delete(node);node.remove();}}
 async function blackHeld(params,signal){const[open,duration]=String(params).split(',').map(Number);if(!heldBlack){heldBlack=document.createElement('div');heldBlack.dataset.originalEffect='BlackFade';heldBlack.style.cssText='position:absolute;inset:0;background:#000;opacity:0;pointer-events:none;z-index:9999';(sourceNode('UIImgEffectRoot')||stage).append(heldBlack);}await fade(heldBlack,Number(heldBlack.style.opacity)||0,open===1?1:0,Number(duration)||0,signal,TWEEN_OUT_QUAD);}
 async function bgEffect(params,signal,row){const[open,id]=String(params).split(',').map(Number);if(open!==1){bg?.element.remove();if(bg?.root)bg.root.hidden=true;bg=null;return;}const asset=data.bg?.[String(id)];if(!asset||asset.available===false)throw error('原BG资源未恢复：'+id,row,{type:14,params});const target=sourceNode('BG/ImgCG'),root=sourceNode('BG'),img=await image(asset,signal);bg?.element.remove();let container=target;if(container){root.hidden=false;target.hidden=false;target.replaceChildren(img);}else{container=document.createElement('div');container.dataset.originalBG=asset.bgPath;container.style.cssText='position:absolute;inset:0;pointer-events:none;z-index:59';container.append(img);stage.prepend?stage.prepend(container):stage.append(container);transients.add(container);}bg={element:img,container,root,asset};await hideBlack(.01,{signal});}
 function musicWait(ms,signal){return new Promise((resolve,reject)=>{const finish=()=>{signal.removeEventListener('abort',cancel);resolve();},timer=setTimeout(finish,ms),cancel=()=>{clearTimeout(timer);reject(abortError());};signal.addEventListener('abort',cancel,{once:true});if(signal.aborted)cancel();});}
 async function volume(audio,from,to,seconds,signal){check(signal);const start=performance.now();audio.volume=from;while(true){check(signal);const t=seconds>0?Math.min(1,(performance.now()-start)/(seconds*1000)):1;audio.volume=from+(to-from)*t;if(t>=1)return;await musicWait(Math.min(16,seconds*1000),signal);}}
 function playBGM(id,options={}){
  id=Number(id);if(id===musicId)return{unchanged:true,id};const asset=data.sounds?.[String(id)];
  if(!asset||asset.available===false){sourceWarning('Original sound reference is unavailable; PlaySound has no replacement clip',{soundId:id});return{sourceLoadFailed:true,id};}
  if(!globalThis.Audio){sourceWarning('Audio playback is unavailable in this runtime',{soundId:id});return{sourceLoadFailed:true,id};}
  musicController.abort();musicController=new AbortController();const signal=musicController.signal,token=++musicSerial,old=music;musicId=id;
  const task=(async()=>{if(old){await volume(old,old.volume,0,options.fadeOut??data.bgmRules?.fadeOutSeconds??1,signal);old.pause();}check(signal);if(token!==musicSerial)return;const audio=music=new Audio(new URL(asset.url,ROOT).href);audio.loop=Number(asset.soundType)===2;audio.preload='auto';audio.volume=0;await audio.play();await volume(audio,0,options.volume??1,options.fadeIn??data.bgmRules?.fadeInSeconds??1,signal);})();
  task.catch(failure=>{if(failure?.name==='AbortError'||signal.aborted||token!==musicSerial)return;music?.pause();music=null;musicId=0;if(failure?.name==='NotAllowedError'){sourceWarning('Browser blocked the original BGM until a user interaction; the same track can be retried',{soundId:id,retryable:true});return;}errors.push({message:failure.message,context:{effect:'BGM',soundId:id}});});return{started:true,id};
 }
 function sound(id,{signal,volume:gain=1}={}){
  check(signal);id=Number(id);const asset=data.sounds?.[String(id)];
  if(!asset||asset.available===false){sourceWarning('Original sound reference is unavailable; PlaySound has no replacement clip',{soundId:id});return{sourceLoadFailed:true,id};}
  if(Number(asset.soundType)===2)return playBGM(id,{volume:gain});
  if(!globalThis.Audio){sourceWarning('Audio playback is unavailable in this runtime',{soundId:id});return{sourceLoadFailed:true,id};}
  const audio=new Audio(new URL(asset.url,ROOT).href);audio.preload='auto';audio.loop=false;audio.volume=Math.max(0,Math.min(1,gain));sounds.add(audio);
  const cleanup=()=>{sounds.delete(audio);signal?.removeEventListener('abort',stop);},stop=()=>{audio.pause();cleanup();};
  audio.addEventListener('ended',cleanup,{once:true});signal?.addEventListener('abort',stop,{once:true});
  Promise.resolve(audio.play()).catch(failure=>{cleanup();sourceWarning('Browser could not start the original sound clip',{soundId:id,reason:failure.message});});
  return{started:true,id};
 }
 function stopBGM(){const id=musicId;musicController.abort();musicController=new AbortController();musicSerial++;music?.pause();music=null;musicId=0;return{stopped:true,id};}
 async function spineFx(fx,row,signal){
  if(!npcs?.mountPortrait||!fx.profile)throw error('原SpineFX骨骼播放器或动作边界缺失：'+fx.fxPath,row,{type:12,params:fx.id});
  const role='_plot_fx_'+fx.id,target=sourceNode('ForwardImgEffectRoot')||stage,root=document.createElement('div');root.dataset.originalEffect=fx.sourcePath;root.style.cssText='position:absolute;inset:0;pointer-events:none';root.rect=target.rect||{w:target.clientWidth||750,h:target.clientHeight||1334};target.append(root);transients.add(root);
  npcs.data.roles[role]={kind:'effect',binaryUrl:'../'+fx.binaryUrl,atlasUrl:'../'+fx.atlasUrl,animations:{[fx.animation]:fx.profile},uiPrefab:{nodes:[{name:'spine',transform:{m_LocalScale:{x:1,y:1,z:1},m_AnchoredPosition:{x:0,y:0}}}]}};
  const background=document.createElement('div');background.style.cssText='position:absolute;inset:0;background:#000;opacity:0;pointer-events:none';root.append(background);
  let handle;
  try{
   handle=npcs.mountPortrait(root,{role,animation:fx.animation,originalUnits:true,instanceKey:role+'/'+Math.random().toString(36).slice(2)});fxHandles.add(handle);
   await new Promise((resolve,reject)=>{const stop=()=>reject(abortError());signal.addEventListener('abort',stop,{once:true});handle.ready.then(resolve,reject).finally(()=>signal.removeEventListener('abort',stop));});check(signal);
   handle.player.animationState.setAnimation(0,fx.animation,!!fx.loop);handle.player.animationState.timeScale=fx.timeScale;
   const flash=(async()=>{await fade(background,0,1,fx.background.fadeIn,signal);await wait(Math.max(0,fx.background.fadeOutDelay-fx.background.fadeIn),signal);await fade(background,1,0,fx.background.fadeOut,signal);})();
   // Source SpineFx waits its configured .5 seconds after the original prefab loads.
   await Promise.all([flash,wait(Number(fx.fxDuration)||0,signal)]);
  }finally{if(handle){fxHandles.delete(handle);handle.dispose();}transients.delete(root);root.remove();}
 }
 async function execute(row,effect,signal){check(signal);sourceNode('UIImgEffectRoot');const type=Number(effect.type),params=effect.params??'';
  if(type===13)return cgEffect(params,signal,row);
  if(type===1){setMemory(Number(params)===1);return;}
  if(type===7)return black({from:1,to:0,duration:Number(params)||0,signal});
  if(type===6)return black({from:0,to:1,duration:Number(params)||0,signal});
  if(type===8)return blackInOut(params,signal,row);
  if(type===11)return blackHeld(params,signal);
  if(type===14)return bgEffect(params,signal,row);
  if(type===15)return playBGM(Number(String(params).split(',')[0]));
  if(type===12){const id=Number(String(params).split(',')[0]);if(!id){sourceWarning('Original SpineFx rejects fxId=0 and returns',{dialogueId:row?.id});return;}const fx=data.fx[String(id)];if(!fx){sourceWarning('Original SpineFx config is absent and returns',{dialogueId:row?.id,fxId:id});return;}if(!fx.available){sourceWarning(fx.sourceWarning||'Original SpineFx resource is unavailable',{fxId:fx.id,dialogueId:row?.id,sourcePath:fx.fxPath});await wait(Number(fx.fxDuration)||0,signal);return {sourceLoadFailed:true,fxId:fx.id};}return spineFx(fx,row,signal);}
  throw error('原剧情效果尚未实现：'+type,row,effect);
 }
 async function before(row,effects=[],options={}){const signal=signalFor(options.signal);for(const effect of effects)await execute(row,effect,signal);}
 function on(row,effects=[],options={}){const signal=signalFor(options.signal);check(signal);for(const effect of effects){if(![1,6,7,8,11,12,13,14,15].includes(Number(effect.type)))throw error('原剧情效果尚未实现：'+effect.type,row,effect);execute(row,effect,signal).catch(failure=>{if(failure?.name!=='AbortError')errors.push({message:failure.message,context:failure.context||{dialogueId:row?.id,effectType:effect.type}});});}return{started:effects.length};}
 async function apply(step,context={}){
  const signal=signalFor(context.signal);
  if(step.kind==='bgm'||Number(step.plotType)===12)return playBGM(step.bgmId??step.performId);
  if(step.kind==='world'||Number(step.plotType)===7){if(Number(step.worldId??step.performId)===1)return{unchanged:true,worldId:1};throw error('原世界场景尚未恢复：'+(step.worldId??step.performId),context.row,step);}
  if(step.kind==='cg'||Number(step.plotType)===9){await cgEffect('1,'+(step.cgId??step.performId),signal);await wait(Number(step.waitSeconds??step.performParams)||0,signal);return cgEffect(0,signal);}
  if(step.effectType!=null)return execute(context.row,{type:step.effectType,params:step.params??step.performParams},signal);
  if(step.params!=null&&!step.kind)return execute(context.row,step,signal);
  throw error('原剧情步骤效果尚未恢复：'+(step.kind??step.type),context.row,{type:step.type,params:step.performParams});
 }
 const preflight=plan=>preflightConstructionStoryEffects(data,plan);
 function end(){lifetime.abort();lifetime=new AbortController();for(const animation of animations)animation.cancel();animations.clear();for(const record of timers){clearTimeout(record.timer);record.abort();}timers.clear();resetVisuals();screenBlack?.remove();screenBlack=null;host=null;}
 function dispose(){if(disposed)return;end();disposed=true;stopBGM();for(const audio of sounds)audio.pause();sounds.clear();svg.remove();delete stage.dataset.sourceMemory;}
 return {data,limitations,warnings,errors,before,on,end,apply,preflight,sound,playBGM,stopBGM,resetBGM:()=>playBGM(data.bgmRules?.defaultBgmId??1),black,blackTransition:black,showBlack,hideBlack,blackSwitch,dispose,get memoryEnabled(){return memory;},get activeCG(){return cg?.asset||null;},get activeBG(){return bg?.asset||null;},get currentBGM(){return musicId;}};
}
