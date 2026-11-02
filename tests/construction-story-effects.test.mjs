import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import crypto from 'node:crypto';
import {loadConstructionStoryEffects,sourceMemoryMatrix,preflightConstructionStoryEffects} from '../src/construction-story-effects.mjs';
const meta=JSON.parse(fs.readFileSync(new URL('../assets/construction/story-effects.json',import.meta.url),'utf8'));
class Element{
 constructor(name,document){this.name=name;this.ownerDocument=document;this.style={filter:'',opacity:''};this.dataset={};this.children=[];this.parentElement=null;}
 append(child){child.remove();this.children.push(child);child.parentElement=this;}
 remove(){if(this.parentElement){this.parentElement.children=this.parentElement.children.filter(child=>child!==this);this.parentElement=null;}}
 replaceChildren(...children){for(const child of this.children.slice())child.remove();for(const child of children)this.append(child);}
 contains(child){return child===this||this.children.some(node=>node.contains(child));}
 querySelector(){return null;}
 get isConnected(){return this.name==='body'||!!this.parentElement?.isConnected;}
 set src(value){this._src=value;if(value)queueMicrotask(()=>this.onload?.());}
 get src(){return this._src;}
 animate(){return{finished:Promise.resolve(),cancel(){}};}
}
const fixture=async(options={})=>{const document={createElement:name=>new Element(name,document),createElementNS:(_,name)=>new Element(name,document)};document.body=new Element('body',document);const screen=new Element('screen',document),stage=new Element('stage',document),canvas=new Element('canvas',document);document.body.append(screen);screen.append(stage);screen.append(canvas);const data=structuredClone(meta);data.cgRules.openFadeSeconds=0;data.cgRules.openWaitSeconds=0;data.cgRules.closeFadeSeconds=0;data.cgRules.closeWaitSeconds=0;data.fx['1'].fxDuration=0;data.fx['1'].background={fadeIn:0,fadeOutDelay:0,fadeOut:0};if(options.fxAvailable!==undefined)data.fx['1'].available=options.fxAvailable;const effects=await loadConstructionStoryEffects({stage,scene:{canvas},npcs:options.npcs,data});return{effects,stage,screen,document};};

