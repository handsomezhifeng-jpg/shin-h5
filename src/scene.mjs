// CameraController.NormalChessboard: (0,6,-10), X=35 degrees, orthographicSize=5.5.
const S=1624/11, PITCH=Math.sin(35*Math.PI/180), UP=Math.cos(35*Math.PI/180), HALF=Math.SQRT1_2, BOARD_SCALE=.9;
const loadImage=url=>new Promise((resolve,reject)=>{const image=new Image();image.onload=()=>resolve(image);image.onerror=()=>reject(new Error('图片加载失败：'+url));image.src=url;});
export const worldPoint=(x,y,z)=>({x:(x+z)*HALF*S*BOARD_SCALE,y:((x-z)*HALF*PITCH-y*UP)*S*BOARD_SCALE});
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
  constructor(canvas,data,ui,initialBase=1) {this.initialBase=initialBase;this.loadedMaps=new Set();this.mapLoads=new Map();this.canvas=canvas;this.ctx=canvas.getContext('2d',{alpha:false});this.data=data;this.ui=ui;this.camera={x:0,y:0};this.offset={x:375,y:812+(6*UP-10*PITCH)*S};this.zoom=5.5;this.position=0;this.spriteCache=new Map();this.images={};this.map=1;}
  async load() {
    const urls={atlas:'assets/scene/grid-atlas.png',goldcoin:'assets/scene/grid-atlas-goldcoin.png',shield:'assets/scene/shield.png',rent0:'assets/scene/avatar-3.png',rent1:'assets/scene/avatar-4.png',rent2:'assets/scene/avatar-6.png'};
    await Promise.all(Object.entries(urls).map(async([key,url])=>{this.images[key]=await loadImage(url);}));
    this.prefabs=await fetch('assets/scene/grid-prefabs.json').then(r=>r.json()).then(d=>d.prefabs);
    [this.layout,this.bgMesh,this.hooks]=await Promise.all(['maincity-layout.json','city-background-mesh.json','grid-hooks.json'].map(n=>fetch('assets/scene/'+n).then(r=>r.json())));
    await this.ensureMap(this.initialBase);
    await document.fonts.load('17px ShinBoardNumbers');
    this.meshes=await fetch('assets/scene/grid-meshes.json').then(r=>{if(!r.ok)throw new Error('格子模型加载失败');return r.json();});
    this.fund=await fetch('assets/scene/fund-prop.json').then(r=>r.json());for(const object of this.fund.objects)this.meshes[object.mesh.name]=object.mesh;for(const t of this.fund.textures)this.images[t.url]=await loadImage(t.url);
    const wanted=['icon_shield.png','icon_shield_01.png','icon_money.png','img_main_GachaMachine.png','img_event_shinchan_01.png'];
    for(const name of wanted){const url=this.ui.image(name);if(url){try{this.images[name]=await loadImage(url);}catch{}}}
    return this;
  }
  async ensureMap(base){if(this.loadedMaps.has(base))return;if(this.mapLoads.has(base))return this.mapLoads.get(base);const task=(async()=>{const t=this.layout.textures[String(base)];if(!t)throw new Error('未导入地图原资源：'+base);await Promise.all([...t.background,...t.foreground].map(async x=>{this.images[x.url]=await loadImage(x.url);}));this.loadedMaps.add(base);for(const old of [...this.loadedMaps])if(old!==base){const oldTextures=this.layout.textures[String(old)];for(const x of [...oldTextures.background,...oldTextures.foreground])delete this.images[x.url];this.loadedMaps.delete(old);}})();this.mapLoads.set(base,task);try{await task;}finally{this.mapLoads.delete(base);}}
  makeMeshRenderer() {
    const canvas=document.createElement('canvas'),gl=canvas.getContext('webgl',{alpha:true,antialias:true,preserveDrawingBuffer:true});
    if(!gl)throw new Error('浏览器不支持WebGL');
    const shader=(type,source)=>{const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(s));return s;};
    const program=gl.createProgram();gl.attachShader(program,shader(gl.VERTEX_SHADER,`precision mediump float;attribute vec3 position;attribute vec2 uv;attribute vec4 color;attribute vec3 normal;attribute vec3 world;uniform float outline;uniform vec2 projectionScale;varying vec2 vUv;varying vec4 vColor;varying vec3 vNormal;varying vec3 vWorld;void main(){vUv=uv;vColor=color;vNormal=normal;vWorld=world;vec3 p=position;p.xy+=vec2(normal.x,normal.y*${UP}+normal.z*${PITCH})*projectionScale*outline;gl_Position=vec4(p,1.0);}`));gl.attachShader(program,shader(gl.FRAGMENT_SHADER,`precision mediump float;uniform sampler2D atlas;uniform float toon;uniform float outline;uniform vec3 cameraPosition;varying vec2 vUv;varying vec4 vColor;varying vec3 vNormal;varying vec3 vWorld;void main(){vec4 c=texture2D(atlas,vUv)*vColor;if(c.a<0.01)discard;if(outline>0.0){gl_FragColor=vec4(toon>1.5?vec3(.4056604):vec3(.3207547,.05900677,.05900677),1.0);return;}if(toon>1.5){float light=smoothstep(0.0,.1,dot(normalize(vNormal),normalize(vec3(-.2,1.0,.56))));c.rgb*=1.2*mix(vec3(.752),vec3(.97),light);}else if(toon>0.5){vec3 n=normalize(vNormal);vec3 viewDir=normalize(cameraPosition-vWorld);float light=smoothstep(0.0,.02,dot(n,vec3(4.58,8.59,-4.64)));c.rgb*=mix(vec3(.98113209,.79138488,.79138488),vec3(1.0),light);vec3 halfVector=normalize(viewDir+vec3(-.63,6.13,-5.17));c.rgb+=step(.46,smoothstep(.99,.999,dot(n,halfVector)))*vec3(1.0);c.rgb+=smoothstep(0.0,.02,dot(n,viewDir+vec3(.9,-2.31,4.5))*.5+.5)*vec3(.17,.09282,.09282);}gl_FragColor=c;}`));gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(program));
    const texture=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,texture);gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,true);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,this.images.atlas);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);gl.enable(gl.DEPTH_TEST);gl.depthFunc(gl.LEQUAL);gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);
    return {canvas,gl,program,texture,toon:gl.getUniformLocation(program,'toon'),outline:gl.getUniformLocation(program,'outline'),projectionScale:gl.getUniformLocation(program,'projectionScale'),cameraPosition:gl.getUniformLocation(program,'cameraPosition'),normal:gl.getAttribLocation(program,'normal'),world:gl.getAttribLocation(program,'world'),textures:new Map([['assets/scene/grid-atlas.png',texture]]),position:gl.getAttribLocation(program,'position'),uv:gl.getAttribLocation(program,'uv'),color:gl.getAttribLocation(program,'color'),vertices:gl.createBuffer(),indices:gl.createBuffer()};
  }
  tileSprite(name,rotation=0,matrix=null,textureUrl='assets/scene/grid-atlas.png',space='board') {
    const key=(space==='world'?this.camera.x:0)+':'+space+':'+this.zoom+':'+textureUrl+':'+name+':'+rotation+':'+(matrix?matrix.join(','):'');if(space!=='dice'&&this.spriteCache.has(key))return this.spriteCache.get(key);
    const mesh=this.meshes[name] || this.meshes.checkerboard_07_green;const angle=rotation*Math.PI/180,c=Math.cos(angle),s=Math.sin(angle);const points=[];
    for(let i=0;i<mesh.positions.length;i+=3){let [x,y,z]=mesh.positions.slice(i,i+3);if(matrix){const m=matrix;[x,y,z]=[m[0]*x+m[4]*y+m[8]*z+m[12],m[1]*x+m[5]*y+m[9]*z+m[13],m[2]*x+m[6]*y+m[10]*z+m[14]];}points.push(space!=='board'?{x:(x*c+z*s)*S,y:-(y*UP+(-x*s+z*c)*PITCH)*S}:worldPoint(x*c+z*s,y,-x*s+z*c));}
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
      let normal=mesh.normals?.slice(i*3,i*3+3) || [0,1,0];if(matrix){const m=matrix,[a,b,c]=normal;normal=[m[0]*a+m[4]*b+m[8]*c,m[1]*a+m[5]*b+m[9]*c,m[2]*a+m[6]*b+m[10]*c];}
      vertices.push((p.x-minX)/width*2-1,1-(p.y-minY)/height*2,(space!=='board'?(rz*UP-y*PITCH):((rz-rx)*HALF*UP-y*PITCH)*BOARD_SCALE)/10,mesh.uv[i*2],mesh.uv[i*2+1],...(mesh.colors?.slice(i*4,i*4+4) || [1,1,1,1]),...normal,x+(space==='world'?0:0),y+(space==='world'?.084:0),z+(space==='world'?2.1:0));
    }
    gl.bindBuffer(gl.ARRAY_BUFFER,render.vertices);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(vertices),gl.STATIC_DRAW);
    gl.enableVertexAttribArray(render.position);gl.vertexAttribPointer(render.position,3,gl.FLOAT,false,60,0);gl.enableVertexAttribArray(render.uv);gl.vertexAttribPointer(render.uv,2,gl.FLOAT,false,60,12);
    gl.enableVertexAttribArray(render.color);gl.vertexAttribPointer(render.color,4,gl.FLOAT,false,60,20);
    gl.enableVertexAttribArray(render.normal);gl.vertexAttribPointer(render.normal,3,gl.FLOAT,false,60,36);gl.enableVertexAttribArray(render.world);gl.vertexAttribPointer(render.world,3,gl.FLOAT,false,60,48);gl.uniform1f(render.toon,space==='world'?1:space==='dice'?2:0);gl.uniform1f(render.outline,0);gl.uniform3f(render.cameraPosition,-this.camera.x/S,6,-10);gl.uniform2f(render.projectionScale,2*S/width,2*S/height);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,render.indices);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,new Uint16Array(mesh.indices),gl.STATIC_DRAW);let texture=render.textures.get(textureUrl);if(!texture){texture=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,texture);gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,true);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,this.images[textureUrl] || this.images.goldcoin);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);render.textures.set(textureUrl,texture);}gl.bindTexture(gl.TEXTURE_2D,texture);if(space==='world'||space==='dice'){gl.uniform1f(render.outline,space==='dice'?.0005:.0012);gl.enable(gl.CULL_FACE);gl.frontFace(gl.CW);gl.cullFace(gl.FRONT);gl.drawElements(gl.TRIANGLES,mesh.indices.length,gl.UNSIGNED_SHORT,0);gl.disable(gl.CULL_FACE);gl.uniform1f(render.outline,0);}gl.drawElements(gl.TRIANGLES,mesh.indices.length,gl.UNSIGNED_SHORT,0);
    const error=gl.getError();if(error!==gl.NO_ERROR)throw new Error('棋盘网格绘制失败：'+error);
    ctx.drawImage(render.canvas,0,0,width,height);
    const result={canvas,x:minX,y:minY,width,height};if(space!=='dice')this.spriteCache.set(key,result);return result;
  }
  drawBackdrop(layer,map){const node=this.layout.nodes[layer==='foreground'?'BG_F_SubMesh':'BG_SubMesh'],m=node.matrixInMainCityRoot,mesh=this.bgMesh;const entries=this.layout.textures[String(map)][layer];for(let j=0;j<mesh.subMeshes.length;j++){const im=this.images[entries[j].url];const indices=mesh.subMeshes[j].indices;for(let i=0;i<indices.length;i+=3){const p=[],uv=[];for(const id of indices.slice(i,i+3)){const x=mesh.positions[id*3],y=mesh.positions[id*3+1],z=mesh.positions[id*3+2];p.push(this.project(m[0]*x+m[4]*y+m[8]*z+m[12],m[1]*x+m[5]*y+m[9]*z+m[13],m[2]*x+m[6]*y+m[10]*z+m[14]));uv.push({x:mesh.uv[id*2]*im.width,y:(1-mesh.uv[id*2+1])*im.height});}texturedTriangle(this.ctx,im,p,uv);}}}
  direction(index){const m=this.hooks.slots[String(index+1)].center.matrixInNormalPrefab;const yaw=Math.atan2(m[8],m[10])*180/Math.PI;return {back:yaw>-90&&yaw<=90,flip:yaw>0};}
  drawFundShadow(){if(!this.fund)return;const o=this.fund.objects[0],m=this.fund.runtimeMatrixInMainCityRoot,material=o.materials.find(x=>x.isShadow),off=material.colors._ShadowOffset,alpha=material.colors._ShadowColor.a,height=material.floats._ShadowHeight;const points=[];for(let i=0;i<o.mesh.positions.length;i+=3){const [x,y,z]=o.mesh.positions.slice(i,i+3);const wy=m[1]*x+m[5]*y+m[9]*z+m[13],wx=m[0]*x+m[4]*y+m[8]*z+m[12]+off.r*wy+off.b,wz=m[2]*x+m[6]*y+m[10]*z+m[14]+off.g*wy+off.a;points.push(this.project(wx,height,wz));}const x=Math.floor(Math.min(...points.map(p=>p.x)))-1,y=Math.floor(Math.min(...points.map(p=>p.y)))-1,w=Math.ceil(Math.max(...points.map(p=>p.x))-x)+1,h=Math.ceil(Math.max(...points.map(p=>p.y))-y)+1;const canvas=document.createElement('canvas');canvas.width=w*2;canvas.height=h*2;const ctx=canvas.getContext('2d');ctx.scale(2,2);ctx.fillStyle='black';for(let i=0;i<o.mesh.indices.length;i+=3){ctx.beginPath();o.mesh.indices.slice(i,i+3).forEach((id,n)=>{const p=points[id];n?ctx.lineTo(p.x-x,p.y-y):ctx.moveTo(p.x-x,p.y-y);});ctx.closePath();ctx.fill();}this.ctx.save();this.ctx.globalAlpha=alpha;this.ctx.drawImage(canvas,x,y,w,h);this.ctx.restore();}
  drawText(tile){const t=this.hooks.slots[String(tile.id)]?.text;if(!t?.settings || ![1,3,4,9].includes(tile.type))return;const m=t.matrixInNormalPrefab,p=this.project(m[12]*BOARD_SCALE,m[13]*BOARD_SCALE,m[14]*BOARD_SCALE),ctx=this.ctx;const size=t.settings.m_fontSize/10;ctx.save();ctx.translate(p.x,p.y);ctx.transform(m[0]*BOARD_SCALE*S,-(m[1]*UP+m[2]*PITCH)*BOARD_SCALE*S,-m[4]*BOARD_SCALE*S,(m[5]*UP+m[6]*PITCH)*BOARD_SCALE*S,0,0);ctx.font=`700 ${size}px ShinBoardNumbers`;ctx.textAlign='center';ctx.textBaseline='middle';ctx.lineWidth=.055;ctx.strokeStyle='#8d8d8d';ctx.fillStyle='#898689';const value=Math.round(tile.param*(this.data.maps[Math.min(this.state.map-1,2)]?.inflation || 20));const label=(tile.type===4?'-':'')+value;ctx.strokeText(label,0,0);ctx.fillText(label,0,0);ctx.restore();}
  meshFor(tile) {const names={1:'checkerboard_01',2:'checkerboard_06',3:'checkerboard_07_green',4:'checkerboard_07_1_red',5:'checkerboard_02',6:'checkerboard_03',7:'checkerboard_15',8:'checkerboard_04',9:'checkerboard_07_yellow'};return names[tile.type] || names[3];}
  worldPosition(index) {const p=this.data.positions[index];return worldPoint(p.x,0,p.z);}
  project(x,y,z){return {x:375+x*S+this.camera.x,y:812-((y-6)*UP+(z+10)*PITCH)*S+this.camera.y};}
  background(ctx,image,x,y,z){const p=this.project(x,y,z);const w=12.88*S,h=20.48*S;ctx.drawImage(image,p.x-w/2,p.y-h/2,w,h);}
  screenPosition(index,hook='base') {const h=this.hooks?.slots[String(index+1)]?.[hook]?.positionInNormalPrefab;if(h)return this.project(h.x*BOARD_SCALE,h.y*BOARD_SCALE,h.z*BOARD_SCALE);const p=this.worldPosition(index);return {x:p.x+this.offset.x+this.camera.x,y:p.y+this.offset.y+this.camera.y};}
  follow(index,immediate=false) {
    const p=this.worldPosition(index);const target=immediate?{x:0,y:0}:{x:Math.max(-300,Math.min(300,-p.x)),y:0};
    if(immediate){this.camera=target;return Promise.resolve();}
    const start={...this.camera};const time=performance.now();return new Promise(resolve=>{const tick=()=>{const t=Math.min(1,(performance.now()-time)/420);const k=1-Math.pow(1-t,3);this.camera={x:start.x+(target.x-start.x)*k,y:start.y+(target.y-start.y)*k};this.draw();if(t<1)requestAnimationFrame(tick);else resolve();};tick();});
  }
  draw(state=this.state) {
    if(state)this.state=state;if(!this.state||!this.images.atlas)return;const s=this.state,ctx=this.ctx;const base=this.data.maps[Math.min(s.map-1,2)].baseId;if(!this.loadedMaps.has(base)){this.ensureMap(base).then(()=>this.draw()).catch(console.error);return;}
    ctx.clearRect(0,0,750,1624);ctx.fillStyle='#5c9073';ctx.fillRect(0,0,750,1624);
    this.drawBackdrop('background',this.data.maps[Math.min(s.map-1,2)].baseId);
    const tiles=this.data.squares.map((tile,index)=>({tile,index,point:this.screenPosition(index)})).sort((a,b)=>a.point.y-b.point.y);
    for(const {tile,index,point:p} of tiles){const source=this.prefabs[String(tile.id)];let matrix=null;if(source?.modelMatrix){const a=source.instanceMatrix,b=source.modelMatrix;matrix=Array.from({length:16},(_,i)=>{const row=i%4,col=Math.floor(i/4);return a[row]*b[col*4]+a[row+4]*b[col*4+1]+a[row+8]*b[col*4+2]+a[row+12]*b[col*4+3];});matrix[12]-=source.instance.position.x;matrix[13]-=source.instance.position.y;matrix[14]-=source.instance.position.z;}const sprite=this.tileSprite(source&&this.meshes[source.meshName]?source.meshName:this.meshFor(tile),0,matrix,source?.texture);ctx.drawImage(sprite.canvas,p.x+sprite.x,p.y+sprite.y,sprite.width,sprite.height);
      this.drawText(tile);
    }
    if(this.fund){const m=this.fund.runtimeMatrixInMainCityRoot;const matrix=[...m];matrix[12]=matrix[13]=matrix[14]=0;const p=this.project(m[12],m[13],m[14]);this.drawFundShadow();for(const o of this.fund.objects){const sprite=this.tileSprite(o.mesh.name,0,matrix,o.materials.find(m=>!m.isShadow).texture.url,'world');ctx.drawImage(sprite.canvas,p.x+sprite.x,p.y+sprite.y,sprite.width,sprite.height);}}
    for(const pos of s.shields){const p=this.screenPosition(pos,'propRoot');const icon=this.images.shield;if(icon)ctx.drawImage(icon,p.x-25,p.y-78,50,58);else{ctx.save();ctx.fillStyle='#9dd5ee';ctx.strokeStyle='white';ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(p.x-21,p.y-77);ctx.lineTo(p.x+21,p.y-77);ctx.lineTo(p.x+18,p.y-48);ctx.lineTo(p.x,p.y-35);ctx.lineTo(p.x-18,p.y-48);ctx.closePath();ctx.fill();ctx.stroke();ctx.restore();}}
    for(const pos of s.rents){const p=this.screenPosition(pos,'propRoot');const pic=this.images['rent'+(pos%3)];if(pic){ctx.save();ctx.beginPath();ctx.arc(p.x,p.y-55,24,0,Math.PI*2);ctx.clip();ctx.drawImage(pic,p.x-30,p.y-90,60,70);ctx.restore();ctx.strokeStyle='#fff4ce';ctx.lineWidth=3;ctx.beginPath();ctx.arc(p.x,p.y-55,24,0,Math.PI*2);ctx.stroke();}}
    this.drawBackdrop('foreground',this.data.maps[Math.min(s.map-1,2)].baseId);
    const p=this.screenPosition(this.position,'center');ctx.save();ctx.fillStyle='#31502c44';ctx.beginPath();ctx.ellipse(p.x,p.y+4,35,10,0,0,Math.PI*2);ctx.fill();ctx.restore();
    if(this.pieceElement){this.pieceElement.style.left=p.x+'px';this.pieceElement.style.top=p.y+'px';}this.onDraw?.(this.camera);
  }
  setPiece(index,element) {this.pieceElement=element;this.position=index;const p=this.screenPosition(index,'center');element.style.left=p.x+'px';element.style.top=p.y+'px';}
  async move(path,element,onStep) {
    for(const index of path){const from=this.position;this.onDirection?.(index,from);const target=this.screenPosition(index,'center'),start=this.screenPosition(from,'center');const duration=150;const at=performance.now();
      await new Promise(resolve=>{const tick=()=>{const t=Math.min(1,(performance.now()-at)/duration);element.style.left=(start.x+(target.x-start.x)*t)+'px';element.style.top=(start.y+(target.y-start.y)*t-Math.sin(t*Math.PI)*16)+'px';if(t<1)requestAnimationFrame(tick);else resolve();};tick();});this.position=index;onStep?.(index);if(index%5===0){await this.follow(index);this.setPiece(index,element);} }
    await this.follow(this.position);this.setPiece(this.position,element);
  }
}