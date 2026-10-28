import {BoardGame,SAVE_KEY} from './engine.mjs';
import {OriginalUI} from './fgui.mjs';
import {OriginalDice} from './dice.mjs';
import {OriginalScene} from './scene.mjs';
const $=s=>document.querySelector(s);const ui=new OriginalUI();
let saved=null;try{saved=JSON.parse(localStorage.getItem(SAVE_KEY));}catch{}
const engine=new BoardGame(window.GAME_DATA,saved);const game=$('#game'),piece=$('#piece'),modal=$('#modal-layer');
let facing='f',buildingLayout,currentAnimation='';
let dice3d;
let mainView,scene,player,busy=false,auto=false,autoTimer=0,toastTimer=0,modalKind='',modalView=null,prisonBusy=false;
const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const format=n=>Math.round(n).toLocaleString('en-US');
const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function save(){try{localStorage.setItem(SAVE_KEY,JSON.stringify(engine.snapshot()));}catch{toast('当前浏览器无法保存进度');}}
function toast(text){$('#toast').textContent=text;$('#toast').classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('#toast').classList.remove('show'),2600);}
function scale(){const factor=Math.min(window.innerWidth/750,window.innerHeight/1624);game.style.transform=`scale(${factor})`;}
window.addEventListener('resize',scale);scale();
function activate(root,path,action,label){return ui.action(root,path,action,label);}
function setText(root,path,text){ui.text(root,path,text);}
function addButton(parent,label,action,top=1260){const b=document.createElement('button');b.className='modal-action';b.dataset.action=action;b.style.top=top+'px';b.textContent=label;b.style.backgroundImage=`url('${ui.image('btn_com_orange01.png')}')`;parent.append(b);return b;}
function closeButton(){const b=document.createElement('button');b.className='modal-close';b.textContent='×';b.setAttribute('aria-label','关闭');b.dataset.action='close';modal.append(b);return b;}
function showModal(name,options={},kind=name){autoTimer&&clearTimeout(autoTimer);modal.replaceChildren();modal.hidden=false;modalKind=kind;clearTimeout(toastTimer);$('#toast').classList.remove('show');modalView=ui.create(name,options);modalView.classList.add('modal-view');modal.append(modalView);for(const n of modalView.querySelectorAll('[data-name="com_RedDot"],[data-name="RedDot"]'))n.style.display='none';for(const n of modalView.querySelectorAll('[data-name="icon_player"]'))ui.setImage(n,'assets/scene/shin-avatar.png');setText(modalView,'com_topBar/topMoeny/title',format(engine.state.coins));setText(modalView,'com_topBar/topKbNormal/title',engine.state.level);setText(modalView,'com_topBar/topShield/title',engine.state.shield+'/'+engine.state.shieldCap);return modalView;}
function hideModal(){modal.hidden=true;modal.replaceChildren();modalView=null;modalKind='';update();scheduleAuto();}
function close(){if(engine.state.pending){toast('请完成当前事件');return;}hideModal();}
function replaceComponent(root,path,controllers){const old=ui.find(root,path);if(!old)return null;const next=ui.component(old.dataset.pkg,old.dataset.resource,{controllers});next.style.cssText=old.style.cssText;next.dataset.name=old.dataset.name;next.dataset.node=old.dataset.node;old.replaceWith(next);return next;}
function makeMain(){
 mainView=ui.create('MainWindow',{controllers:{ctrl_bottomType:'0',c1:'0',ctrl_gameType:'0'}});
 const allowed=new Set(['com_topBar','loader_bottom_02','loader_bottom','loader_bottom_03','btn_go','btn_bet','btn_build','progress_dice','btn_draw','btn_friend','text_build','text_dice_time','text_draw','text_friend','freeDiceRemainNum']);
 for(const child of mainView.fgContent.children)if(!allowed.has(child.dataset.name))child.style.display='none';
 replaceComponent(mainView,'btn_bet',{show_ctrl:'0'});
 replaceComponent(mainView,'com_topBar/topMoeny',{ctrl_bgType:'0'});
 for(const node of mainView.querySelectorAll('[data-name="com_RedDot"],[data-name="gacha"],[data-name="RedDot"]'))node.style.display='none';
 for(const node of ui.find(mainView,'btn_bet')?.querySelectorAll('[data-name="n146"]') || [])node.style.display='none';
 setText(mainView,'text_build','建造');setText(mainView,'text_draw','画册');setText(mainView,'text_friend','好友');
 activate(mainView,'btn_go','roll','投骰子，长按自动');activate(mainView,'btn_bet','bet','切换倍率');activate(mainView,'btn_build','build','打开建造');activate(mainView,'btn_draw','album','打开画册');activate(mainView,'btn_friend','report','棋盘报告');activate(mainView,'com_topBar/btn_moreInfo','menu','菜单');activate(mainView,'com_topBar/btn_head','menu','玩家信息');
 ui.setImage(ui.find(mainView,'com_topBar/btn_head/com_avaterMask/icon_player'),'assets/scene/shin-avatar.png');
 $('#main-ui').replaceChildren(mainView);
 const world=$('#world-ui');world.innerHTML='';
 const fund=document.createElement('button');fund.className='world-hit';fund.style.cssText='width:160px;height:140px';fund.dataset.action='fund';fund.setAttribute('aria-label','存钱罐');fund.innerHTML='<span class="world-caption" id="fund-caption"></span>';world.append(fund);
}
function update(){
 const s=engine.state;if(!mainView)return;
 setText(mainView,'com_topBar/topMoeny/title',format(s.coins));setText(mainView,'com_topBar/topKbNormal/title',s.level);setText(mainView,'com_topBar/topShield/title',s.shield+'/'+s.shieldCap);
 const shieldIcon=ui.find(mainView,'com_topBar/topShield/icon');if(shieldIcon)ui.setImage(shieldIcon,'assets/scene/shield-front.png');
 setText(mainView,'btn_bet/title','X'+s.bet);setText(mainView,'progress_dice/title',format(s.dice)+'/50');setText(mainView,'text_dice_time',s.freeRolls?'免费投点剩余 '+s.freeRolls+' 次':s.dice>=50?'骰子充足':'每小时恢复5骰子');
 const free=ui.find(mainView,'freeDiceRemainNum');if(free)free.style.display='none';
 const gacha=$('#gacha-caption');if(gacha)gacha.textContent=s.gacha>=engine.gachaCost?'可扭蛋':`${s.gacha}/${engine.gachaCost}`;
 const fund=$('#fund-caption');if(fund)fund.textContent=s.fund?format(s.fund):'存钱罐';
 const go=ui.find(mainView,'btn_go');if(go)go.setAttribute('aria-disabled',String(busy));
 scene?.draw(s);if(scene&&!busy)scene.setPiece(s.position,piece);save();
}
function play(animation){animation=animation.replace(/_[fb]$/, '_'+facing);if(player?.animationState&&animation!==currentAnimation){try{player.setAnimation(animation,true);currentAnimation=animation;}catch{}}}
async function diceAnimation(dice){if(modalKind!=='prison')return dice3d.play(dice);const fx=$('#dice-fx');fx.hidden=false;const images=fx.querySelectorAll('img');for(let k=0;k<9;k++){for(let i=0;i<2;i++)images[i].src=ui.image(`icon_prisondice_0${1+Math.floor(Math.random()*6)}.png`);fx.style.transform=`rotate(${(k%2?1:-1)*7}deg)`;await wait(60);}for(let i=0;i<2;i++)images[i].src=ui.image(`icon_prisondice_0${dice[i]}.png`);fx.style.transform='';await wait(420);fx.hidden=true;}
function floatReward(text){const el=document.createElement('div');el.className='float-reward';el.textContent=text;const p=scene.screenPosition(engine.state.position);el.style.left=p.x+'px';el.style.top=(p.y-160)+'px';$('#float-layer').append(el);setTimeout(()=>el.remove(),1600);}
function scheduleAuto(){if(!modal.hidden || engine.state.pending)return;clearTimeout(autoTimer);if(auto&&!busy&&modal.hidden&&!engine.state.pending)autoTimer=setTimeout(roll,900);}
async function roll(){
 if(busy)return;if(!modal.hidden){toast('请先完成当前操作');return;}
 const result=engine.roll();if(result.error){auto=false;toast(result.error);return;}busy=true;save();
 try{await diceAnimation(result.dice);play('run_f');await scene.move(result.path,piece,(index)=>{scene.draw(engine.state);});play('idle_f');update();if(result.gain)floatReward((result.gain>0?'+':'')+format(result.gain));
  if(engine.state.pending){await wait(220);showPending();}else if(result.event?.kind==='fund-add')toast('存钱罐 +'+format(result.event.value));
 }finally{busy=false;update();scheduleAuto();}
}
function showPending(){const p=engine.state.pending;if(!p){hideModal();return;}
 if(p.kind==='chance'){
  const ctrl=p.card.type===3?'5':p.card.type===4?'7':[5,6].includes(p.card.type)?'1':'0';const v=showModal('ChanceWindow',{controllers:{c1:ctrl}},'chance');
  const titles={1:'获得美金',2:'缴纳美金',3:'获得骰子',4:'免费投点',5:'前进！',6:'前进！'};
  setText(v,'title_01',p.card.title || titles[p.card.type]);if(p.card.type<=2)setText(v,'title_04',format(p.card.param*engine.inflation*p.bet));setText(v,'com_bet/title_04','X'+p.bet);ui.hide(v,'n20');setText(v,'title_num',p.card.type===4?p.card.param:p.card.param*p.bet);setText(v,'title_05',p.card.description || ([5,6].includes(p.card.type)?'前往最近的好友捣蛋格':p.card.type===4?'免费投点期间保持当前倍率':''));
  const card=ui.find(v,'icon_img');if(card)ui.setImage(card,'assets/scene/chance/'+(p.card.pic || 'img_card_03')+'_01.png');ui.setSkin(v,'loader_Card','ChessboardEvent_01','bg_card_01.png');ui.setSkin(v,'icon_bg','ChessboardEvent_01','bg_card_03.png');ui.setImage(ui.find(v,'icon_title'),'assets/scene/chance/title.png');ui.setImage(ui.find(v,'icon_res'),ui.image(p.card.type===3||p.card.type===4?'icon_dice.png':'icon_money.png'));addButton(modal,'继续','chance-confirm',1300);autoCollect('chance-confirm');
 }else if(p.kind==='shield'){
  const v=showModal('SheildWindow',{},'shield');ui.setImage(ui.find(v,'loader_sheild'),'assets/scene/shield.png');setText(v,'title_01','+'+p.awarded);if(p.returned){const text=document.createElement('div');text.className='event-result';text.textContent='返还 '+p.returned+' 骰子';modal.append(text);}addButton(modal,'收取','dismiss',1250);autoCollect('dismiss');
 }else if(p.kind==='rent'){
  const v=showModal('FriendRentWindow',{},'rent');setText(v,'com_monty/title','+'+format(p.value));const t=document.createElement('div');t.className='event-result';t.style.top='780px';t.textContent=engine.state.opponents[p.target].name+'的租金 +'+format(p.value);modal.append(t);addButton(modal,'收取','dismiss',1120);autoCollect('dismiss');
 }else if(p.kind==='prison')showPrison();else if(p.kind==='attack')showAttack();else if(p.kind==='blind')showBlind();
}
function autoCollect(action){if(auto){const current=modalKind;clearTimeout(autoTimer);autoTimer=setTimeout(()=>{if(modalKind===current)handleAction(action);},1800);}}
async function chanceConfirm(){if(busy)return;const result=engine.resolveChance();if(!result)return;save();if(result.kind==='move'){modal.hidden=true;modal.replaceChildren();modalKind='';busy=true;play('run_f');try{await scene.move(result.path,piece);play('idle_f');}finally{busy=false;update();}showPending();}else{hideModal();toast(result.free?'获得 '+result.free+' 次免费投点':result.dice?'骰子 +'+result.dice:'美金 '+(result.coins>=0?'+':'')+format(result.coins));}}
function showPrison(){const p=engine.state.pending;const v=showModal('PrisonWindow',{controllers:{c1:'0'}},'prison');setText(v,'title_01','剩余 '+(3-p.attempts)+' 次');setText(v,'title_02','掷出相同点数逃脱');setText(v,'title_08',p.bet);activate(v,'btn_go','prison-roll','尝试脱困');addButton(modal,'掷骰子 · '+(3-p.attempts)+'次','prison-roll',1280);}
async function prisonRoll(){if(prisonBusy)return;prisonBusy=true;const result=engine.prisonRoll();save();await diceAnimation(result.dice);prisonBusy=false;if(result.finished){hideModal();toast(result.success?'成功脱困，骰子 +'+result.awarded:'脱困失败，缴纳 '+format(result.fine)+' 美金');}else{showPrison();toast('点数不同，再试一次');}}
function mapBase(){return engine.mapConfig.baseId || 1;}
function buildingPositions(){return buildingLayout.bases[String(mapBase())].positions.map(([x,y])=>[x-225,y]);}
function buildingImage(index,level,small=false){return `assets/scene/buildings/icon_build_${small?'s_':''}${String(mapBase()).padStart(3,'0')}_${index+1}_${Math.max(1,level)}.png`;}
function placeBuilding(image,index,level){const [x,y]=buildingPositions()[index];const dims=buildingLayout.images[buildingImage(index,level).split('/').pop()] || [360,452];image.style.cssText=`position:absolute;left:${x-dims[0]/2}px;top:${y-dims[1]}px;width:${dims[0]}px;height:${dims[1]}px;max-width:none;max-height:none;object-fit:fill`;return image;}
function showAttack(){
 const p=engine.state.pending;const target=engine.state.opponents[p.target];const v=showModal('DestroyBuildingWindow',{},'attack');ui.hide(v,'com_buildings');ui.hide(v,'group_getMoney');ui.hide(v,'icon_shield');
 const bg=document.createElement('img');bg.className='build-scene';bg.src=`assets/scene/bg_build_${mapBase()}.png`;v.prepend(bg);setText(v,'text_top_name',target.name+'的棋盘');ui.setImage(ui.find(v,'btn_player_icon/com_avaterMask/icon_player'),['assets/scene/avatar-3.png','assets/scene/avatar-4.png','assets/scene/avatar-6.png'][p.target]);activate(v,'btn_switch','switch-target','更换对手');
 const box=document.createElement('div');box.className='attack-buildings';box.style.inset='0';
 for(let i=0;i<5;i++){const b=document.createElement('button');b.dataset.action='attack:'+i;b.style.left=(buildingPositions()[i][0]-75)+'px';b.style.top=(buildingPositions()[i][1]-130)+'px';b.disabled=target.buildings[i]<=0;b.setAttribute('aria-label','破坏建筑'+(i+1));b.innerHTML=`<img src="${buildingImage(i,Math.max(1,target.buildings[i]))}" alt="建筑${i+1}"><span>${target.buildings[i]>0?'点击捣蛋':'已破坏'}</span>`;box.append(b);}modal.append(box);const hint=document.createElement('div');hint.className='event-result';hint.style.top='1300px';hint.textContent='选择一个建筑捣蛋';modal.append(hint);
}
function showBlind(){
 const p=engine.state.pending;const v=showModal('BlindBoxWindow',{controllers:{c1:'0'}},'blind');setText(v,'text_name',engine.state.opponents[p.target].name+'的盲盒');setText(v,'text_desc','找到3个相同图案');ui.setImage(ui.find(v,'com_head/com_avaterMask/icon_player'),['assets/scene/avatar-3.png','assets/scene/avatar-4.png','assets/scene/avatar-6.png'][p.target]);for(const n of v.querySelectorAll('[data-name^="saoguang"],[data-name^="com_previewline_Fake"]'))n.style.display='none';setText(v,'comp_radio/title_04','X'+p.bet);for(let row=1;row<=3;row++){const line=ui.find(v,'com_previewline_'+row);if(!line)continue;const count=p.picks.filter(x=>x.symbol===3-row).length;[...line.querySelectorAll('[data-name="icon_figure"]')].forEach((figure,i)=>{ui.setImage(figure,ui.skin('BlindBox_01',`icon_BlindBox_figure0${row+1}_s.png`));figure.style.filter=i<count?'':'grayscale(1)';figure.style.opacity=i<count?'1':'.5';});for(const text of line.querySelectorAll('.fg-text'))text.textContent=format([15000,10000,5000][row-1]*p.bet);}
 ui.setSkin(v,'loader_backBg','BlindBox_01','bg_BlindBox_background02.png');for(let i=1;i<=3;i++)ui.setSkin(v,'loader_bg'+i,'BlindBox_01','bg_BlindBox_red0'+i+'.png');
 for(let i=1;i<=12;i++){
  const old=ui.find(v,'mc_box_'+i);if(!old)continue;const chosen=p.picks.find(x=>x.index===i-1);
  const body=ui.component(old.dataset.pkg,old.dataset.resource,{controllers:{ctrl_selected:chosen?'2':'0',ctrl_super:'0'}});body.style.cssText=old.style.cssText;body.dataset.name=old.dataset.name;body.dataset.action='blind:'+(i-1);body.style.pointerEvents='auto';body.setAttribute('role','button');body.setAttribute('aria-label','打开盲盒'+i);body.tabIndex=0;old.replaceWith(body);
  if(chosen){const figure=ui.find(body,'icon_figure');ui.setImage(figure,ui.skin('BlindBox_01',`icon_BlindBox_figure0${4-chosen.symbol}.png`));const number=document.createElement('div');number.className='world-caption';number.textContent=['小奖','中奖','大奖'][chosen.symbol];number.style.bottom='0';body.append(number);}
 }
}
function showBuild(){if(engine.state.pending){showPending();return;}auto=false;const v=showModal('BuildWindow',{},'build');ui.hide(v,'com_buildings');const bg=document.createElement('img');bg.src=`assets/scene/bg_build_${mapBase()}.png`;bg.className='build-scene';v.prepend(bg);const bottom=ui.find(v,'com_bottomPart');if(bottom){bottom.style.left='-20px';bottom.style.top='1148px';}
 for(let i=0;i<5;i++){const building=engine.state.buildings[i];if(building.level>0){const img=document.createElement('img');img.className='building-sprite';img.src=buildingImage(i,building.level);placeBuilding(img,i,building.level);v.append(img);}}
 setText(v,'com_bottomPart/text_mapName',engine.mapConfig.name || ('第 '+engine.state.map+' 张地图'));setText(v,'com_bottomPart/text_lv',engine.state.buildings.reduce((n,b)=>n+b.level,0)+'/'+engine.maxBuildLevel*5);setText(v,'com_topBar/topMoeny/title',format(engine.state.coins));setText(v,'com_topBar/topKbNormal/title',engine.state.level);
 const list=ui.find(v,'com_bottomPart/buildingList');if(list){list.replaceChildren();for(let i=0;i<5;i++){const b=engine.state.buildings[i];const card=document.createElement('button');card.className='building-choice';card.dataset.action='build:'+i;card.setAttribute('aria-label',(b.damaged?'修复':'升级')+'建筑'+(i+1));card.style.left=(i*146)+'px';card.style.top='0';const ref=ui.data.packages[ui.data.byName.Build].items;const id=Object.keys(ref).find(id=>ref[id].name==='Btn_BuildingItem.xml');if(id){const comp=ui.component(ui.data.byName.Build,id);for(const n of comp.querySelectorAll('.fg-text,.fg-richtext,.fg-loader'))n.style.display='none';card.append(comp);}const image=document.createElement('img');image.src=buildingImage(i,Math.max(1,b.level),true);card.append(image);const cost=document.createElement('span');cost.className='cost';cost.textContent=b.level>=engine.maxBuildLevel&&!b.damaged?'已满级':format(engine.buildingCost(i));card.append(cost);const lv=document.createElement('span');lv.className='level';lv.textContent='★'.repeat(b.level)+'☆'.repeat(Math.max(0,engine.maxBuildLevel-b.level));lv.style.fontSize='19px';card.append(lv);card.disabled=b.level>=engine.maxBuildLevel&&!b.damaged;list.append(card);}}
 activate(v,'btn_gacha','gacha','扭蛋');activate(v,'com_bottomPart/com_closure','close','返回棋盘');closeButton();if(engine.canUpgradeMap)addButton(modal,'前往下一地图','next-map',990);
}
function showGacha(){if(engine.state.pending)return;const v=showModal('GachaMachineWindow',{},'gacha');ui.hide(v,'icon_gachaMachine');for(const n of ['icon_ball','icon_ball2','icon_ball3','icon_ball4','icon_ball5'])ui.hide(v,n);const machine=document.createElement('img');machine.src='assets/scene/gacha.png';machine.style.cssText='position:absolute;left:120px;top:220px;width:510px;height:800px;object-fit:contain';v.append(machine);const label=document.createElement('div');label.className='event-result';label.style.top='1100px';label.textContent='扭蛋币 '+engine.state.gacha+' / '+engine.gachaCost;v.append(label);addButton(modal,'扭蛋','draw-gacha',1280);closeButton();}
function simplePanel(title,body,buttons=[]){modal.replaceChildren();modal.hidden=false;modalKind='panel';const box=document.createElement('div');box.className='simple-panel';const h=document.createElement('h1');h.textContent=title;box.append(h);const content=document.createElement('div');content.innerHTML=body;box.append(content);for(const [text,action] of buttons){const b=document.createElement('button');b.textContent=text;b.dataset.action=action;box.append(b);}modal.append(box);closeButton();}
function report(){if(engine.state.pending)return;simplePanel('棋盘报告',`<div class="report-scroll">${engine.state.report.length?engine.state.report.map(r=>`<div class="report-item">${escape(r.message)}</div>`).join(''):'<p>还没有棋盘事件</p>'}</div>`);}
async function handleAction(action){
 if(action==='roll'){if(auto){auto=false;clearTimeout(autoTimer);toast('已停止自动投点');return;}return roll();}
 if(action==='bet'){if(busy)return;engine.nextBet();update();return;}
 if(action==='close')return close();
 if(action==='build')return showBuild();if(action==='gacha')return showGacha();
 if(action==='chance-confirm')return chanceConfirm();if(action==='prison-roll')return prisonRoll();
 if(action==='dismiss'){engine.dismiss();hideModal();return;}
 if(action==='report')return report();
 if(action==='menu'){if(engine.state.pending)return;auto=false;simplePanel('蜡笔小新',`<p>第 ${engine.state.map} 张地图</p><p>金币 ${format(engine.state.coins)} · 骰子 ${format(engine.state.dice)}</p><p class="local-note">当前进度保存在此设备。好友对手为本地角色。</p>`,[['棋盘报告','report'],['重新开始','reset-confirm']]);return;}
 if(action==='album'){simplePanel('画册',`<p>已收集贴纸 ${engine.state.stickers || 0} 张</p><p>建造获得扭蛋币，扭蛋可获得贴纸奖励。</p>`);return;}
 if(action==='fund'){const result=engine.openFund();if(result.error)toast(result.error);else{update();floatReward('+'+format(result.coins));toast('领取存钱罐 '+format(result.coins)+' 美金');}return;}
 if(action==='draw-gacha'){const result=engine.drawGacha();if(result.error){toast(result.error);return;}showGacha();update();toast(result.coins?'美金 +'+format(result.coins):result.dice?'骰子 +'+result.dice:'获得 '+result.card+' 张贴纸');return;}
 if(action==='next-map'){if(!engine.canUpgradeMap)return;busy=true;try{const base=window.GAME_DATA.maps[Math.min(engine.state.map,2)].baseId;await scene.ensureMap(base);if(engine.upgradeMap()){dice3d.clear();hideModal();scene.follow(0,true);scene.setPiece(0,piece);toast('进入新地图，获得50骰子和10,000美金');}}catch(error){toast('地图加载失败，请重试');console.error(error);}finally{busy=false;update();}return;}
 if(action==='switch-target'){const p=engine.state.pending;engine.changeOpponent((p.target+1)%3);showAttack();save();return;}
 if(action.startsWith('build:')){const result=engine.build(Number(action.split(':')[1]));if(result?.error)toast(result.error);else{showBuild();update();toast(result.complete?'地图建筑已全部完成':'建筑升级至 '+result.level+' 级');}return;}
 if(action.startsWith('attack:')){const result=engine.attack(Number(action.split(':')[1]));if(result?.error){toast(result.error);return;}if(!result)return;save();hideModal();toast((result.blocked?'被护盾挡住':'捣蛋成功')+'，美金 +'+format(result.coins));return;}
 if(action.startsWith('blind:')){const result=engine.openBlind(Number(action.split(':')[1]));if(!result)return;save();if(result.finished){hideModal();toast('匹配成功，美金 +'+format(result.coins));}else showBlind();update();return;}
 if(action==='reset-confirm'){simplePanel('重新开始','<p>清除当前设备上的棋盘进度？</p>',[['确认重新开始','reset']]);return;}
 if(action==='reset'){dice3d.clear();engine.state=engine.fresh();await scene.ensureMap(1);auto=false;hideModal();scene.follow(0,true);update();toast('已重新开始');}
}
let pressTimer=0,longPressed=false;
game.addEventListener('pointerdown',event=>{const el=event.target.closest('[data-action="roll"]');if(!el||busy||!modal.hidden)return;longPressed=false;pressTimer=setTimeout(()=>{longPressed=true;auto=true;toast('自动投点已开启');roll();},550);});
game.addEventListener('pointerup',()=>clearTimeout(pressTimer));game.addEventListener('pointercancel',()=>clearTimeout(pressTimer));game.addEventListener('pointerleave',()=>clearTimeout(pressTimer));
game.addEventListener('click',event=>{const el=event.target.closest('[data-action]');if(!el)return;if(el.dataset.action==='roll'&&longPressed){longPressed=false;return;}if(busy && !['close'].includes(el.dataset.action))return;handleAction(el.dataset.action);});
game.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){const el=event.target.closest('[data-action]');if(el && el.tagName!=='BUTTON'){event.preventDefault();handleAction(el.dataset.action);}}});
async function init(){
 try{
  buildingLayout=await fetch('assets/scene/building-layout.json').then(r=>r.json());await document.fonts.load('24px ShinOriginal');makeMain();scene=new OriginalScene($('#board'),window.GAME_DATA,ui,engine.mapConfig.baseId);await scene.load();dice3d=new OriginalDice(scene,game);await dice3d.load();scene.onDraw=()=>{if(!dice3d.playing)dice3d.redraw();const f=$('#world-ui [data-action="fund"]');if(f){const p=scene.project(0,.084,2.1);f.style.left=p.x+'px';f.style.top=(p.y-45)+'px';}};scene.onDirection=(to)=>{const d=scene.direction(to);facing=d.back?'b':'f';$('#spine').style.transform=d.flip?'scaleX(-1)':'';play('run_'+facing);};scene.onDirection(engine.state.position);scene.position=engine.state.position;scene.follow(engine.state.position,true);scene.draw(engine.state);scene.setPiece(engine.state.position,piece);
  player=new spine.SpinePlayer('spine',{skeleton:'assets/spine/shin/1_body.skel',atlas:'assets/spine/shin/1_body.atlas',animation:'idle_'+facing,showControls:false,showLoading:false,interactive:false,alpha:true,backgroundColor:'#00000000',premultipliedAlpha:true,viewport:{x:-180,y:-60,width:360,height:450,padLeft:0,padRight:0,padTop:0,padBottom:0},error:(p,message)=>{console.error('原Spine加载失败',message);toast('角色动画加载失败，请刷新重试');}});
  piece.style.width=(360*.0024*1624/11)+'px';piece.style.height=(450*.0024*1624/11*Math.cos(35*Math.PI/180))+'px';
  update();$('#loading').hidden=true;if(engine.state.pending)showPending();
  window.__SHIN={engine,ui,scene,dice3d,get busy(){return busy;},get auto(){return auto;},showPending,showBuild,handleAction};
  setInterval(()=>{if(engine.restoreDice())update();},30000);
 }catch(error){console.error(error);$('#loading').innerHTML='<div>加载失败</div><span>请刷新重试</span>';}
}
init();