test('Memory矩阵等价于原GLES shader的灰度及原序列化染色，保留alpha',()=>{
 const memory=meta.memory;assert.deepEqual(memory.overlayColor,[.9607843160629272,.886274516582489,.7568627595901489,1]);assert.equal(memory.intensity,1);assert.equal(memory.desaturation,1);
 const matrix=sourceMemoryMatrix(memory),rgba=[.2,.4,.6,.7],grey=rgba.slice(0,3).reduce((sum,value,index)=>sum+value*memory.luminance[index],0);
 for(let row=0;row<3;row++)assert.ok(Math.abs(matrix.slice(row*5,row*5+4).reduce((sum,value,index)=>sum+value*rgba[index],matrix[row*5+4])-grey*memory.overlayColor[row])<1e-12);
 assert.deepEqual(matrix.slice(15),[0,0,0,1,0]);
});
test('首2章CG使用真实导出纹理尺寸与哈希，shader保留原程序及系数',()=>{
 for(const[id,width,height]of[['3',484,592],['4',588,804]]){const asset=meta.cg[id],bytes=fs.readFileSync(new URL('../assets/construction/'+asset.url,import.meta.url));assert.equal(bytes.readUInt32BE(16),width);assert.equal(bytes.readUInt32BE(20),height);assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'),asset.sha256);}
 const shader=fs.readFileSync(new URL('../assets/construction/'+meta.memory.shaderUrl,import.meta.url),'utf8');assert.match(shader,/0\.298999995, 0\.587000012, 0\.114/);assert.match(shader,/SV_Target0\.w = u_xlat16_0\.w/);assert.equal(meta.cgRules.openWaitSeconds,1);assert.equal(meta.fx['1'].fxDuration,.5);
});
test('Memory覆盖原合成场景共同父层，end恢复并可继续复用',async()=>{
 const{effects,screen,stage}=await fixture();await effects.before({id:65},[{type:1,params:1}]);assert.match(screen.style.filter,/mhx-source-memory/);assert.equal(stage.style.filter,'');assert.equal(effects.memoryEnabled,true);effects.end();assert.equal(screen.style.filter,'');await effects.before({id:115},[{type:1,params:1}]);assert.equal(effects.memoryEnabled,true);effects.dispose();assert.equal(screen.style.filter,'');
});
test('CG3开关与CG4切换均使用源图片，不创建替代素材',async()=>{
 const{effects,stage}=await fixture();await effects.before({id:31},[{type:13,params:'1,3'}]);assert.equal(effects.activeCG.cgPath,'9:story_img_1001021');assert.ok(stage.children.some(node=>node.dataset.originalCG==='9:story_img_1001021'));await effects.before({id:35},[{type:13,params:0}]);assert.equal(effects.activeCG,null);await effects.before({id:202},[{type:13,params:'1,4'}]);assert.equal(effects.activeCG.cgPath,'9:story_img_1002031');effects.dispose();
});
test('源Spine载入失败仍按原失败路径等待并记录warning，on不阻塞',async()=>{
 const{effects}=await fixture({fxAvailable:false});const started=effects.on({id:38},[{type:12,params:1}]);assert.deepEqual(started,{started:1});assert.equal(effects.warnings.length,1);await effects.before({id:38},[{type:12,params:1}]);assert.equal(effects.warnings.length,1);assert.equal(effects.errors.length,0);effects.dispose();
});
test('on后台错误可查，未知before效果仍明确拒绝',async()=>{
 const{effects}=await fixture();effects.on({id:1},[{type:13,params:'1,999'}]);await new Promise(setImmediate);assert.equal(effects.errors.length,1);await assert.rejects(effects.before({id:2},[{type:99,params:1}]),/尚未实现/);effects.dispose();
});
test('原遮罩可持有、释放与blackSwitch回调，end可取消等待',async()=>{
 const{effects,stage}=await fixture();await effects.showBlack(0);assert.ok(stage.children.some(node=>node.dataset.originalEffect==='Prefabs/Common/Black.prefab'));await effects.hideBlack(0);assert.equal(stage.children.length,0);let black=false;await effects.blackSwitch({fadeIn:0,hold:0,fadeOut:0,onBlack:()=>{black=true;}});assert.equal(black,true);assert.equal(stage.children.length,0);
 const waiting=effects.blackSwitch({fadeIn:0,hold:20,fadeOut:0});await Promise.resolve();effects.end();await assert.rejects(waiting,error=>error.name==='AbortError');assert.equal(stage.children.length,0);effects.dispose();
});
test('永久dispose后不可重启效果，普通end则不会破坏后续open',async()=>{
 const{effects}=await fixture();effects.end();await effects.before({id:76},[{type:1,params:0}]);effects.dispose();await assert.rejects(effects.before({id:65},[{type:1,params:1}]),error=>error.name==='AbortError');
});
test('未await的遮罩释放遇到关窗中断不产生未处理的Promise错误',async()=>{
 const{effects}=await fixture();await effects.showBlack(0);void effects.hideBlack(1);effects.end();await new Promise(setImmediate);assert.equal(effects.errors.length,0);effects.dispose();
});
test('同版CDN补齐全部实际CG，预检阻止缺图与缺动作边界',()=>{
 assert.equal(meta.catalog.version,'1.4.93.1');
 for(let id=3;id<=29;id++)assert.equal(meta.cg[String(id)].available,true);
 const plan={steps:[{type:1,rows:[{id:38,effectsBefore:[{type:13,params:'1,29'},{type:12,params:'1,1'}]}]}]};assert.equal(preflightConstructionStoryEffects(meta,plan).ok,true);
 const bad=structuredClone(meta);delete bad.fx['1'].profile;assert.equal(preflightConstructionStoryEffects(bad,plan).missing[0].kind,'spine-animation-bounds');bad.cg['29'].available=false;assert.equal(preflightConstructionStoryEffects(bad,plan).missing[0].kind,'CG');
});
test('原type3黑底叙述忽略所有行效果，预检不因未执行引用误挡',()=>{
 const plan={steps:[{type:1,rows:[{id:1,type:3,effectsBefore:[{type:99,params:'1'},{type:13,params:'1,999'}],effectsOn:[{type:12,params:999}]}]}]};assert.deepEqual(preflightConstructionStoryEffects(meta,plan),{ok:true,missing:[],warnings:[]});
 plan.steps[0].rows[0].type=1;assert.equal(preflightConstructionStoryEffects(meta,plan).ok,false);
});
test('slap重放真实hit骨骼、源UI坐标、非循环动画，播放后销毁',async()=>{
 const tracks=[],mounts=[];let disposed=0;
 const npcs={data:{roles:{}},mountPortrait(root,options){mounts.push({root,options});return{ready:Promise.resolve(),player:{animationState:{setAnimation:(...args)=>tracks.push(args)}},dispose(){disposed++;}};}};
 const{effects,stage}=await fixture({npcs});await effects.before({id:38},[{type:12,params:'1,1'}]);assert.equal(mounts.length,1);assert.equal(mounts[0].options.originalUnits,true);assert.deepEqual(tracks,[[0,'animation',false]]);const profile=npcs.data.roles._plot_fx_1;assert.equal(profile.binaryUrl,'../story-fx/hit.skel');assert.equal(profile.animations.animation.duration,0.30000001192092896);assert.equal(disposed,1);assert.equal(stage.children.length,0);effects.dispose();
});
test('slap资源载入中关闭会立即中断，后续加载完成不能复活特效',async()=>{
 let ready,disposed=0;const npcs={data:{roles:{}},mountPortrait(){return{ready:new Promise(resolve=>ready=resolve),dispose(){disposed++;}};}};
 const{effects,stage}=await fixture({npcs}),playing=effects.before({id:38},[{type:12,params:1}]);effects.end();await assert.rejects(playing,error=>error.name==='AbortError');ready();await new Promise(setImmediate);assert.ok(disposed>=1);assert.equal(stage.children.length,0);effects.dispose();
});
test('原施工音效立即开始且不阻塞剧情，永久销毁停止音频',async()=>{
 const previous=globalThis.Audio,instances=[];
 globalThis.Audio=class{constructor(url){this.url=url;instances.push(this);}addEventListener(){}play(){this.played=true;return new Promise(()=>{});}pause(){this.paused=true;}};
 try{const{effects}=await fixture();assert.deepEqual(effects.sound(21),{started:true,id:21});assert.equal(instances[0].played,true);assert.equal(instances[0].loop,false);assert.match(instances[0].url,/SfxDecoration.flac$/);effects.end();assert.equal(instances[0].paused,undefined);effects.dispose();assert.equal(instances[0].paused,true);}finally{globalThis.Audio=previous;}
});
test('关建设可停止BGM，下次打开仍能原曲重启',async()=>{
 const previous=globalThis.Audio,instances=[];
 globalThis.Audio=class{constructor(url){this.url=url;instances.push(this);}play(){return Promise.resolve();}pause(){this.paused=true;}};
 try{const{effects}=await fixture();effects.playBGM(1,{fadeIn:0});await new Promise(setImmediate);assert.equal(effects.currentBGM,1);assert.deepEqual(effects.stopBGM(),{stopped:true,id:1});assert.equal(instances[0].paused,true);assert.equal(effects.currentBGM,0);assert.deepEqual(effects.resetBGM(),{started:true,id:1});assert.equal(instances.length,2);effects.dispose();await new Promise(setImmediate);assert.equal(effects.errors.length,0);}finally{globalThis.Audio=previous;}
});
test('浏览器首次拦截音乐只记录warning，同曲下一次用户交互可重试',async()=>{
 const previous=globalThis.Audio,instances=[];
 globalThis.Audio=class{constructor(){instances.push(this);}play(){return instances.length===1?Promise.reject(Object.assign(Error('gesture required'),{name:'NotAllowedError'})):Promise.resolve();}pause(){this.paused=true;}};
 try{const{effects}=await fixture();effects.playBGM(1,{fadeIn:0});await new Promise(setImmediate);assert.equal(effects.currentBGM,0);assert.equal(effects.errors.length,0);assert.equal(effects.warnings[0].retryable,true);assert.equal(instances[0].paused,true);assert.deepEqual(effects.playBGM(1,{fadeIn:0}),{started:true,id:1});await new Promise(setImmediate);assert.equal(effects.currentBGM,1);assert.equal(instances.length,2);effects.dispose();}finally{globalThis.Audio=previous;}
});
