const ROOT='assets/scene/skins/ink/';
export const MARKET_GROUND_ASSET=ROOT+'market-ground-v1.webp';
export const MARKET_GROUND_Y=-.002;
const IDENTITY=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1];
const SCALE=.9,HALF=Math.SQRT1_2,SHADOW='ink:tile-contact-shadow';

// The texture occupies the same ground plane as the native board. A short
// transparent skirt beneath the outer row blends it into the existing street.
function groundMesh(){
 const positions=[],uv=[],colors=[],indices=[],steps=32,extent=3.7,solid=3.2;
 for(let j=0;j<=steps;j++)for(let i=0;i<=steps;i++){
  const u=-extent+2*extent*i/steps,v=-extent+2*extent*j/steps;
  positions.push((u+v)*HALF*SCALE,MARKET_GROUND_Y,(-u+v)*HALF*SCALE);
  uv.push(i/steps,j/steps);
  const t=Math.min(1,Math.max(0,(extent-Math.max(Math.abs(u),Math.abs(v)))/(extent-solid)));
  colors.push(1,1,1,t*t*(3-2*t));
  if(i<steps&&j<steps){const n=j*(steps+1)+i;indices.push(n,n+1,n+steps+2,n,n+steps+2,n+steps+1);}
 }
 return {positions,uv,colors,indices};
}

function hull(points){
 const sorted=[...new Map(points.map(p=>[p.join(','),p])).values()].sort((a,b)=>a[0]-b[0]||a[1]-b[1]);
 const cross=(a,b,c)=>(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);
 const half=list=>{const out=[];for(const p of list){while(out.length>1&&cross(out.at(-2),out.at(-1),p)<=0)out.pop();out.push(p);}return out;};
 return [...half(sorted).slice(0,-1),...half([...sorted].reverse()).slice(0,-1)];
}

export class InkMarketGround{
 constructor(scene){this.scene=scene;this.mesh=groundMesh();this.footprints=new Map();}
 async load(){
  const image=new Image();await new Promise((resolve,reject)=>{image.onload=resolve;image.onerror=()=>reject(new Error('市集地面贴图加载失败'));image.src=MARKET_GROUND_ASSET;});
  this.scene.images[MARKET_GROUND_ASSET]=image;
  const white=document.createElement('canvas');white.width=white.height=1;const ctx=white.getContext('2d');ctx.fillStyle='#fff';ctx.fillRect(0,0,1,1);this.scene.images[SHADOW]=white;
  return this;
 }
 draw(render){this.scene.geometry3D(render,this.mesh,IDENTITY,MARKET_GROUND_ASSET,0,1,[1,1,1,1],this.mesh.indices,null,true,.001);}
 footprint(name){
  if(!this.footprints.has(name)){
   const mesh=this.scene.meshes[name],low=Math.min(...mesh.positions.filter((_,i)=>i%3===1)),points=[];
   for(let i=0;i<mesh.positions.length;i+=3)if(mesh.positions[i+1]<low+.035)points.push([mesh.positions[i],mesh.positions[i+2]]);
   this.footprints.set(name,hull(points));
  }
  return this.footprints.get(name);
 }
 drawContacts(render,matrices){
  const s=this.scene,g=render.gl;g.depthMask(false);g.blendFunc(g.SRC_ALPHA,g.ONE_MINUS_SRC_ALPHA);
  const positions=[],uv=[],colors=[],indices=[];
  for(const tile of s.data.squares){
   const source=s.prefabs[String(tile.id)],edge=this.footprint(source.meshName),matrix=matrices.get(tile.id-1);
   if(edge.length<3)continue;
   const cx=edge.reduce((n,p)=>n+p[0],0)/edge.length,cz=edge.reduce((n,p)=>n+p[1],0)/edge.length;
   const start=positions.length/3,alpha=.18/(1+Math.max(0,matrix[13])*4);
   const vertex=(x,z,a)=>{positions.push((matrix[0]*x+matrix[8]*z+matrix[12])*SCALE+.012,MARKET_GROUND_Y+.001,(matrix[2]*x+matrix[10]*z+matrix[14])*SCALE-.012);uv.push(.5,.5);colors.push(.28,.23,.17,a);};
   vertex(cx,cz,alpha);
   for(const[x,z]of edge)vertex(x,z,alpha);
   for(const[x,z]of edge){const dx=x-cx,dz=z-cz,length=Math.hypot(dx,dz)||1;vertex(x+dx/length*.075,z+dz/length*.075,0);}
   for(let i=0;i<edge.length;i++){
    const a=start+1+i,b=start+1+(i+1)%edge.length,c=a+edge.length,d=b+edge.length;
    indices.push(start,a,b,a,c,d,a,d,b);
   }
  }
  const mesh={positions,uv,colors,indices};s.geometry3D(render,mesh,IDENTITY,SHADOW,0,1,[1,1,1,1],indices,null,true,.001);
  g.depthMask(true);
 }
}
