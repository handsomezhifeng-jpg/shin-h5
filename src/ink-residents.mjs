import{INK_SURROUNDING_HEIGHT}from './ink-character-scale.mjs';
import{sampleMarketResidents,sampleSweeperAnimation}from './ink-resident-rules.mjs';
const ROOT='assets/scene/skins/ink/';
export const INK_RESIDENT_ASSETS=['residents-v4.json','residents-customers-v4.webp','residents-vendors-v4.webp','residents-seedance-sweeper-v1.json','residents-original-sweep-20-v1.webp','residents-original-sweeper-walk-24-v1.webp'].map(n=>ROOT+n);
const load=url=>new Promise((resolve,reject)=>{const im=new Image();im.onload=()=>resolve(im);im.onerror=()=>reject(Error('市集人物资源加载失败：'+url));im.src=url;});
const polygon=(c,points)=>{c.beginPath();points.forEach(([x,y],i)=>i?c.lineTo(x,y):c.moveTo(x,y));c.closePath();};
export class InkResidents{
 static async load(scene,background,coordinates){const manifests=await Promise.all(['residents-v4.json','residents-seedance-sweeper-v1.json'].map(async name=>{const r=await fetch(ROOT+name);if(!r.ok)throw Error('市集人物动作清单缺失：'+name);return r.json();})),[legacy,seedance]=manifests,{sweeper,...retained}=legacy.atlases,data={...legacy,atlases:{...retained,...seedance.atlases}},images=Object.fromEntries(await Promise.all(Object.entries(data.atlases).map(async([key,record])=>[key,await load(ROOT+record.url)])));return new InkResidents(scene,background,coordinates,data,images);}
 constructor(scene,background,coordinates,data,images){this.scene=scene;this.background=background;this.coordinates=coordinates;this.data=data;this.images=images;this.drawn=[];const c=this.doorLeaf=document.createElement('canvas');const artScale=background.width/1024;c.width=40*artScale;c.height=96*artScale;const x=c.getContext('2d');x.scale(artScale,artScale);polygon(x,[[3,26],[37,8],[37,73],[3,91]]);x.clip();x.drawImage(background,215*artScale,155*artScale,40*artScale,96*artScale,0,0,40,96);}
 get active(){return true;}
 sample(time){return sampleMarketResidents(Math.max(0,time));}
 project(x,y){const{unitX,unitY,centerY,up,pitch}=this.coordinates;return this.scene.project((x-512)*unitX,(centerY-y)*unitY*up-.08,(centerY-y)*unitY*pitch);}
 frame(atlas,index){return this.data.atlases[atlas].frames[index];}
 drawPerson(c,atlas,index,pose,{height,flip=false,shadow=true,proceduralMotion=true}={}){
  const f=this.frame(atlas,index),[sx,sy,w,h]=f.crop,unit=height/f.bodyHeight,[ax,ay]=f.anchor;
  c.save();c.globalAlpha=pose.alpha??1;
  if(pose.atDoor){polygon(c,[[218,181],[252,163],[252,229],[1100,229],[1100,1600],[-100,1600],[-100,246],[218,246]]);c.clip();}
  if(shadow){c.fillStyle='#72614725';c.beginPath();c.ellipse(pose.x,pose.y+1,height*.14*(pose.scale??1),height*.035,0,0,Math.PI*2);c.fill();}
  const step=proceduralMotion&&pose.walking?Math.sin((pose.local??0)*10)*.75:0;c.translate(pose.x,pose.y-Math.abs(step));c.scale((flip?-1:1)*(pose.scale??1),pose.scale??1);if(step)c.rotate(step*.009);
  c.drawImage(this.images[atlas],sx,sy,w,h,-ax*unit,-ay*unit,w*unit,h*unit);c.restore();
  const p=this.project(pose.x,pose.y),clip=this.data.atlases[atlas];this.drawn.push({id:pose.id,state:pose.state,variant:pose.variant,cycle:pose.cycle,frame:index,atlas,sequence:clip.reviewClip,frameCount:clip.frames.length,fps:clip.fps,flip,x:pose.x,y:pose.y,screen:p,alpha:pose.alpha??1,scale:pose.scale??1,height:height*(pose.scale??1),visible:true});
 }
 drawDoor(c,open){if(open<=0)return;const q=[[218,181],[252,163],[252,229],[218,246]];c.save();polygon(c,q);c.clip();const shade=c.createLinearGradient(218,180,252,245);shade.addColorStop(0,'#30251c');shade.addColorStop(1,'#66503a');c.fillStyle=shade;c.fill();c.save();const s=1-.89*open,tilt=.24*open;c.transform(s,tilt,0,1,218*(1-s),-218*tilt);c.drawImage(this.doorLeaf,215,155,40,96);c.restore();c.restore();}
 draw(ctx){
  this.startedAt??=this.scene.now;const time=this.timeOverride??Math.max(0,this.scene.now-this.startedAt),state=this.state=this.sample(time),{unitX,unitY}=this.coordinates,origin=this.project(0,0),scale=1624/(2*this.scene.zoom),height=INK_SURROUNDING_HEIGHT*5.5/(812*unitY);this.drawn=[];
  ctx.save();ctx.transform(unitX*scale,0,0,unitY*scale,origin.x,origin.y);ctx.imageSmoothingEnabled=true;ctx.imageSmoothingQuality='high';
  for(const v of state.vendors){const[x,y]=v.position;this.drawPerson(ctx,'vendors',v.row*3+v.frame,{...v,x,y,alpha:1},{height:height*.64,shadow:false});}
  // Actual painted counters occlude the sellers' lower torso. Reuse their exact
  // pixels before drawing the shoppers standing on the foreground pavement.
  for(const v of state.vendors){ctx.save();polygon(ctx,v.counter);ctx.clip();ctx.drawImage(this.background,0,0,1024,1536);ctx.restore();}
  this.drawDoor(ctx,state.sweeper.doorOpen);
  const people=[state.sweeper,...state.visitors].filter(p=>p.visible).sort((a,b)=>a.y-b.y);
  for(const person of people){const sweeper=person.id==='sweeper',animation=sweeper?sampleSweeperAnimation(person,this.data.atlases):{atlas:'customers',frame:person.variant*6+person.frame,flip:[2,3,5].includes(person.frame)!==person.faceRight};this.drawPerson(ctx,animation.atlas,animation.frame,person,{height,flip:animation.flip,proceduralMotion:!sweeper});
   if(sweeper&&person.state==='sweeping'){const phase=(time*1.7)%1;ctx.save();ctx.fillStyle=`rgba(150,126,86,${.13*(1-phase)})`;for(let n=0;n<3;n++){ctx.beginPath();ctx.ellipse(person.x-20+(n-1)*5,person.y-3-phase*9-n*2,2+phase*4,1+phase*1.6,0,0,Math.PI*2);ctx.fill();}ctx.restore();}
  }
  ctx.restore();
 }
}
