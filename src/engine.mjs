import NativeRules from './native-rules.mjs';
export const SAVE_KEY = 'shin-board-h5-v1';
const clone = value => JSON.parse(JSON.stringify(value));
const TYPES = ['','起点','存钱罐','金币','缴费','停车场','机会','陷阱','好友捣蛋','公共事业'];
export class BoardGame {
  constructor(data, saved = null, options = {}) {
    this.rules=options.rules || NativeRules; this.data = data; this.random = options.random || Math.random; this.clock = options.clock || Date.now;
    this.state = this.restore(saved) || this.fresh();
    this.state.nativeRulesVersion=1;this.state.shieldCap=this.attribute(20000);if(!this.state.freeRolls){const valid=this.availableBets();if(!valid.includes(this.state.bet))this.state.bet=valid.filter(n=>n<=this.state.bet).at(-1) || valid[0] || 1;}this.state.maxRoleLevel=Math.max(this.state.maxRoleLevel || 1,this.state.level);this.restoreDice();
  }
  fresh() {
    const state = {version:1,map:1,coins:60000,dice:300,shield:2,shieldCap:3,bet:1,position:0,level:1,buildings:Array.from({length:5},() => ({level:0,damaged:false})),gacha:0,fund:0,turns:0,freeRolls:0,shields:[],rents:[],report:[],pending:null,lastRecovery:this.clock(),gachaDraws:0,opponents:[{name:'风间',shield:1,buildings:[2,3,2,1,3]},{name:'阿呆',shield:0,buildings:[3,2,1,2,2]},{name:'正男',shield:2,buildings:[1,2,3,2,1]}]};
    this.state = state; this.refreshEvents(); return state;
  }
  restore(saved) {
    if (!saved || saved.version !== 1 || !Array.isArray(saved.buildings) || saved.buildings.length !== 5 || !Array.isArray(saved.opponents) || saved.opponents.length !== 3) return null;
    for (const key of ['coins','dice','shield','bet','level','map','position','turns','lastRecovery']) if (!Number.isSafeInteger(saved[key]) || saved[key] < 0) return null;
    if (saved.map < 1 || saved.position >= 40 || saved.bet < 1 || !Array.isArray(saved.report) || !Array.isArray(saved.shields) || !Array.isArray(saved.rents)) return null;
    if (saved.pending && !['chance','prison','attack','blind','shield','rent'].includes(saved.pending.kind)) return null;
    return clone(saved);
  }
  snapshot() { return clone(this.state); }
  get nativeMap(){return this.rules.maps[String(Math.min(this.state?.map || 1,3))];}
  attribute(id){const level=Math.max(this.state?.maxRoleLevel || 1,this.state?.level || 1);if(this.attributeCacheLevel!==level){this.attributeCacheLevel=level;this.attributeCache=Object.fromEntries(Object.values(this.rules.playerVariables).map(p=>[p.id,p.baseValue]));const extra={};for(const row of this.rules.levelGrowth.CN.levels)if(row.level<=level)for(const p of row.parameters)extra[p.id]=p.value;for(const [key,value]of Object.entries(extra))this.attributeCache[key]=(this.attributeCache[key] || 0)+value;if(this.state)this.state.maxRoleLevel=level;}return this.attributeCache[id] || 0;}
  global(name,fallback=0){return this.rules.globals[name]?.CN ?? this.data.globals[name] ?? fallback;}
  get fundPool(){return this.nativeMap.fundBase+this.attribute(20107)+this.state.fund;}
  get diceCap(){return this.attribute(20004);}
  get diceRecovery(){return this.attribute(20003);}
  static floor3(value){const p=10**Math.max(0,Math.floor(Math.log10(Math.max(1,value)))-2);return Math.floor(value/p)*p;}
  static rewardDollar(value){if(value<=100000)return Math.floor(value);const p=10**(String(Math.floor(value)).length-3);return Math.ceil(value/p)*p;}
  squareDollar(tile,bet=1){const base=Math.floor(tile.param*this.inflation*(10000+this.attribute(20130))/10000),id=tile.type===1?20005:tile.type===9?20007:20006;return BoardGame.floor3((base+this.attribute(id))*bet);}
  grantAssets(rewards){const s=this.state;s.inventory ||= {};for(const r of rewards){if(r.type===1&&r.id===1)s.coins+=r.count;else if(r.type===1&&r.id===2)s.dice+=r.count;else if(r.type===1&&r.id===3)s.gacha+=r.count;else s.inventory[r.type+':'+r.id]=(s.inventory[r.type+':'+r.id] || 0)+r.count;}}
  blindReward(symbol,bet,p=this.state.pending){const ratios=[this.global('GRAB_SMALL_SUCCESS_GIVE_DOLLAR_RATIO'),this.global('GRAB_MIDDLE_SUCCESS_GIVE_DOLLAR_RATIO'),this.global('GRAB_BIG_SUCCESS_GIVE_DOLLAR_RATIO')];return BoardGame.rewardDollar(Math.floor((p.baseDollar+this.attribute(20103))*ratios[symbol]/10000)*bet);}
  createBlindSequence(tier){const entries=this.rules.globals.GRAB_TURN_NUM_WEIGHT.CNText.split('|').map(x=>{const[n,weight]=x.split(';').map(Number);return{n,weight};}),n=this.weighted(entries).n,others=[0,1,2].filter(x=>x!==tier),prefix=[tier,tier];while(prefix.length<n-1){const allowed=others.filter(x=>prefix.filter(y=>y===x).length<2);prefix.push(allowed[this.int(allowed.length)]);}for(let i=prefix.length-1;i>0;i--){const j=this.int(i+1);[prefix[i],prefix[j]]=[prefix[j],prefix[i]];}return [...prefix,tier];}
  get mapConfig() { return this.data.maps[Math.min(this.state.map-1,this.data.maps.length-1)]; }
  get inflation() { return this.mapConfig.inflation; }
  get maxBuildLevel() { return this.state.map === 1 ? 3 : 6; }
  get canUpgradeMap() {return this.state.buildings.every(b => b.level >= this.maxBuildLevel && !b.damaged);}
  get tile() {return this.data.squares[this.state.position];}
  get gachaCost() {return this.global('GACHA_ONCE_CONSUME',15);}
  nameOf(type) {return TYPES[type] || '棋盘';}
  int(max) {return Math.min(max-1,Math.floor(this.random()*max));}
  die() {return this.int(6)+1;}
  weighted(items,key='weight') {
    const total = items.reduce((sum,item) => sum+Math.max(0,Number(item[key]) || 0),0);
    if (!items.length || !total) return items[0];
    let n = this.random()*total;
    return items.find(item => (n-=Math.max(0,Number(item[key]) || 0))<0) || items.at(-1);
  }
  record(message) {this.state.report.unshift({message,time:this.clock()});this.state.report=this.state.report.slice(0,50);}
  availableBets() {
    if(this.nativeMap.newPlayerBets.length)return [...this.nativeMap.newPlayerBets];
    const rows=this.data.bets.filter(row => row.min <= this.state.dice).sort((a,b) => b.min-a.min);
    return (rows[0]?.values || [1]).filter(n => n > 0 && (n <= this.state.dice || n===1));
  }
  nextBet() {if (this.state.pending || this.state.freeRolls > 0) return this.state.bet;const bets=this.availableBets();this.state.bet=bets[(bets.indexOf(this.state.bet)+1)%bets.length];return this.state.bet;}
  restoreDice() {
    const cap=this.diceCap, amount=this.diceRecovery, interval=3600000;
    const now=this.clock();
    if (this.state.dice>=cap) {this.state.lastRecovery=now;return 0;}
    const steps=Math.max(0,Math.floor((now-this.state.lastRecovery)/interval));
    const added=Math.min(cap-this.state.dice,steps*amount);this.state.dice+=added;
    if (steps) this.state.lastRecovery+=steps*interval;
    return added;
  }
  refreshEvents() {
    const pool=this.data.squares.filter(t => [3,4,9].includes(t.type)).map(t=>t.id-1);
    for(let i=pool.length-1;i>0;i--){const j=this.int(i+1);[pool[i],pool[j]]=[pool[j],pool[i]];}
    const count=this.data.globals.MAP_SHIELD_EVENT_BASE_NUM || 4;
    this.state.shields=pool.slice(0,count);this.state.rents=pool.slice(count,count+4);
  }
  replaceEvent(kind,oldPos) {
    const state=this.state;const occupied=new Set([...state.shields,...state.rents,oldPos]);
    const allowed=this.data.squares.filter(t => [3,4,9].includes(t.type) && !occupied.has(t.id-1)).map(t=>t.id-1);
    const list=kind==='shield'?state.shields:state.rents;const index=list.indexOf(oldPos);
    if(index>=0)list.splice(index,1,allowed[this.int(allowed.length)] ?? oldPos);
  }
  roll() {
    const s=this.state; if(s.pending) return {error:'请先完成当前事件'};
    this.restoreDice();
    if(s.freeRolls<=0 && s.dice<s.bet) return {error:'骰子不足'};
    const before=s.coins,coinEvents=[]; const bet=s.bet; const free=s.freeRolls>0;
    if(free)s.freeRolls--;else s.dice-=bet;
    const dice=[this.die(),this.die()];const steps=dice[0]+dice[1];const from=s.position;const path=[];
    for(let i=0;i<steps;i++){s.position=(s.position+1)%40;path.push(s.position);if(s.position===0){const amount=this.squareDollar(this.data.squares[0],bet);s.coins+=amount;coinEvents.push({index:0,amount,phase:i===steps-1?'land':'exit',kind:'start'});}}
    if(dice[0]===dice[1]){const amount=BoardGame.rewardDollar((this.nativeMap.sameDice+this.attribute(20108))*bet);s.coins+=amount;coinEvents.unshift({index:from,amount,phase:'dice',kind:'sameDice'});}
    s.turns++;const event=this.land(bet,false,coinEvents);this.record(`第${s.turns}次投点：${dice.join('+')}，${this.nameOf(this.tile.type)}`);
    return {from,path,dice,steps,bet,free,event,gain:s.coins-before,coinEvents,coinsBefore:before,tile:clone(this.tile)};
  }
  land(bet=this.state.bet,forceBlind=false,coinEvents=null) {
    const s=this.state;const tile=this.tile,before=s.coins;let result=null;
    if([3,9].includes(tile.type))s.coins+=this.squareDollar(tile,bet);
    if(tile.type===4)s.coins=Math.max(0,s.coins-Math.round(tile.param*this.inflation));
    if(s.coins!==before)coinEvents?.push({index:s.position,amount:s.coins-before,phase:'land',kind:'square'});
    if(tile.type===2){const value=(Math.floor(BoardGame.floor3(tile.param*this.inflation)*(10000+this.attribute(20130))/10000)+this.attribute(20109))*bet;s.fund+=value;result={kind:'fund-add',value};}
    if(tile.type===6){const pool=this.data.chances.filter(c=>c.pool===1 && c.weight>0 && c.type<=6);const card=clone(this.weighted(pool));s.pending={kind:'chance',card,bet};}
    if(tile.type===7)s.pending={kind:'prison',bet,attempts:0,history:[],fine:Math.round(tile.param*this.inflation)};
    if(tile.type===8) {
      const target=this.int(s.opponents.length);const blind=forceBlind || this.random()>=this.global('BUDDY_TRICK_DAMAGE_WEIGHT',75)/100;
      if(blind){const weights=this.nativeMap.robLevelWeights,tier=this.weighted([{tier:0,weight:weights.small},{tier:1,weight:weights.middle},{tier:2,weight:weights.big}]).tier,range=this.weighted(this.nativeMap.robGainRanges);let baseDollar=range.lower+this.int(range.upper-range.lower+1);if(baseDollar>=10000)baseDollar=Math.floor(baseDollar/1000)*1000;s.pending={kind:'blind',bet,target,tier,baseDollar,picks:[],sequence:this.createBlindSequence(tier),finished:false};}
      else s.pending={kind:'attack',bet,target};
    }
    if(s.shields.includes(s.position)){
      s.shieldCap=this.attribute(20000);const awarded=Math.min(bet,Math.max(0,s.shieldCap-s.shield));const returned=bet-awarded;s.shield+=awarded;s.dice+=returned;this.replaceEvent('shield',s.position);s.pending={kind:'shield',awarded,returned};
    }else if(s.rents.includes(s.position)){
      const value=BoardGame.rewardDollar((this.nativeMap.friendEventToll+this.attribute(20008)+this.attribute(this.rules.rentColorAttributes?.[tile.id] || 0))*bet);s.coins+=value;this.replaceEvent('rent',s.position);s.pending={kind:'rent',value,bet,target:s.position%s.opponents.length};
    }
    return s.pending || result;
  }
  dismiss() {if(['shield','rent'].includes(this.state.pending?.kind)){this.state.pending=null;return true;}return false;}
  resolveChance() {
    const s=this.state,p=s.pending;if(p?.kind!=='chance')return null;const coinsBefore=s.coins;s.pending=null;
    const c=p.card;let result={kind:'reward',coins:0,dice:0,free:0};
    if(c.type===1){result.coins=BoardGame.floor3((Math.floor(c.param*this.inflation)+this.attribute(20101))*p.bet);s.coins+=result.coins;}
    if(c.type===2){result.coins=-Math.min(s.coins,Math.round(c.param*this.inflation));s.coins+=result.coins;}
    if(c.type===3){result.dice=c.param*p.bet;s.dice+=result.dice;}
    if(c.type===4){result.free=c.param;s.freeRolls+=c.param;}
    if(c.type===5 || c.type===6){const from=s.position,path=[],coinEvents=[];do{s.position=(s.position+1)%40;path.push(s.position);if(s.position===0){const amount=Math.round(this.data.squares[0].param*this.inflation*p.bet);s.coins+=amount;coinEvents.push({index:0,amount,phase:'exit',kind:'start'});}}while(this.tile.type!==8 && path.length<40);this.land(p.bet,c.type===6,coinEvents);result={kind:'move',from,path,event:s.pending,coinEvents,coinsBefore};}
    this.record('机会卡：'+(result.kind==='move'?'前往好友捣蛋':result.free?`免费投点${result.free}次`:result.dice?`获得${result.dice}骰子`:`美金${result.coins>=0?'+':''}${result.coins}`));return result;
  }
  prisonRoll() {
    const s=this.state,p=s.pending;if(p?.kind!=='prison')return null;
    const dice=[this.die(),this.die()];p.attempts++;p.history.push(dice);
    if(dice[0]===dice[1]){const awarded=dice[0]*p.bet;s.dice+=awarded;s.pending=null;this.record(`成功脱困，获得${awarded}骰子`);return {dice,success:true,awarded,finished:true};}
    if(p.attempts>=3){const fine=Math.min(s.coins,p.fine);s.coins-=fine;s.pending=null;this.record(`脱困失败，缴纳${fine}美金`);return {dice,success:false,fine,finished:true};}
    return {dice,success:false,attempts:p.attempts,finished:false};
  }
  changeOpponent(index) {const p=this.state.pending;if(p?.kind!=='attack'||!Number.isInteger(index)||index<0||index>=this.state.opponents.length)return false;p.target=index;return true;}
  attack(index) {
    const s=this.state,p=s.pending;if(p?.kind!=='attack')return null;const target=s.opponents[p.target];
    if(!Number.isInteger(index)||index<0||index>=5||target.buildings[index]<=0)return {error:'请选择可破坏的建筑'};
    const blocked=target.shield>0;if(blocked)target.shield--;else{target.damaged ||= Array(5).fill(false);if(target.damaged[index])target.buildings[index]--;else target.damaged[index]=true;}
    const coins=BoardGame.rewardDollar(((blocked?this.nativeMap.destroyLoseGain:this.nativeMap.destroyWinGain)+this.attribute(20104)+(blocked?this.attribute(20105):0))*p.bet);s.coins+=coins;s.pending=null;this.record(`${blocked?'被护盾挡住':'捣蛋成功'}：${target.name}，获得${coins}美金`);return {blocked,coins,name:target.name,index};
  }
  openBlind(index) {
    const s=this.state,p=s.pending;if(p?.kind!=='blind'||!Number.isInteger(index)||index<0||index>=12||p.picks.some(v=>v.index===index))return null;
    const symbol=p.sequence[p.picks.length];p.picks.push({index,symbol});
    const matched=p.picks.filter(v=>v.symbol===symbol).length;
    if(matched>=3){const coins=Number.isFinite(p.baseDollar)?this.blindReward(symbol,p.bet,p):Math.round([5000,10000,15000][symbol]*p.bet);s.coins+=coins;const result={finished:true,coins,symbol,picks:clone(p.picks)};s.pending=null;this.record(`盲盒匹配成功，获得${coins}美金`);return result;}
    return {finished:false,symbol,picks:clone(p.picks)};
  }
  buildingCost(index) {
    const b=this.state.buildings[index];if(!b)return 0;
    const id=this.mapConfig.buildIds[index];const level=b.damaged?Math.max(1,b.level):b.level+1;
    const original=this.data.buildCosts.find(c=>c.id===id&&c.level===level)?.cost;
    const raw=original ?? Math.round((4000+index*1600)*Math.pow(1.8,level-1)*Math.pow(1.4,this.state.map-1));
    return b.damaged?Math.max(1,Math.floor(raw*(this.data.globals.BUILDING_FIXED_AMOUNT_RATIO || 20)/100)):raw;
  }
  build(index) {
    const s=this.state;if(s.pending)return {error:'请先完成棋盘事件'};const b=s.buildings[index];if(!b)return {error:'建筑不存在'};
    if(!b.damaged&&b.level>=this.maxBuildLevel)return {error:'已满级'};
    const cost=this.buildingCost(index);if(s.coins<cost)return {error:'美金不足'};
    s.coins-=cost;const repaired=b.damaged;
    if(repaired){b.damaged=false;b.level=Math.max(1,b.level);}else{b.level++;if(this.mapConfig.buildIds[index]!==this.global('GUIDE_NO_REWARD_BUILDING'))s.gacha+=this.global('BUILDING_UPGRADE_GIVE_GACHA_NUM',1);}
    if(this.mapConfig.buildIds[index]!==this.global('GUIDE_INITIALZE_BUILDING_LV_ONE'))s.level++;s.shieldCap=this.attribute(20000);this.record(`${repaired?'修复':'升级'}建筑${index+1}至${b.level}级`);return {index,cost,level:b.level,repaired,complete:this.canUpgradeMap};
  }
  upgradeMap() {
    if(!this.canUpgradeMap||this.state.pending||this.state.map>=this.data.maps.length)return false;
    const s=this.state;s.map++;s.position=0;s.buildings=Array.from({length:5},()=>({level:0,damaged:false}));s.fund=0;this.refreshEvents();this.grantAssets(this.nativeMap.welcomeRewards);s.dice+=this.attribute(20009);this.record(`进入第${s.map}张地图`);return true;
  }
  openFund() {
    const s=this.state;if(s.pending)return {error:'请先完成棋盘事件'};if(s.fund<=0)return {error:'踩到存钱罐格子，积累奖励'};
    const coins=s.fund;s.fund=0;s.coins+=coins;this.record(`领取存钱罐${coins}美金`);return {coins};
  }
  ensureGachaQueue(){const s=this.state;if(!s.gachaSequence?.length){const pool=[...this.data.gacha];s.gachaSequence=[];if(!s.gachaFirstCreated){for(const id of this.rules.gachaFirst || []){const at=pool.findIndex(x=>x.id===id);if(at>=0)s.gachaSequence.push(pool.splice(at,1)[0].id);}s.gachaFirstCreated=true;}while(pool.length){const chosen=this.weighted(pool);s.gachaSequence.push(chosen.id);pool.splice(pool.indexOf(chosen),1);}}return s.gachaSequence;}
  drawGachaMany(count=1){if(this.state.pending)return{error:'请先完成棋盘事件'};const s=this.state,n=Math.max(1,Math.min(5,Math.floor(count))),today=new Date(this.clock()+8*3600000).toISOString().slice(0,10),used=s.gachaDay===today?(s.gachaToday || 0):0;if(s.gacha<this.gachaCost*n)return{error:'扭蛋币不足'};if(used+n>this.global('DAY_GACHA_LIMIT',100))return{error:'今日扭蛋次数不足'};const draws=Array.from({length:n},()=>this.drawGacha());return {coins:draws.reduce((v,r)=>v+r.coins,0),dice:draws.reduce((v,r)=>v+r.dice,0),card:0,gold:draws.some(r=>r.gold),draws};}
  drawGacha() {
    const s=this.state;if(s.pending)return {error:'请先完成棋盘事件'};if(s.gacha<this.gachaCost)return {error:`建造或升级获得扭蛋币，集满${this.gachaCost}个可扭蛋`};
    const today=new Date(this.clock()+8*3600000).toISOString().slice(0,10);if(s.gachaDay!==today){s.gachaDay=today;s.gachaToday=0;}if((s.gachaToday || 0)>=this.global('DAY_GACHA_LIMIT',100))return{error:'今日扭蛋次数已用完'};this.ensureGachaQueue();const prize=this.data.gacha.find(x=>x.id===s.gachaSequence[0]);if(!prize)return {error:'奖池不可用'};
    s.gacha-=this.gachaCost;s.gachaDraws++;s.gachaToday=(s.gachaToday || 0)+1;s.gachaSequence.shift();const meta=this.rules.gachaMeta?.[prize.id];let coins=0,dice=0,card=0;
    for(const reward of prize.rewards){if(meta?.isGold){s.sealedDrops ||= {};s.sealedDrops[reward.id]=(s.sealedDrops[reward.id] || 0)+1;}else if(reward.id===1){coins+=Math.round(reward.count*this.inflation);}else if(reward.id===2){dice+=reward.count;}else if(reward.id>7){s.inventory ||= {};s.inventory['2:'+reward.id]=(s.inventory['2:'+reward.id] || 0)+reward.count;}}
    if(meta?.isGold)s.gachaSequence=[];s.coins+=coins;s.dice+=dice;s.stickers=(s.stickers || 0)+card;this.record(`扭蛋奖励：${coins?coins+'美金':dice?dice+'骰子':card+'张贴纸'}`);return {coins,dice,card,gold:!!meta?.isGold,prizeId:prize.id,shell:meta?.shell,icon:prize.icon};
  }
}