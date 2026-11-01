// Pan only the world. HUD actions and modal scrolling keep their original events.
export function installScenePan({game,scene,canPan,getPosition}){
 let gesture=null,suppressClick=false,lastTap=null;
 game.classList.add('scene-pan-enabled');
 const allowed=target=>target instanceof Element&&!target.closest('#main-ui,#modal-layer,#loading')&&(!target.closest('[data-action],button,a,[role="button"]')||!!target.closest('.world-hit'));
 const finish=(event,cancelled=false)=>{
  if(!gesture||event.pointerId!==gesture.id)return;
  const g=gesture;gesture=null;game.classList.remove('scene-panning');
  if(game.hasPointerCapture(g.id))game.releasePointerCapture(g.id);
  if(g.dragged){if(!cancelled&&canPan()){const rect=game.getBoundingClientRect();scene.panFrom(g.camera,(event.clientX-g.x)*750/rect.width,(event.clientY-g.y)*1624/rect.height);}suppressClick=!cancelled;lastTap=null;return;}
  if(cancelled||!canPan()||!allowed(event.target)){lastTap=null;return;}
  const now=performance.now();
  if(lastTap&&now-lastTap.time<320&&Math.hypot(event.clientX-lastTap.x,event.clientY-lastTap.y)<24){lastTap=null;scene.follow(getPosition());scene.requestFrame();}
  else lastTap={time:now,x:event.clientX,y:event.clientY};
 };
 game.addEventListener('pointerdown',event=>{
  suppressClick=false;
  if(gesture){lastTap=null;finish({pointerId:gesture.id},true);return;}
  if(event.isPrimary===false||event.button!==0||!canPan()||!allowed(event.target))return;
  gesture={id:event.pointerId,x:event.clientX,y:event.clientY,camera:{...scene.cameraWorld},dragged:false};
 },true);
 window.addEventListener('pointermove',event=>{
  const g=gesture;if(!g||event.pointerId!==g.id)return;
  if(!canPan()){finish(event,true);return;}
  const dx=event.clientX-g.x,dy=event.clientY-g.y;
  if(!g.dragged){if(Math.hypot(dx,dy)<6)return;g.dragged=true;lastTap=null;game.setPointerCapture(g.id);game.classList.add('scene-panning');}
  event.preventDefault();
  const rect=game.getBoundingClientRect();scene.panFrom(g.camera,dx*750/rect.width,dy*1624/rect.height);
 },{passive:false});
 window.addEventListener('pointerup',event=>finish(event));
 window.addEventListener('pointercancel',event=>finish(event,true));
 // Touch starts with implicit capture on the canvas/button. Its bubbling loss
 // while transferring capture to the game is not the end of this gesture.
 game.addEventListener('lostpointercapture',event=>{if(event.target===game)finish(event,true);});
 for(const name of ['blur','resize'])window.addEventListener(name,()=>{if(gesture)finish({pointerId:gesture.id},true);lastTap=null;});
 game.addEventListener('click',event=>{if(suppressClick){suppressClick=false;event.preventDefault();event.stopImmediatePropagation();}},true);
}
