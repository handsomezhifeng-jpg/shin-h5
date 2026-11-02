import{Construction}from './construction.mjs';
import{NativeConstructionProgress,loadNativeConstructionData}from './construction-native-progress.mjs';
import{NativeConstructionPlot,loadNativeConstructionPlotStage,createNativeConstructionPlotPlan}from './construction-native-plot.mjs';
import{loadConstructionStoryUI}from './construction-story-ui.mjs';
import{loadConstructionNewLook}from './construction-newlook.mjs';
import{loadConstructionUnitFx}from './construction-unit-fx.mjs';
import{loadConstructionAmbient}from './construction-ambient.mjs';
import{loadConstructionUnitTimeline}from './construction-unit-timeline.mjs';
import{cancelConstructionUI,playConstructionUI}from './construction-ui-motion.mjs';
import{playConstructionUnlock}from './construction-unit-motion.mjs';
import{ConstructionCameraInput}from './construction-camera-input.mjs';

const vector=v=>Array.isArray(v)?v:String(v??'').split(',').map(Number);
const abort=()=>Object.assign(Error('建设已关闭'),{name:'AbortError'});

// The board owns the wallet and save. Quest order, staging, costs and rewards are
// the recovered MainQuest/Plot rules, persisted in their own additive save field.
export class NativeConstruction extends Construction{
 async load(){
  await super.load();
  await this.cameraInput.load();
  const[{loadConstructionTaskContent},{loadConstructionStoryEffects}]=await Promise.all([import('./construction-task-content.mjs'),import('./construction-story-effects.mjs')]);
  [this.nativeData,this.newlook,this.unitFx,this.content,this.effects]=await Promise.all([loadNativeConstructionData(),loadConstructionNewLook(),loadConstructionUnitFx(),loadConstructionTaskContent({data:this.data,ui:this.ui,npcs:this.npcs}),loadConstructionStoryEffects({stage:this.stage,scene:this.scene,npcs:this.npcs})]);
  this.story=await loadConstructionStoryUI({stage:this.stage,npcs:this.npcs,ui:this.ui,getItem:id=>this.content.getItem(id)});
  const{loadConstructionHomeUI}=await import('./construction-home-ui.mjs');this.home=await loadConstructionHomeUI({layer:this.layer,ui:this.ui,content:this.content});
  const{loadConstructionLongTapUI}=await import('./construction-longtap-ui.mjs');this.longTapUI=await loadConstructionLongTapUI({ui:this.ui});
  this.ambient=await loadConstructionAmbient();
  this.unitTimeline=await loadConstructionUnitTimeline();
  this.stageCache=new Map();return this;
 }
 open(parent){
  this.lifetime?.abort();this.lifetime=new AbortController();this.progress=new NativeConstructionProgress(this.engine,this.nativeData);this.lastError=null;this.loading=true;this.reviewChapter=undefined;this.reviewScroll=null;this.preview=null;this.plotOverrides={};this.panel='';this.busy=false;this.disposed=false;this.parent=parent;parent.append(this.screen);this.onChange();
  this.plot=new NativeConstructionPlot(this.progress,{
   loadStage:(id,options)=>this.loadStage(id,options),
   dialogue:async(rows,ctx)=>{try{await this.releasePlotBlack(.85,ctx);return await this.story.showDialogue(rows,{...ctx,hasCG:()=>!!this.effects.activeCG,onBefore:(r,e)=>this.effects.before(r,e,ctx),onOn:(r,e)=>this.effects.on(r,e,ctx)});}finally{this.effects.end();}},
   animation:(rows,ctx)=>this.animatePlot(rows,ctx),
   choice:(unlock,ctx)=>this.chooseUnit(unlock,ctx),
   unlock:(unlocks,ctx)=>this.unlockUnits(unlocks,ctx),
   chapterPopup:ctx=>this.story.showChapterPopup(ctx),effect:(step,ctx)=>this.effects.apply(step,ctx),pause:(seconds,ctx)=>this.delay(seconds*1000,ctx.signal),finish:(plan,ctx)=>this.finishPlotPresentation(plan,ctx),onChange:()=>{this.savePresentation();this.onChange();}
  });
  this.render();
  const session=this.lifetime;this.ready=this.prepareIdle().then(()=>{if(this.lifetime===session&&!session.signal.aborted&&!this.disposed){this.loading=false;void this.effects.resetBGM?.();if(this.progress.pending)void this.playPlot();}}).catch(e=>{if(this.lifetime===session)this.fail(e);});
 }
 async loadStage(id,options){if(!this.stageCache.has(id))this.stageCache.set(id,await loadNativeConstructionPlotStage(id,options));return this.stageCache.get(id);}
 savePresentation(){const pending=this.progress.pending;if(pending)pending.presentation={version:1,cursor:pending.cursor,camera:{x:this.scene.camera.x,y:this.scene.camera.y,orthographicSize:this.scene.camera.orthographicSize},plotOverrides:structuredClone(this.plotOverrides),npcs:this.npcs.captureScene?.()};}
 preflight(questId,stage){
  const plan=createNativeConstructionPlotPlan(this.progress,questId,stage),missing=[],warnings=[],checkRole=(id,action,portrait=false)=>{if(!(Number(id)>0))return;if(portrait&&!this.progress.data.avatars.some(a=>Number(a.id)===Number(id))){warnings.push({avatarId:Number(id),source:'Missing AvatarVo: original SetSpine/SetNameComp preserve the previous presentation without requesting an asset'});return;}const key=(portrait?'npc_':'q_npc_')+id,profile=this.npcs.data.roles[key];if(!profile)missing.push(key);else if(action&&profile.kind!=='static'&&profile.animations&&!profile.animations[action]&&!profile.animations[action+'_begin'])warnings.push({role:key,action,source:'MapGameUtils.PlaySpineAnim leaves the current animation unchanged when both names are absent'});};
  if(plan.standPoint){const p=plan.standPoint,actions=String(p.actionNames??p.actionIds).split(';');String(p.roleIds).split(';').forEach((id,i)=>checkRole(id,actions[i]));}
  if(!this.progress.data.avatars.some(a=>Number(a.id)===Number(plan.quest.avatar)))missing.push('AvatarVo:'+plan.quest.avatar);else checkRole(plan.quest.avatar,'normal',true);for(const step of plan.steps){if(step.type===1){let cg=false;for(const row of step.rows){if(Number(row.type)===3)continue;for(const e of row.effectsBefore||[])if(e.type===13)cg=Number(String(e.params).split(',')[0])===1;if(!cg)checkRole(row.characterId>=9901&&row.characterId<=9999?9901:row.characterId,row.faceId||'normal',true);for(const e of row.effectsOn||[])if(e.type===13)cg=Number(String(e.params).split(',')[0])===1;}}if(step.type===2)for(const row of step.rows)checkRole(row.roleId,row.roleActionName);if(step.type===7&&step.worldId!==1)missing.push('world_'+step.worldId);for(const u of step.unlocks||[]){const unit=this.scene.data.units[String(u.unitId)];if(!unit){missing.push(String(u.unitId));continue;}if(step.type===3){for(const style of[1,2,3]){const path=unit.prefabPath.replace(/_skin\d+/i,'_skin'+String(style).padStart(2,'0'));if(!(this.scene.hasPrefab?.(path)??this.scene.prefab(path)))missing.push(path);}}else if(Number(u.unlockActive)!==1){const skin=this.progress.resolveUnlockSkin(u),path=skin!==null?unit.prefabPath.replace(/_skin\d+/i,'_skin'+String(skin).padStart(2,'0')):unit.prefabPath;if(!(this.scene.hasPrefab?.(path)??this.scene.prefab(path)))missing.push(path);}}}
  const effects=this.effects.preflight?.(plan);if(effects){missing.push(...effects.missing);warnings.push(...effects.warnings);}return{ok:missing.length===0,missing:[...new Set(missing)],warnings,plan};
 }
 async prepareIdle(questId=this.progress.viewQuestId){
  const token=this.lifetime.signal,id=this.progress.plotStageId(questId);if(id<1)return;
  const data=await this.loadStage(id,{signal:token});if(token.aborted)return;
  this.scene.setOrthoSize(this.scene.data.cameraAPP?.orthographicSize||5.625);const quest=this.progress.quests.get(questId),stand=data.standPoints.find(s=>Number(s.id)===Number(quest?.plotId));
  if(stand){let pos=vector(stand.camPos);if(pos.length!==2||!pos.every(Number.isFinite)){const points=String(stand.positions).split(';').map(vector);pos=[0,1].map(i=>points.reduce((sum,p)=>sum+p[i],0)/points.length);}this.scene.setFocus(...pos);}
  if(!this.npcSceneMounted&&this.npcs.mountScene){await this.npcs.mountScene(this.screen,this.scene,{...this.stageSource(),questId});this.npcSceneMounted=true;}
  await this.npcs.updateScene?.({...this.stageSource(),questId},{signal:token});await this.npcs.showQuestRoles?.(questId,{signal:token,prepare:false});if(!this.ambientMounted){this.ambient.mountScene(this.scene);this.ambientMounted=true;}this.drawScene();await this.scene.readyImages();
 }
 stageSource(){const state=this.progress.sceneState({preview:this.preview});for(const id of Object.keys(this.scene.data.units))if(!(id in state.visible))state.visible[id]=true;return state;}
 sceneState(){const state=this.stageSource();for(const[id,change]of Object.entries(this.plotOverrides||{})){if(change.visible!==undefined){state.visible[id]=change.visible;if(!change.visible)state.prefabs[id]=false;else delete state.prefabs[id];}if(change.skin!==undefined)state.skins[id]=change.skin;}return state;}
 drawScene(){this.scene.draw(this.sceneState());}
 render({showMain=false}={}){
  if(this.taskView)cancelConstructionUI(this.taskView);this.taskView=null;this.drawScene();const homeVisible=!!this.home?.el.isConnected;this.layer.replaceChildren();this.stage.replaceChildren();
  if(this.busy&&!showMain)return;
  this.home.render(this.progress);if(!homeVisible)void this.home.playEntry();
  if(this.panel==='task')this.task();if(this.panel==='history')this.history();if(this.panel==='choose')this.choose();
 }
 task(_index,{reuse=false,phase='open'}={}){
  let v=this.taskView;if(v&&reuse)cancelConstructionUI(v,{finish:true});if(!reuse||!v?.el.isConnected){if(v)cancelConstructionUI(v);this.stage.replaceChildren();const backdrop=document.createElement('div');backdrop.className='construction-backdrop';backdrop.dataset.action='construction:back';this.stage.append(backdrop);v=this.view('TaskDailog');}
  this.taskView=v;const b=this.data.taskBindings,q=this.progress.currentQuest;v.show('UIEffectCapture',false);v.show('ReviewPanel',false);v.show('TaskPanel/Finish',!q||this.progress.allFinished);v.show('TaskPanel/Normal',!!q&&!this.progress.allFinished);v.show('BtnToTask',false);v.text(b.title,'主线任务');v.text(b.chapter,String(q?.chapte||''));v.text(b.description,q?.name_zh_CN??q?.name??'');v.action(b.close,'construction:back','关闭任务');v.action(b.review,'construction:history','主线回顾');
  const finished=!q||this.progress.allFinished;v.show('DaySlider',!finished);
  if(!finished){v.image(b.costButton,this.engine.state.coins>=this.progress.cost?'common_btn_green_2':'common_btn_grey_2');v.action(b.costButton,'construction:select','完成主线任务');this.taskContentReady=this.content.fill(v,q,{progress:this.progress}).catch(e=>this.fail(e));}
  else{const schedule=this.nativeData.schedule.find(row=>Number(row.cnUnlock??row.unlock)===this.progress.state.unlockChapterId);v.action('Finish/FontStyleButton','construction:back','好的');if(schedule)v.text('Finish/TextDesc2','预计下次更新时间为: '+String(schedule.Desc_zh_CN??schedule.Desc??''));this.taskContentReady=Promise.resolve();}
  this.animateTask(phase);return v;
 }
 history({phase}={}){
  if(!this.taskView?.el.isConnected)this.task(undefined,{phase:'TaskDailog_Task'});const v=this.taskView;cancelConstructionUI(v,{finish:true});
  const content=v.find('ReviewPanel/ScrollView/Viewport/Content'),viewport=v.find('ReviewPanel/ScrollView/Viewport');content.replaceChildren();content.classList.add('construction-native-history');Object.assign(content.style,{left:'0px',top:'0px',width:'796px',pointerEvents:'auto'});Object.assign(viewport.style,{overflowY:'auto',pointerEvents:'auto',touchAction:'pan-y'});
  this.reviewChapter??=Math.max(1,this.progress.chapter);let y=0;
  for(let chapter=1;chapter<=this.progress.state.unlockChapterId;chapter++){
   const cell=this.ui.create('ChapterCell',{width:796,height:166});cell.el.hidden=false;cell.el.style.top=y+'px';const locked=chapter>this.progress.chapter;cell.text('TxtName',locked?'???':'第'+chapter+'章');cell.show('ImgLock',locked);cell.action('ChapterCell',locked?'construction:locked-chapter':'construction:chapter:'+chapter,locked?'章节未解锁':'第'+chapter+'章');for(const path of ['ImgBg','ImgTexture','ImgArrow','TxtName'])cell.switch(path,this.reviewChapter===chapter?1:2);const label=cell.find('TxtName')?.textNode;if(label&&this.reviewChapter!==chapter)label.style.webkitTextStroke='0';content.append(cell.el);y+=166;
   if(chapter!==this.reviewChapter)continue;
   for(const q of this.nativeData.quests.filter(q=>Number(q.chapte)===chapter)){
    const item=this.ui.create('ItemCell',{width:796,height:154});item.el.hidden=false;item.el.style.top=y+'px';const unlocked=Number(q.id)<this.progress.questId&&!this.progress.pending;item.show('ImgLock',!unlocked);item.text('TxtName',unlocked?(q.name_zh_CN??q.name):'');item.text('TxtNum',unlocked?String(q.chapte)+'-'+String(q.sec):'???');item.action('ItemCell',unlocked?'construction:review:'+q.id:'construction:locked-quest',unlocked?'回顾'+q.name:'剧情未解锁');item.el.dataset.questId=q.id;content.append(item.el);y+=154;
   }
  }
  content.style.height=y+'px';v.action('BtnToTask','construction:task','返回主线任务');v.text('BtnToTask/Text','任务');v.text(this.data.taskBindings.title,'主线回顾');this.animateTask(phase||'TaskDailog_Review');if(this.reviewScroll!=null)viewport.scrollTop=this.reviewScroll;
 }
 async chooseUnit(unlock,ctx,{style=0,free=false}={}){
  await this.releasePlotBlack(.9,ctx);if(ctx.signal.aborted)throw abort();this.choiceSourceState=structuredClone(this.sceneState());this.choice=unlock;this.preview=style?{unitId:String(unlock.unitId),style}:null;this.choiceView=null;this.panel='choose';this.choiceIsFree=free;this.choose();
  this.choiceCamera=this.animateCamera({...unlock,camMoveTime:Number(unlock.camMoveDuration)/.6,camScaleTime:Number(unlock.camMoveDuration)/.6},ctx).catch(e=>{if(e.name!=='AbortError')this.fail(e);});
  this.choiceMotion=playConstructionUI(this.choiceView,this.data,'TransitionRestDecorSelectPopUp',{phase:'open'});
  return new Promise((resolve,reject)=>{const cancel=()=>{if(this.resolveChoice===complete)this.resolveChoice=null;reject(abort());};const complete=style=>{ctx.signal.removeEventListener('abort',cancel);this.resolveChoice=null;resolve(style);};this.resolveChoice=complete;ctx.signal.addEventListener('abort',cancel,{once:true});});
 }
 choose(){
  let v=this.choiceView;if(!v?.el.isConnected){this.stage.replaceChildren();v=this.view('TransitionRestDecorSelectPopUp');this.choiceView=v;}v.text('TxtTitle','选择装修');v.action('FontStyleButton','construction:confirm','确认装修');for(let skin=1;skin<=3;skin++){v.action('BtnType'+skin,'construction:skin:'+skin,'装修样式'+skin);v.show('BtnType'+skin+'/ImgSelect',this.preview?.style===skin);}v.show('FontStyleButton',!!this.preview);this.drawScene();
  if(!this.choiceGlow){const start=performance.now(),tick=now=>{this.choiceGlow=0;if(this.disposed||this.panel!=='choose')return;if(this.preview){const t=((now-start)/1000)%1.6,value=t<1?.9+.3*t:1.2-.3*(t-1)/.6;this.scene.draw({...this.scene.state,brightness:{[this.preview.unitId]:value}});}this.choiceGlow=requestAnimationFrame(tick);};this.choiceGlow=requestAnimationFrame(tick);}
 }
 async unlockUnits(unlocks,ctx){
  await this.releasePlotBlack(.9,ctx);
  const session=this.lifetime;this.setWorldTimeScale(5/3);
  try{return await this.performUnitUnlock(unlocks,ctx);}finally{if(this.lifetime===session)this.setWorldTimeScale(1);}
 }
 worldTime(){this.worldClock??={offset:0,anchor:performance.now(),scale:1};const c=this.worldClock;return c.offset+(performance.now()-c.anchor)/1000*c.scale;}
 setWorldTimeScale(scale){const time=this.worldTime();this.worldClock={offset:time,anchor:performance.now(),scale};this.ambient.setTimeScale(scale);this.npcs.setSceneTimeScale(this.npcs.storyMode?1:scale);}
 async performUnitUnlock(unlocks,ctx){
  this.panel='';this.stage.replaceChildren();this.preview=null;
  if(ctx.fromChoice){const old=this.choiceSourceState||this.sceneState(),saved=this.progress.pending?.choice,id=String(unlocks[0].unitId);if(!this.choiceSourceState){if(saved?.previousStyle)old.skins[id]=saved.previousStyle;else delete old.skins[id];}this.scene.draw(old);this.choiceSourceState=null;}
  const types=u=>String(u.unlockFxTypes??u.unlockFxType).split(';').map(Number),withHammer=unlocks.filter(u=>types(u).some(t=>t===3||t===7));
  const preloaded=Promise.all(unlocks.filter(u=>Number(u.unlockActive)!==1).map(u=>this.scene.preloadUnit(String(u.unitId),this.progress.resolveUnlockSkin(u),{signal:ctx.signal})));preloaded.catch(()=>{});
  const camPos=unlocks.find(u=>u.camPos)?.camPos||'',camScale=Number(unlocks.find(u=>Number(u.camScale))?.camScale)||0,camMoveDuration=Number(unlocks.find(u=>Number(u.camMoveDuration))?.camMoveDuration)||0;if(camPos||camScale)await this.animateCamera({camPos,camScale,camMoveTime:camMoveDuration/.6/(5/3),camScaleTime:camMoveDuration/.6/(5/3)},ctx);
  const check=()=>{if(ctx.signal.aborted)throw abort();};await this.scene.readyImages();check();
  if(withHammer.length){const u=withHammer[0],kind=types(u).filter(t=>t===3||t===7).at(-1),bounds=this.sourceUnitBounds(u.unitId),[x,y]=this.scene.project(bounds.center.x,bounds.center.y);void this.effects.sound?.(21);if(kind===3)await this.hammer.play(this.screen,{x,y,pixelsPerUnit:this.scene.camera.scale,timeScale:5/3});else await this.unitFx.play(7,this.screen,{x,y,pixelsPerUnit:this.scene.camera.scale,timeScale:5/3,signal:ctx.signal});check();}
  for(const u of unlocks.filter(u=>Number(u.unlockActive)===1)){const kind=types(u).find(t=>t!==3&&t!==7)||0;if(![2,4,5,6].includes(kind))continue;void this.effects.sound?.(this.unitFx.source[kind].soundId);for(const target of this.scene.unitEmissionTargets(u.unitId)){const[x,y]=this.scene.project(target.x,target.y);this.unitFx.play(kind,this.screen,{x,y,pixelsPerUnit:this.scene.camera.scale,timeScale:5/3,signal:ctx.signal,clock:()=>this.worldTime(),project:()=>{const[x,y]=this.scene.project(target.x,target.y);return{x,y,pixelsPerUnit:this.scene.camera.scale};}}).catch(e=>this.fail(e));}}
  await playConstructionUnlock(this.scene,unlocks.filter(u=>Number(u.unlockActive)===1),{signal:ctx.signal,disappear:true});check();
  await preloaded;check();
  for(const u of unlocks){const id=String(u.unitId),change={visible:Number(u.unlockActive)!==1},skin=this.progress.resolveUnlockSkin(u);if(skin!==null)change.skin=skin;this.plotOverrides[id]=change;}
  this.drawScene();await this.scene.readyImages();
  const shown=unlocks.filter(u=>Number(u.unlockActive)!==1);await Promise.all([playConstructionUnlock(this.scene,shown,{signal:ctx.signal}),...shown.map(u=>this.unitTimeline.play(this.scene,String(u.unitId),{signal:ctx.signal,timeScale:5/3}))]);check();
  if(withHammer.length){void this.effects.sound?.(22);await this.newlook.play(this.screen,{x:375,y:812,pixelsPerUnit:this.scene.camera.scale,timeScale:5/3});check();}
  else{const stars=unlocks.filter(u=>Number(u.unlockActive)!==1&&(types(u).find(t=>t!==3&&t!==7)||0)===1);if(stars.length){void this.effects.sound?.(22);const work=[];for(const u of stars)for(const target of this.scene.unitEmissionTargets(u.unitId)){if(!target.tilemap&&!target.emissionMesh)continue;const[x,y]=this.scene.project(target.x,target.y);work.push(this.unitFx.play(1,this.screen,{x,y,pixelsPerUnit:this.scene.camera.scale,timeScale:5/3,unitBounds:this.sourceUnitBounds(u.unitId),sceneUnit:target,signal:ctx.signal}));}await Promise.all([this.delay(2000/(5/3),ctx.signal),...work]);check();}}
 }
 sourceUnitBounds(unitId){const row=this.nativeData.unitBounds.find(b=>String(b.id)===String(unitId));if(!row)throw Error('缺少原建筑边界 '+unitId);const[x,y,width,height]=String(row.bounds).split(';').map(Number);return{min:{x,y},max:{x:x+width,y:y+height},size:{x:width,y:height},center:{x:x+width/2,y:y+height/2},source:'UnitBoundsVo:'+unitId};}
 async decorate(unitId){
  unitId=String(unitId);if(this.loading||this.busy||this.progress.pending||!this.progress.threeChoice.has(unitId))return false;const unlock=this.progress.selectedUnlock(unitId);if(!this.progress.unlocked(unlock)||!this.sceneState().visible[unitId])return false;
  const session=this.lifetime;this.busy=true;this.panel='';this.render();
  try{while(unitId){this.nextDecorUnit=null;const selected=this.progress.selectedUnlock(unitId),style=await this.chooseUnit(selected,{signal:session.signal},{style:this.progress.recordSkin(unitId),free:true});if(session.signal.aborted)throw abort();const result=this.progress.confirmSkin(unitId,style);if(!result.ok)throw Error(result.error);this.onChange();unitId=this.nextDecorUnit;}return true;}
  catch(error){if(error.name!=='AbortError')this.fail(error);return false;}
  finally{if(this.lifetime===session&&!this.disposed){this.preview=null;this.choice=null;this.panel='';this.busy=false;this.choiceIsFree=false;this.render();}}
 }
 async switchFreeDecor(unitId){
  unitId=String(unitId);if(!this.choiceIsFree||this.confirming||!this.resolveChoice||unitId===String(this.choice?.unitId)||!this.progress.threeChoice.has(unitId)||!this.progress.unlocked(this.progress.selectedUnlock(unitId)))return false;
  this.nextDecorUnit=unitId;await this.action('construction:confirm');return true;
 }
 hitDecorUnit(x,y){
  const[wx,wy]=this.scene.world(x,y);this.hitContext??=document.createElement('canvas').getContext('2d',{willReadFrequently:true});const ctx=this.hitContext;ctx.canvas.width=ctx.canvas.height=1;
  for(let i=this.scene.instances.length-1;i>=0;i--){const item=this.scene.instances[i],id=String(item.unit);if(!this.progress.threeChoice.has(id)||!this.progress.unlocked(this.progress.selectedUnlock(id)))continue;const box=item.bounds;if(!box||wx<box[0]||wx>box[2]||wy<box[1]||wy>box[3])continue;const[a,b,c,d,tx,ty]=item.matrix,det=a*d-b*c;if(!det)continue;let lx=(d*(wx-tx)-c*(wy-ty))/det,ly=(-b*(wx-tx)+a*(wy-ty))/det;if(item.flipX)lx=-lx;if(item.flipY)ly=-ly;const sp=this.scene.data.sprites[item.sprite],im=this.scene.images.get(sp?.url);if(!im)continue;const[bx,by,bw,bh]=sp.bounds,u=(lx-bx)/bw,v=1-(ly-by)/bh;if(u<0||v<0||u>=1||v>=1)continue;ctx.clearRect(0,0,1,1);ctx.drawImage(im,Math.floor(u*im.width),Math.floor(v*im.height),1,1,0,0,1,1);if(ctx.getImageData(0,0,1,1).data[3]>0)return id;
  }return null;
 }
 bindPan(){
  this.cameraInput=new ConstructionCameraInput(this);this.cameraInput.bind();
 }
 async animatePlot(rows,ctx){
  if(!this.npcs.playAnimationRows)throw Error('原场景人物动画尚未就绪');const options={...ctx,timeScale:1,onCamera:r=>{void this.animateCamera(r,ctx).catch(e=>{if(e.name!=='AbortError')this.fail(e);});},onBlack:o=>{this.effects.blackSwitch?.(o).catch(e=>{if(e.name!=='AbortError')this.fail(e);});}};
  if(ctx.skip){const black=rows.find(r=>Number(r.blackSwitch)===1);if(black){await this.npcs.playAnimationRows([{...black,order:1,delay:0}],options);await this.delay(500,ctx.signal);}return;}
  if(this.plotBlack){const prepared=await this.npcs.prepareAnimationRows(rows,options),stand=this.plot.plan?.standPoint;if(!prepared.hasPrepareCameraEvent&&stand){const pos=vector(stand.camPos);if(pos.length===2)this.scene.setFocus(...pos);if(Number(stand.camScale)>0)this.scene.setOrthoSize(Number(stand.camScale));}await this.delay(100,ctx.signal);await this.releasePlotBlack(.7,ctx);}
  await this.npcs.playAnimationRows(rows,options);
 }
 async releasePlotBlack(waitSeconds,ctx){if(!this.plotBlack)return;this.plotBlack=false;this.effects.hideBlack?.(.8,ctx).catch(e=>{if(e.name!=='AbortError')this.fail(e);});await this.delay(waitSeconds*1000,ctx.signal);}
 async animateCamera(r,{signal}){
  if(signal.aborted)throw abort();const p=vector(r.camPos),hasPos=p.length===2&&p.every(Number.isFinite),size=Number(r.camScale),moveTime=Number(r.camMoveTime)*.6,scaleTime=Number(r.camScaleTime)*.6,duration=Math.max(moveTime,scaleTime,0),from={...this.scene.camera},start=performance.now();if(!hasPos&&!(size>0))return;
  await new Promise((resolve,reject)=>{let raf;const cancel=()=>{cancelAnimationFrame(raf);reject(abort());};signal.addEventListener('abort',cancel,{once:true});const frame=now=>{if(signal.aborted)return cancel();const t=(now-start)/1000,ease=v=>v*(2-v),move=ease(moveTime>0?Math.min(1,t/moveTime):1),scale=ease(scaleTime>0?Math.min(1,t/scaleTime):1);this.scene.setCamera({x:hasPos?from.x+(p[0]-from.x)*move:this.scene.camera.x,y:hasPos?from.y+(p[1]-from.y)*move:this.scene.camera.y,orthographicSize:size>0?from.orthographicSize+(size-from.orthographicSize)*scale:this.scene.camera.orthographicSize});if(t<duration)raf=requestAnimationFrame(frame);else{signal.removeEventListener('abort',cancel);resolve();}};raf=requestAnimationFrame(frame);});
 }
 async finishPlotPresentation(_plan,ctx){
  if(!this.plotBlack){await this.effects.showBlack(.4,{signal:ctx.signal});await this.delay(100,ctx.signal);}this.plotBlack=true;
  await this.prepareIdle(this.progress.questId);await this.delay(100,ctx.signal);this.effects.hideBlack(.8,{signal:ctx.signal}).catch(e=>{if(e.name!=='AbortError')this.fail(e);});this.effects.resetBGM();await this.delay(700,ctx.signal);this.plotBlack=false;
 }
 delay(ms,signal){return new Promise((resolve,reject)=>{if(signal?.aborted){reject(abort());return;}const finish=()=>{signal?.removeEventListener('abort',cancel);resolve();},timer=setTimeout(finish,Math.max(0,ms)),cancel=()=>{clearTimeout(timer);reject(abort());};signal?.addEventListener('abort',cancel,{once:true});});}
 async playPlot(reviewQuestId){
  if(this.plot.running||this.busy)return;const session=this.lifetime,plot=this.plot;this.busy=true;this.panel='';this.render();
  try{const signal=session.signal,pending=this.progress.pending;if(reviewQuestId==null&&pending?.levelUp&&!pending.levelUpShown&&this.story.showLevelUp){await this.story.showLevelUp(pending.levelUp,{signal});if(signal.aborted)throw abort();pending.levelUpShown=true;this.onChange();}this.plotBlack=true;await this.effects.showBlack?.(.4,{signal});await this.npcs.showQuestRoles?.(reviewQuestId??pending?.completedQuestId,{signal,prepare:true});if(reviewQuestId==null&&pending?.presentation){const saved=pending.presentation;this.plotOverrides=structuredClone(saved.plotOverrides||{});if(saved.camera)this.scene.setCamera(saved.camera);if(saved.npcs)await this.npcs.restoreScene(saved.npcs,{signal});this.drawScene();}const result=await plot.play(reviewQuestId==null?{}:{reviewQuestId});if(result.ok&&!this.disposed&&this.lifetime===session){this.plotOverrides={};this.drawScene();this.panel='';this.render({showMain:true});if(reviewQuestId==null&&this.story.showGoodsFly){void this.effects.sound?.(20);await this.story.showGoodsFly({exp:this.submitted?.exp||15,rewards:this.submitted?.rewards||[],sourceApp:true,signal});}if(signal.aborted)throw abort();this.submitted=null;this.busy=false;this.panel=reviewQuestId!=null?'history':this.progress.allFinished?'task':'';this.render();}}
  catch(error){if(this.lifetime===session)this.fail(error);}finally{if(!this.disposed&&this.lifetime===session)this.busy=false;}
 }
 fail(error){if(error?.name==='AbortError'||this.disposed)return;console.error(error);this.lastError=error;this.busy=false;this.panel='';this.render();this.toast('原剧情未能继续，已保存当前进度');}
 async action(action){
  if(!action.startsWith('construction:'))return false;const[,kind,value]=action.split(':');if(this.loading&&!['close','gacha'].includes(kind)){const session=this.lifetime;await this.ready;if(this.lifetime!==session||session.signal.aborted||this.disposed)return true;if(this.loading){this.toast('场景加载未完成，请重新进入庭院');return true;}}
  if(this.busy&&!['close','skin','confirm'].includes(kind))return true;if(!['close','gacha'].includes(kind)&&!this.effects.currentBGM)void this.effects.resetBGM();
  switch(kind){
   case'close':this.dispose();this.onClose();break;
   case'gacha':this.dispose();this.onGacha();break;
   case'level-info':if(this.story.showLevelInfo)await this.story.showLevelInfo(this.progress,{signal:this.lifetime.signal});break;
   case'task':{if(this.progress.pending){await this.playPlot();break;}const review=this.panel==='history';this.panel='task';this.task(undefined,{reuse:!!this.taskView,phase:review?'TaskDailog_ReviewToTask':'open'});break;}
   case'back':if(!await this.leaveTask())break;this.reviewChapter=undefined;this.reviewScroll=null;this.panel='';this.render();break;
   case'history':this.panel='history';this.history({phase:'TaskDailog_TaskToReview'});break;
   case'locked-chapter':this.toast('章节未解锁');break;
   case'locked-quest':this.toast('剧情未解锁');break;
   case'chapter':this.reviewChapter=this.reviewChapter===Number(value)?0:Number(value);this.reviewScroll=null;this.history();break;
   case'review':if(this.progress.isCompleted(value)&&!this.progress.pending){this.reviewScroll=this.taskView?.find('ReviewPanel/ScrollView/Viewport')?.scrollTop||0;if(!await this.leaveTask())break;await this.playPlot(Number(value));}break;
   case'select':{
    if(this.progress.pending){await this.playPlot();break;}if(this.engine.state.coins<this.progress.cost){this.toast('铜钱不足');break;}const id=this.progress.questId;
    // Check that the supplied package actually contains this plot before charging.
    const stageId=this.progress.plotStageId(id);if(stageId<1){this.toast('包内尚无这项任务的剧情');break;}const stage=await this.loadStage(stageId);if(!stage.plot.some(r=>Number(r.groupId)===Number(this.progress.currentQuest.plotId))){this.toast('包内尚无这项任务的剧情');break;}this.availability=this.preflight(id,stage);if(!this.availability.ok){this.toast('当前包缺少这项任务的素材');return true;}
    if(!await this.leaveTask())break;const result=this.progress.submit(id);if(!result.ok){this.toast(result.error);break;}this.submitted=result;this.onChange();await this.playPlot();break;
   }
   case'decorate':await this.decorate(value);break;
   case'skin':if(this.choice&&!this.confirming&&[1,2,3].includes(Number(value))){this.preview={unitId:String(this.choice.unitId),style:Number(value)};this.choose();}break;
   case'confirm':if(this.preview&&this.resolveChoice&&!this.confirming){this.confirming=true;try{const style=this.preview.style,view=this.choiceView;await playConstructionUI(view,this.data,'TransitionRestDecorSelectPopUp',{phase:'close'});if(!this.disposed&&this.resolveChoice){this.stage.replaceChildren();this.resolveChoice(style);}}finally{this.confirming=false;}}break;
  }
  return true;
 }
 dispose(){if(this.ambientMounted)this.setWorldTimeScale(1);this.disposed=true;this.cameraInput?.reset();clearTimeout(this.longTapTimer);this.longTapUI?.dispose();cancelAnimationFrame(this.choiceGlow);this.choiceGlow=0;this.lifetime?.abort();this.plot?.dispose();this.story?.dispose();this.effects?.end();this.effects?.stopBGM();this.home?.dispose();this.newlook?.dispose();this.unitFx?.cancel();this.unitTimeline?.cancel();this.ambient?.detach();this.ambientMounted=false;this.resolveChoice=null;this.npcSceneMounted=false;super.dispose();}
}
