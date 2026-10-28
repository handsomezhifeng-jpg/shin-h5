const S=130, PITCH=.56, HALF=Math.SQRT1_2;
const loadImage=url=>new Promise((resolve,reject)=>{const image=new Image();image.onload=()=>resolve(image);image.onerror=()=>reject(new Error('图片加载失败：'+url));image.src=url;});
export const worldPoint=(x,y,z)=>({x:(x+z)*HALF*S,y:(x-z)*HALF*S*PITCH-y*S});
function texturedTriangle(ctx,image,p,q) {
  const [p0,p1,p2]=p,[q0,q1,q2]=q;
  const det=q0.x*(q1.y-q2.y)+q1.x*(q2.y-q0.y)+q2.x*(q0.y-q1.y);if(Math.abs(det)<.001)return;
  const a=(p0.x*(q1.y-q2.y)+p1.x*(q2.y-q0.y)+p2.x*(q0.y-q1.y))/det;
  const c=(p0.x*(q2.x-q1.x)+p1.x*(q0.x-q2.x)+p2.x*(q1.x-q0.x))/det;
  const e=(p0.x*(q1.x*q2.y-q2.x*q1.y)+p1.x*(q2.x*q0.y-q0.x*q2.y)+p2.x*(q0.x*q1.y-q1.x*q0.y))/det;
  const b=(p0.y*(q1.y-q2.y)+p1.y*(q2.y-q0.y)+p2.y*(q0.y-q1.y))/det;
  const d=(p0.y*(q2.x-q1.x)+p1.y*(q0.x-q2.x)+p2.y*(q1.x-q0.x))/det;
  const f=(p0.y*(q1.x*q2.y-q2.x*q1.y)+p1.y*(q2.x*q0.y-q0.x*q2.y)+p2.y*(q0.x*q1.y-q1.x*q0.y))/det;
  ctx.save();ctx.beginPath();ctx.moveTo(p0.x,p0.y);ctx.lineTo(p1.x,p1.y);ctx.lineTo(p2.x,p2.y);ctx.closePath();ctx.clip();ctx.transform(a,b,c,d,e,f);ctx.drawImage(image,0,0);ctx.restore();
}
export class OriginalScene {
  constructor(canvas,data,ui) {this.canvas=canvas;this.ctx=canvas.getContext('2d',{alpha:false});this.data=data;this.ui=ui;this.camera={x:0,y:-100};this.offset={x:375,y:790};this.position=0;this.spriteCache=new Map();this.images={};this.map=1;}
  async load() {
    const urls={map1:'assets/scene/bg_main_1_full.webp',map2:'assets/scene/bg_main_2_full.webp',atlas:'assets/scene/grid-atlas.png',shield:'assets/scene/shield.png',rent0:'assets/scene/avatar-3.png',rent1:'assets/scene/avatar-4.png',rent2:'assets/scene/avatar-6.png'};
    await Promise.all(Object.entries(urls).map(async([key,url])=>{this.images[key]=await loadImage(url);}));
    this.prefabs=await fetch('assets/scene/grid-prefabs.json').then(r=>r.json()).then(d=>d.prefabs);
    this.meshes=await fetch('assets/scene/grid-meshes.json').then(r=>{if(!r.ok)throw new Error('格子模型加载失败');return r.json();});
    const wanted=['icon_shield.png','icon_shield_01.png','icon_money.png','img_main_GachaMachine.png','img_event_shinchan_01.png'];
    for(const name of wanted){const url=this.ui.image(name);if(url){try{this.images[name]=await loadImage(url);}catch{}}}
    return this;
  }
  makeMeshRenderer() {
    const canvas=document.createElement('canvas'),gl=canvas.getContext('webgl',{alpha:true,antialias:true,preserveDrawingBuffer:true});
    if(!gl)throw new Error('浏览器不支持WebGL');
    const shader=(type,source)=>{const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(s));return s;};
    const program=gl.createProgram();gl.attachShader(program,shader(gl.VERTEX_SHADER,'attribute vec3 position;attribute vec2 uv;varying vec2 vUv;void main(){vUv=uv;gl_Position=vec4(position,1.0);}'));gl.attachShader(program,shader(gl.FRAGMENT_SHADER,'precision mediump float;uniform sampler2D atlas;varying vec2 vUv;void main(){vec4 c=texture2D(atlas,vUv);if(c.a<0.01)discard;gl_FragColor=c;}'));gl.linkProgram(program);
    const texture=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,texture);gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,true);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,this.images.atlas);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);gl.enable(gl.DEPTH_TEST);gl.depthFunc(gl.LEQUAL);gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);
    return {canvas,gl,program,texture,position:gl.getAttribLocation(program,'position'),uv:gl.getAttribLocation(program,'uv'),vertices:gl.createBuffer(),indices:gl.createBuffer()};
  }
  tileSprite(name,rotation=0,matrix=null) {
    const key=name+':'+rotation+':'+(matrix?matrix.join(','):'');if(this.spriteCache.has(key))return this.spriteCache.get(key);
    const mesh=this.meshes[name] || this.meshes.checkerboard_07_green;const angle=rotation*Math.PI/180,c=Math.cos(angle),s=Math.sin(angle);const points=[];
    for(let i=0;i<mesh.positions.length;i+=3){let [x,y,z]=mesh.positions.slice(i,i+3);if(matrix){const m=matrix;[x,y,z]=[m[0]*x+m[4]*y+m[8]*z+m[12],m[1]*x+m[5]*y+m[9]*z+m[13],m[2]*x+m[6]*y+m[10]*z+m[14]];}points.push(worldPoint(x*c+z*s,y,-x*s+z*c));}
    const minX=Math.floor(Math.min(...points.map(p=>p.x)))-3,minY=Math.floor(Math.min(...points.map(p=>p.y)))-3;
    const width=Math.ceil(Math.max(...points.map(p=>p.x))-minX)+3,height=Math.ceil(Math.max(...points.map(p=>p.y))-minY)+3;
    const canvas=document.createElement('canvas');canvas.width=width*2;canvas.height=height*2;const ctx=canvas.getContext('2d');ctx.scale(2,2);ctx.imageSmoothingEnabled=true;
    if(!this.glRenderer) this.glRenderer=this.makeMeshRenderer();
    const render=this.glRenderer;
    render.canvas.width=canvas.width;render.canvas.height=canvas.height;const gl=render.gl;
    gl.viewport(0,0,canvas.width,canvas.height);gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.useProgram(render.program);
    const vertices=[];
    for(let i=0;i<points.length;i++) {
      const p=points[i];let x=mesh.positions[i*3],y=mesh.positions[i*3+1],z=mesh.positions[i*3+2];if(matrix){const m=matrix;[x,y,z]=[m[0]*x+m[4]*y+m[8]*z+m[12],m[1]*x+m[5]*y+m[9]*z+m[13],m[2]*x+m[6]*y+m[10]*z+m[14]];}const rx=x*c+z*s,rz=-x*s+z*c;
      vertices.push((p.x-minX)/width*2-1,1-(p.y-minY)/height*2,-((rx-rz)*.707*.84+y*.54)/4,mesh.uv[i*2],mesh.uv[i*2+1]);
    }
    gl.bindBuffer(gl.ARRAY_BUFFER,render.vertices);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(vertices),gl.STATIC_DRAW);
    gl.enableVertexAttribArray(render.position);gl.vertexAttribPointer(render.position,3,gl.FLOAT,false,20,0);gl.enableVertexAttribArray(render.uv);gl.vertexAttribPointer(render.uv,2,gl.FLOAT,false,20,12);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,render.indices);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,new Uint16Array(mesh.indices),gl.STATIC_DRAW);gl.bindTexture(gl.TEXTURE_2D,render.texture);gl.drawElements(gl.TRIANGLES,mesh.indices.length,gl.UNSIGNED_SHORT,0);
    ctx.drawImage(render.canvas,0,0,width,height);
    const result={canvas,x:minX,y:minY,width,height};this.spriteCache.set(key,result);return result;
  }
  meshFor(tile) {const names={1:'checkerboard_01',2:'checkerboard_06',3:'checkerboard_07_green',4:'checkerboard_07_1_red',5:'checkerboard_02',6:'checkerboard_03',7:'checkerboard_15',8:'checkerboard_04',9:'checkerboard_07_yellow'};return names[tile.type] || names[3];}
  worldPosition(index) {const p=this.data.positions[index];return worldPoint(p.x,0,p.z);}
  screenPosition(index) {const p=this.worldPosition(index);return {x:p.x+this.offset.x+this.camera.x,y:p.y+this.offset.y+this.camera.y};}
  follow(index,immediate=false) {
    const p=this.worldPosition(index);const target={x:Math.max(-300,Math.min(300,-p.x)),y:Math.max(-160,Math.min(230,230-p.y))};
    if(immediate){this.camera=target;return Promise.resolve();}
    const start={...this.camera};const time=performance.now();return new Promise(resolve=>{const tick=()=>{const t=Math.min(1,(performance.now()-time)/420);const k=1-Math.pow(1-t,3);this.camera={x:start.x+(target.x-start.x)*k,y:start.y+(target.y-start.y)*k};this.draw();if(t<1)requestAnimationFrame(tick);else resolve();};tick();});
  }
  draw(state=this.state) {
    if(state)this.state=state;if(!this.state||!this.images.atlas)return;const s=this.state,ctx=this.ctx;
    ctx.clearRect(0,0,750,1624);ctx.fillStyle='#5c9073';ctx.fillRect(0,0,750,1624);
    const bg=this.images[s.map%2===1?'map1':'map2'];const scale=1752/bg.width;
    ctx.drawImage(bg,this.offset.x+this.camera.x-bg.width*scale*.5,this.offset.y+this.camera.y-bg.height*.5*scale,bg.width*scale,bg.height*scale);
    const tiles=this.data.squares.map((tile,index)=>({tile,index,point:this.screenPosition(index)})).sort((a,b)=>a.point.y-b.point.y);
    for(const {tile,index,point:p} of tiles){const source=tile.id===11?null:this.prefabs[String(tile.id)];let matrix=null;if(source?.modelMatrix){const a=source.instanceMatrix,b=source.modelMatrix;matrix=Array.from({length:16},(_,i)=>{const row=i%4,col=Math.floor(i/4);return a[row]*b[col*4]+a[row+4]*b[col*4+1]+a[row+8]*b[col*4+2]+a[row+12]*b[col*4+3];});matrix[12]-=source.instance.position.x;matrix[13]-=source.instance.position.y;matrix[14]-=source.instance.position.z;}const sprite=this.tileSprite(source&&this.meshes[source.meshName]?source.meshName:this.meshFor(tile),0,matrix);ctx.drawImage(sprite.canvas,p.x+sprite.x,p.y+sprite.y,sprite.width,sprite.height);
      if([1,3,4,9].includes(tile.type)){ctx.save();ctx.translate(p.x,p.y-2);ctx.font='bold 19px Microsoft YaHei';ctx.textAlign='center';ctx.lineWidth=4;ctx.strokeStyle='#403e32';ctx.fillStyle=tile.type===4?'#ffe6dd':'#fff4ac';const value=Math.round(tile.param*(this.data.maps[Math.min(s.map-1,2)]?.inflation || 20));ctx.strokeText((tile.type===4?'-':'')+value,0,0);ctx.fillText((tile.type===4?'-':'')+value,0,0);ctx.restore();}
    }
    for(const pos of s.shields){const p=this.screenPosition(pos);const icon=this.images.shield;if(icon)ctx.drawImage(icon,p.x-25,p.y-78,50,58);else{ctx.save();ctx.fillStyle='#9dd5ee';ctx.strokeStyle='white';ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(p.x-21,p.y-77);ctx.lineTo(p.x+21,p.y-77);ctx.lineTo(p.x+18,p.y-48);ctx.lineTo(p.x,p.y-35);ctx.lineTo(p.x-18,p.y-48);ctx.closePath();ctx.fill();ctx.stroke();ctx.restore();}}
    for(const pos of s.rents){const p=this.screenPosition(pos);const pic=this.images['rent'+(pos%3)];if(pic){ctx.save();ctx.beginPath();ctx.arc(p.x,p.y-55,24,0,Math.PI*2);ctx.clip();ctx.drawImage(pic,p.x-30,p.y-90,60,70);ctx.restore();ctx.strokeStyle='#fff4ce';ctx.lineWidth=3;ctx.beginPath();ctx.arc(p.x,p.y-55,24,0,Math.PI*2);ctx.stroke();}}
    const p=this.screenPosition(this.position);ctx.save();ctx.fillStyle='#31502c44';ctx.beginPath();ctx.ellipse(p.x,p.y+4,35,10,0,0,Math.PI*2);ctx.fill();ctx.restore();
    if(this.pieceElement){this.pieceElement.style.left=p.x+'px';this.pieceElement.style.top=(p.y-10)+'px';}this.onDraw?.(this.camera);
  }
  setPiece(index,element) {this.pieceElement=element;this.position=index;const p=this.screenPosition(index);element.style.left=p.x+'px';element.style.top=(p.y-10)+'px';}
  async move(path,element,onStep) {
    for(const index of path){const from=this.position;const target=this.screenPosition(index),start=this.screenPosition(from);const duration=150;const at=performance.now();
      await new Promise(resolve=>{const tick=()=>{const t=Math.min(1,(performance.now()-at)/duration);element.style.left=(start.x+(target.x-start.x)*t)+'px';element.style.top=(start.y+(target.y-start.y)*t-10-Math.sin(t*Math.PI)*16)+'px';if(t<1)requestAnimationFrame(tick);else resolve();};tick();});this.position=index;onStep?.(index);if(index%5===0){await this.follow(index);this.setPiece(index,element);} }
    await this.follow(this.position);this.setPiece(this.position,element);
  }
}