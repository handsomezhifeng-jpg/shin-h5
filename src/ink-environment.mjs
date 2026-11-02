import {SanguoEnvironment} from './sanguo-environment.mjs';
import {INK_SURROUNDING_HEIGHT} from './ink-character-scale.mjs';
import {InkResidents,INK_RESIDENT_ASSETS} from './ink-residents.mjs';
import {InkMarketGround,MARKET_GROUND_ASSET} from './ink-market-ground.mjs';
const ROOT='assets/scene/skins/ink/';
export const INK_ASSETS=[...['north-courtyard.webp','market-square.webp','south-market.webp','cast-watercolor-v2.webp','villagers-v3.json'].map(n=>ROOT+n),MARKET_GROUND_ASSET,...INK_RESIDENT_ASSETS];
const UP=Math.cos(35*Math.PI/180), PITCH=Math.sin(35*Math.PI/180);
const RADIUS=4.588338483*.9, UNIT_X=RADIUS/404, UNIT_Y=RADIUS*PITCH/256;
const CENTER_Y=730+(.26*.9+.08)*UP/UNIT_Y;
export const INK_OVERVIEW_ZOOM=6.8;
// Painted regions are registered to the native board, not to the viewport.
// Thus dragging, camera follow, zoom and all forty landing positions remain live.
export class InkEnvironment extends SanguoEnvironment {
 // Both following and dragging use the actual painted frame. Its projected
 // bounds must cover the canvas, including beneath the translucent HUD.
 cameraBounds(zoom=INK_OVERVIEW_ZOOM){
  const halfWidth=zoom*750/1624;
  const left=-512*UNIT_X+halfWidth,right=512*UNIT_X-halfWidth;
  const bottom=(CENTER_Y-1536)*UNIT_Y-.08*UP,top=CENTER_Y*UNIT_Y-.08*UP;
  return {left,right,bottom:(bottom+10*PITCH+zoom)/UP,top:(top+10*PITCH-zoom)/UP};
 }
 panCamera(p,zoom=INK_OVERVIEW_ZOOM){
  const b=this.cameraBounds(zoom),clip=(v,lo,hi)=>lo<=hi?Math.max(lo,Math.min(hi,v)):(lo+hi)/2;
  return {x:clip(p.x,b.left,b.right),y:clip(p.y,b.bottom,b.top),z:-10};
 }
 async load(){
  await super.load();
  this.skinVersion='ink-market-ground-v1';
  this.hideCentralFund=true;
  this.marketGround=await new InkMarketGround(this.scene).load();
  this.placements=[];
  this.panels=[];
  // The painted 10-by-10 diamond spans (108,730), (512,474),
  // (916,730), (512,986). Register those to the forty-step corner
  // centers; the painting's vertical ratio differs from our 35-degree camera.
  const unitX=UNIT_X, unitY=UNIT_Y;
  const centerX=512, centerY=CENTER_Y;
  const panel=(url,leftPx,rightPx,topPx,bottomPx,flipX=false,flipY=false)=>{
   const left=(leftPx-centerX)*unitX,right=(rightPx-centerX)*unitX;
   const low=(centerY-bottomPx)*unitY,high=(centerY-topPx)*unitY;
   const u0=flipX?1:0,u1=flipX?0:1,v0=flipY?1:0,v1=flipY?0:1;
   const mesh={positions:[left,low*UP,low*PITCH,right,low*UP,low*PITCH,right,high*UP,high*PITCH,left,high*UP,high*PITCH],uv:[u0,v0,u1,v0,u1,v1,u0,v1],indices:[0,1,2,0,2,3]};
   this.panels.push({url,mesh});
  };
  for(const [name,top,bottom] of [['north-courtyard',0,480],['market-square',480,1000],['south-market',1000,1536]]){
   const url=ROOT+name+'.webp';
   this.scene.images[url]=await new Promise((resolve,reject)=>{const image=new Image();image.onload=()=>resolve(image);image.onerror=reject;image.src=url;});
   panel(url,0,1024,top,bottom);
  }
  await this.composeVillagers();
  // Extend the actual painting's paving beyond its frame, so camera drags never
  // reveal the previous green landscape. This crop is an empty street patch.
  const street=document.createElement('canvas');street.width=street.height=384;
  const south=this.scene.images[ROOT+'south-market.webp'],artScale=south.width/1024;
  street.getContext('2d').drawImage(south,580*artScale,220*artScale,105*artScale,105*artScale,0,0,384,384);
  this.scene.images['assets/scene/skins/sanguo/ground-v2.png']=street;
  return this;
 }
 async composeVillagers(){
  const layout=await fetch(ROOT+'villagers-v3.json').then(r=>{if(!r.ok)throw Error('Missing original villagers');return r.json();});
  const artScale=this.artScale=this.scene.images[ROOT+'north-courtyard.webp'].width/1024;
  const painting=document.createElement('canvas');painting.width=1024*artScale;painting.height=1536*artScale;const c=painting.getContext('2d');c.scale(artScale,artScale);
  const regions=[['north-courtyard',0,480],['market-square',480,1000],['south-market',1000,1536]];
  for(const [name,top,bottom]of regions)c.drawImage(this.scene.images[ROOT+name+'.webp'],0,top,1024,bottom-top);
  const height=INK_SURROUNDING_HEIGHT*5.5/(812*UNIT_Y);this.villagers=layout.characters.map(person=>({id:person.id,standing:person.standing,sourceHeight:height,referenceHeight:INK_SURROUNDING_HEIGHT,position:person.destination}));
  this.residents=await InkResidents.load(this.scene,painting,{unitX:UNIT_X,unitY:UNIT_Y,centerY:CENTER_Y,up:UP,pitch:PITCH});
 }
 drawResidents(ctx){this.residents?.draw(ctx);}
 get active(){return !!this.residents?.active;}
 // Restore the native block thickness. Top surfaces and all landing hooks stay
 // at their original height, so actors and grid props still meet the tile tops.
 prepareMeshes(){
  super.prepareMeshes();
 }
 drawGround(render){
  super.drawGround(render);
  const gl=render.gl;
  gl.disable(gl.DEPTH_TEST);gl.depthMask(false);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);
  const matrix=[1,0,0,0,0,1,0,0,0,0,1,0,0,-.08,0,1];
  for(const {url,mesh} of this.panels)this.scene.geometry3D(render,mesh,matrix,url,0,1,[1,1,1,1],mesh.indices,null,true);
  this.marketGround.draw(render);
  gl.depthMask(true);gl.clear(gl.DEPTH_BUFFER_BIT);gl.enable(gl.DEPTH_TEST);
 }
 // The approved painting supplies its own merchants; remove the former gold monuments.
 drawCarts(){}
 // The reference keeps this square open; the sidebar still supplies fund access.
 drawFund(){}
 drawTileShadows(render,matrices){this.marketGround.drawContacts(render,matrices);}
}
