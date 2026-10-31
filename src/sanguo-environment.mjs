import{multiply,inverse}from './motion.mjs';
const UP=Math.cos(35*Math.PI/180),PITCH=Math.sin(35*Math.PI/180),IDENTITY=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1];
const ROOT='assets/scene/skins/sanguo/',GROUND=ROOT+'ground-v2.png',BUILDINGS=ROOT+'buildings-v3.png',LANDSCAPE=ROOT+'landscape-v3.png',DISTRICT=ROOT+'district-v4.png';
export const SANGUO_ENVIRONMENT_ASSETS=[GROUND,BUILDINGS,LANDSCAPE,DISTRICT];
const load=url=>new Promise((resolve,reject)=>{const i=new Image();i.onload=()=>resolve(i);i.onerror=()=>reject(new Error('三国场景资源加载失败：'+url));i.src=url;});
const billboard=(x,y,z,w,h)=>[w,0,0,0,0,h*UP,h*PITCH,0,0,-PITCH,UP,0,x,y,z,1];
export class SanguoEnvironment{
 constructor(scene){this.scene=scene;this.skinVersion='sanguo-v4';this.cells=[];this.boardCache=new Map();this.drawn=[];this.removedEars={};this.placements=[
  {role:'market',kind:0,position:[1.8,.02,4.8],size:[2.7,2.2]},
  {role:'far-shop',kind:2,position:[4.2,.02,5.9],size:[1.75,1.75]},
  {role:'near-gate',kind:1,position:[-.8,.02,-7.1],size:[2.05,2]},
  {role:'warehouse',kind:2,position:[2.6,.02,-4.9],size:[1.6,1.5]},
  {role:'wall',kind:6,position:[-3.3,.005,3.2],size:[2.6,1.05]},
  {role:'wall',kind:6,position:[4.6,.005,2.4],size:[-2.3,1]},
  {role:'wall',kind:6,position:[2.3,.005,-5.8],size:[2.6,1.05]},
  {role:'green-tree',kind:4,position:[-4.8,.01,1.8],size:[1.7,1.6]},
  {role:'green-tree',kind:4,position:[-2.4,.01,5],size:[1.8,1.6]},
  {role:'green-tree',kind:4,position:[1.3,.01,6.6],size:[1.8,1.5]},
  {role:'maple',kind:5,position:[4.8,.01,3.4],size:[1.7,1.55]},
  {role:'green-tree',kind:4,position:[5.8,.01,-1],size:[1.6,1.5]},
  {role:'maple',kind:5,position:[4,.01,-4.6],size:[1.8,1.65]},
  {role:'green-tree',kind:4,position:[-1.3,.01,-6],size:[1.7,1.6]},
  {role:'green-tree',kind:4,position:[-5,.01,-2.4],size:[1.7,1.6]},
  {role:'banners',kind:7,position:[-3.8,.01,1.8],size:[.9,1.65]},
  {role:'banners',kind:7,position:[4.7,.01,-1.8],size:[.9,1.5]},
  {role:'far-house',kind:2,position:[-3.8,.01,10.5],size:[1.8,1.65]},
  {role:'far-house',kind:2,position:[1.0,.01,12.2],size:[1.9,1.7]},
  {role:'far-house',kind:0,position:[5.2,.01,10.0],size:[2.2,1.65]},
  {role:'far-gate',kind:1,position:[-.8,.01,8.8],size:[1.8,1.7]},
  {role:'far-tree',kind:4,position:[-2.5,.01,9.0],size:[1.8,1.6]},
  {role:'far-tree',kind:4,position:[3.2,.01,10.3],size:[1.7,1.55]},
  {role:'far-tree',kind:5,position:[-6.4,.01,7.5],size:[1.7,1.55]},
  {role:'far-wall',kind:6,position:[-4,.005,8],size:[2.5,1.05]},
  {role:'far-wall',kind:6,position:[4.1,.005,9],size:[2.6,1.05]},
  {role:'command-hall',kind:8,position:[-2.2,.01,4.1],size:[2.8,2.15]},
  {role:'stable',kind:9,position:[-1.8,.01,-4.7],size:[2.2,1.8]},
  {role:'tea-shop',kind:10,position:[4.35,.01,-.6],size:[2.15,1.75]},
  {role:'pavilion',kind:11,position:[-5.4,.01,5.7],size:[2.1,1.9]},
  {role:'courtyard-residence',kind:8,position:[3.25,.01,-6.4],size:[2.5,2]},
  {role:'outer-stable',kind:9,position:[5.2,.01,7.1],size:[2.05,1.7]},
  {role:'far-tea-shop',kind:10,position:[-6.5,.01,9.4],size:[2.0,1.65]},
  {role:'outer-pavilion',kind:11,position:[-7.4,.01,-3.1],size:[2.3,1.95]},
  {role:'side-wall',kind:6,position:[-5.0,.005,-2.1],size:[-2.4,1.05]},
  {role:'side-wall',kind:6,position:[6.0,.005,4.7],size:[2.4,1.05]}


 ];}
 async load(){const s=this.scene;s.images[GROUND]=await load(GROUND);for(const url of [BUILDINGS,LANDSCAPE,DISTRICT])await this.loadAtlas(url);
 const positions=[],uv=[],indices=[];for(let x=-16;x<16;x+=4)for(let z=-16;z<16;z+=4){const n=positions.length/3;for(const[a,b]of [[x,z],[x+4,z],[x+4,z+4],[x,z+4]])positions.push((a+b)*Math.SQRT1_2,-.08,(-a+b)*Math.SQRT1_2);uv.push(0,0,1,0,1,1,0,1);indices.push(n,n+1,n+2,n,n+2,n+3);}this.ground={positions,uv,indices};return this;
 }
 async loadAtlas(url){const image=await load(url),c=document.createElement('canvas');c.width=image.width;c.height=image.height;const ctx=c.getContext('2d');ctx.drawImage(image,0,0);const imageData=ctx.getImageData(0,0,c.width,c.height),pixels=imageData.data,seen=new Uint8Array(c.width*c.height),groups=[[],[],[],[]];
 // Segment the whole sheet first: some roofs/feet cross the nominal sheet midpoint.
 // Assign complete components to a cell, never split a building at that midpoint.
 for(let k=0;k<seen.length;k++){if(seen[k]||pixels[k*4+3]<190)continue;seen[k]=1;const q=[k];let minX=c.width,maxX=0,minY=c.height,maxY=0;for(let head=0;head<q.length;head++){const p=q[head],x=p%c.width,y=Math.floor(p/c.width);minX=Math.min(minX,x);maxX=Math.max(maxX,x);minY=Math.min(minY,y);maxY=Math.max(maxY,y);for(const n of[p-1,p+1,p-c.width,p+c.width]){if(n<0||n>=seen.length||seen[n]||Math.abs(n%c.width-x)>1)continue;if(pixels[n*4+3]>=190){seen[n]=1;q.push(n);}}}if(q.length<48)continue;const cell=((minY+maxY)/2>=c.height/2?2:0)+((minX+maxX)/2>=c.width/2?1:0);groups[cell].push({q,minX,maxX,minY,maxY});}
 for(let i=0;i<4;i++){if(!groups[i].length)throw new Error('Empty environment cell '+url+':'+i);const largest=groups[i].reduce((a,b)=>a.q.length>b.q.length?a:b);const parts=url===BUILDINGS?[largest]:groups[i].filter(p=>p.q.length>=500);const keep=new Uint8Array(c.width*c.height);let minX=c.width,maxX=0,minY=c.height,maxY=0;for(const part of parts){minX=Math.min(minX,part.minX);maxX=Math.max(maxX,part.maxX);minY=Math.min(minY,part.minY);maxY=Math.max(maxY,part.maxY);for(const k of part.q){const xx=k%c.width,yy=Math.floor(k/c.width);for(let a=-2;a<=2;a++)for(let b=-2;b<=2;b++){const x=xx+a,y=yy+b;if(x>=0&&x<c.width&&y>=0&&y<c.height)keep[y*c.width+x]=1;}}}const left=Math.max(0,minX-4),right=Math.min(c.width,maxX+5),top=Math.max(0,minY-4),bottom=Math.min(c.height,maxY+5),u0=left/c.width,u1=right/c.width,v0=1-bottom/c.height,v1=1-top/c.height;
 const crop=document.createElement('canvas');crop.width=right-left;crop.height=bottom-top;const cropCtx=crop.getContext('2d'),out=cropCtx.createImageData(crop.width,crop.height);for(let y=top;y<bottom;y++)for(let x=left;x<right;x++){const src=y*c.width+x;if(!keep[src])continue;const dst=((y-top)*crop.width+x-left)*4;for(let ch=0;ch<4;ch++)out.data[dst+ch]=pixels[src*4+ch];}cropCtx.putImageData(out,0,0);const key=url+':cell:'+i;this.scene.images[key]=crop;
 this.cells.push({texture:key,positions:[-.5,-.02,0,.5,-.02,0,.5,.98,0,-.5,.98,0],normals:[0,0,1,0,0,1,0,0,1,0,0,1],uv:[0,0,1,0,1,1,0,1],indices:[0,1,2,0,2,3],crop:[left,top,right-left,bottom-top]});}
 this.scene.images[url]=image;
 }
 prepareMeshes(){const s=this.scene;for(const[name,mesh]of Object.entries(s.meshes))if(name.startsWith('checkerboard')&&mesh.colors)s.meshes[name]={...mesh,colors:mesh.colors.map((c,i)=>i%4===3?c:1-(1-c)*.45)};for(const name of ['checkerboard_04','checkerboard_05']){const mesh=s.meshes[name],adj=Array.from({length:mesh.positions.length/3},()=>new Set());for(let j=0;j<mesh.indices.length;j+=3){const ids=mesh.indices.slice(j,j+3);for(const id of ids)for(const next of ids)adj[id].add(next);}const visited=new Set(),remove=new Set();for(let k=0;k<adj.length;k++){if(visited.has(k))continue;const q=[k];visited.add(k);for(let h=0;h<q.length;h++)for(const n of adj[q[h]])if(!visited.has(n)){visited.add(n);q.push(n);}const ys=q.map(n=>mesh.positions[n*3+1]);if(q.length<20&&Math.min(...ys)>.43&&Math.max(...ys)>.6)for(const n of q)remove.add(n);}const indices=[];for(let j=0;j<mesh.indices.length;j+=3)if(!mesh.indices.slice(j,j+3).some(n=>remove.has(n)))indices.push(...mesh.indices.slice(j,j+3));s.meshes[name]={...mesh,indices};this.removedEars[name]={vertices:remove.size,triangles:(mesh.indices.length-indices.length)/3};}}
 drawSprite(render,kind,matrix,scale=1){const s=this.scene,g=render.gl;g.blendFunc(g.SRC_ALPHA,g.ONE_MINUS_SRC_ALPHA);s.geometry3D(render,this.cells[kind],matrix,this.cells[kind].texture,0,scale,[1,1,1,1],this.cells[kind].indices,null,true,.5);}
 drawGround(render){const g=render.gl;g.depthMask(true);this.scene.geometry3D(render,this.ground,IDENTITY,GROUND,0,1,[1,1,1,1],this.ground.indices,null,true);g.depthMask(false);for(const p of this.placements)this.worldShadow(render,p.position[0],p.position[2],Math.abs(p.size[0])*.38,Math.abs(p.size[0])*.18);g.disable(g.DEPTH_TEST);this.drawn=[];const list=[...this.placements].sort((a,b)=>b.position[2]-a.position[2]);for(const p of list){this.drawSprite(render,p.kind,billboard(...p.position,...p.size));this.drawn.push(p);}g.enable(g.DEPTH_TEST);g.depthMask(true);}
 worldShadow(render,x,z,w,h){const positions=[x,-.07,z],uv=[.5,.5],colors=[.2,.18,.15,.14],indices=[];for(let i=0;i<=24;i++){const a=i/24*Math.PI*2;positions.push(x+Math.cos(a)*w,-.07,z+Math.sin(a)*h);uv.push(.5,.5);colors.push(.2,.18,.15,0);if(i)indices.push(0,i,i+1);}const mesh={positions,uv,colors,indices};render.gl.blendFunc(render.gl.SRC_ALPHA,render.gl.ONE_MINUS_SRC_ALPHA);this.scene.geometry3D(render,mesh,IDENTITY,GROUND,0,1,[1,1,1,1],indices,null,true);}
 drawFund(render){this.drawSprite(render,3,billboard(0,.084,2.1,.62,.68));}
 drawBoardShadows(render,owner){const g=render.gl;g.depthMask(false);g.blendFunc(g.SRC_ALPHA,g.ONE_MINUS_SRC_ALPHA);for(const[id,entry]of this.boardCache){const item=owner.entries.find(x=>!x.prop.isShadow&&id.startsWith(x.id+':'));if(!item)continue;const d=multiply(owner.matrix(item.id,item.prop),entry.baseInverse),m=multiply(d,entry.matrix),x=m[12]*.9,y=m[13]*.9+.006,z=m[14]*.9,positions=[x,y,z],uv=[.5,.5],colors=[.15,.14,.12,.16],indices=[];for(let i=0;i<=20;i++){const a=i/20*Math.PI*2;positions.push(x+Math.cos(a)*.24,y,z+Math.sin(a)*.13);uv.push(.5,.5);colors.push(.15,.14,.12,0);if(i)indices.push(0,i,i+1);}const mesh={positions,uv,colors,indices};this.scene.geometry3D(render,mesh,IDENTITY,GROUND,0,1,[1,1,1,1],indices,null,true);}}
 boardProp(render,owner,id,prop){const s=this.scene,key=id+':'+prop.path;let entry=this.boardCache.get(key);if(!entry){const mesh=owner.data.meshes[prop.mesh],base=prop.matrixInNormalPrefab,points=[];for(let i=0;i<mesh.positions.length;i+=3){const[a,b,c]=mesh.positions.slice(i,i+3);points.push([base[0]*a+base[4]*b+base[8]*c+base[12],base[1]*a+base[5]*b+base[9]*c+base[13],base[2]*a+base[6]*b+base[10]*c+base[14]]);}const minY=Math.min(...points.map(p=>p[1])),feet=points.filter(p=>p[1]<minY+.02),foot=[(Math.min(...feet.map(p=>p[0]))+Math.max(...feet.map(p=>p[0])))/2,minY,(Math.min(...feet.map(p=>p[2]))+Math.max(...feet.map(p=>p[2])))/2],sizes={1:[.571417,.544405],21:[.986383,.653084],31:[.549235,.465651]},[w,h]=sizes[id],matrix=billboard(...foot,w/.9,h/.9);entry={matrix,baseInverse:inverse(base)};this.boardCache.set(key,entry);}const native=owner.matrix(id,prop),delta=multiply(native,entry.baseInverse),matrix=multiply(delta,entry.matrix);this.drawSprite(render,id===21?1:id===31?0:2,matrix,.9);owner.drawn.push({id,path:prop.path,mesh:prop.mesh,matrix:native,themed:true});}
}
