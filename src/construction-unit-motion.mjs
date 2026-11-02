// PerformScripts.PlayUnitsUnlockByUnlockVo: original delays, .65s Back/Linear
// scale and alpha tweens. The scene applies each prefab child's own pivot.
const clamp=x=>Math.max(0,Math.min(1,x));
const outBack=t=>1+2.70158*(t-1)**3+1.70158*(t-1)**2;
const inBack=t=>t*t*(2.70158*t-1.70158);
const bounce=t=>{const n=7.5625,d=2.75;if(t<1/d)return n*t*t;if(t<2/d)return n*(t-=1.5/d)*t+.75;if(t<2.5/d)return n*(t-=2.25/d)*t+.9375;return n*(t-=2.625/d)*t+.984375;};
export function sampleConstructionUnlock(type,seconds){
 const duration=Number(type)===4?1:.65,t=clamp(seconds/duration),state={sx:1,sy:1,offsetY:0,alpha:1};
 switch(Number(type)){
  case 1:state.sx=state.sy=1-inBack(t);break;
  case 2:state.sx=state.sy=outBack(t);break;
  case 3:state.sx=outBack(t);break;
  // DOJump's Y offset uses the child tween's elapsed fraction (the sequence's
  // eased position), not raw wall time. Upstream ShortcutExtensions.DOJump:
  // https://github.com/Demigiant/dotween/blob/develop/_DOTween.Assembly/DOTween/ShortcutExtensions.cs
  // The same OutQuad/Yoyo child chain and outer OutBounce were verified in the
  // APK's DOJump at RVA 0x19c26d0; see dotween-default-ease-evidence.json.
  case 4:{const u=bounce(t),jump=u<.5?1-(1-2*u)**2:1-(2*u-1)**2;state.offsetY=(1-u)**2+jump;break;}
  case 5:state.alpha=1-t;break;
  case 6:state.alpha=t;break;
 }
 return state;
}
export async function playConstructionUnlock(scene,units,{signal,timeScale=5/3,disappear=false}={}){
 const selected=units.filter(u=>(disappear?[1,5]:[2,3,4,6]).includes(Number(u.unlockAnimType)));if(!selected.length)return;
 const duration=Math.max(...selected.map(u=>(Number(u.unlockAnimDelay)||0)+(Number(u.unlockAnimType)===4?1:.65))),start=performance.now();
 await new Promise((resolve,reject)=>{let raf;const cancel=()=>{cancelAnimationFrame(raf);reject(Object.assign(Error('建设动画已关闭'),{name:'AbortError'}));};if(signal?.aborted)return cancel();signal?.addEventListener('abort',cancel,{once:true});const frame=now=>{if(signal?.aborted)return cancel();const time=(now-start)/1000*timeScale,unitAnimations={};for(const u of selected)unitAnimations[String(u.unitId)]=sampleConstructionUnlock(u.unlockAnimType,Math.max(0,time-(Number(u.unlockAnimDelay)||0)));scene.draw({...scene.state,unitAnimations});if(time<duration)raf=requestAnimationFrame(frame);else{signal?.removeEventListener('abort',cancel);scene.draw({...scene.state,unitAnimations:{}});resolve();}};frame(start);});
}
