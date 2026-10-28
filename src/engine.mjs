export const SAVE_KEY = 'shin-board-h5-v1';
const clone = value => JSON.parse(JSON.stringify(value));
const TYPES = ['','起点','存钱罐','金币','缴费','停车场','机会','陷阱','好友捣蛋','公共事业'];
export class BoardGame {
  constructor(data, saved = null, options = {}) {
    this.data = data; this.random = options.random || Math.random; this.clock = options.clock || Date.now;
    this.state = this.restore(saved) || this.fresh();
    this.restoreDice();
  }
  fresh() {
    const state = {version:1,map:1,coins:60000,dice:300,shield:2,shieldCap:5,bet:1,position:0,level:1,buildings:Array.from({length:5},() => ({level:0,damaged:false})),gacha:0,fund:0,turns:0,freeRolls:0,shields:[],rents:[],report:[],pending:null,lastRecovery:this.clock(),gachaDraws:0,opponents:[{name:'风间',shield:1,buildings:[2,3,2,1,3]},{name:'阿呆',shield:0,buildings:[3,2,1,2,2]},{name:'正男',shield:2,buildings:[1,2,3,2,1]}]};
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
  get mapConfig() { return this.data.maps[Math.min(this.state.map-1,this.data.maps.length-1)]; }
  get inflation() { return this.mapConfig.inflation; }
  get maxBuildLevel() { return this.state.map === 1 ? 3 : 6; }
  get canUpgradeMap() {return this.state.buildings.every(b => b.level >= this.maxBuildLevel && !b.damaged);}
  get tile() {return this.data.squares[this.state.position];}
  get gachaCost() {return this.data.globals.GACHA_ONCE_CONSUME || 15;}
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
    const rows=this.data.bets.filter(row => row.min <= this.state.dice).sort((a,b) => b.min-a.min);
    return (rows[0]?.values || [1]).filter(n => n > 0 && (n <= this.state.dice || n===1));
  }
  nextBet() {if (this.state.pending || this.state.freeRolls > 0) return this.state.bet;const bets=this.availableBets();this.state.bet=bets[(bets.indexOf(this.state.bet)+1)%bets.length];return this.state.bet;}
  restoreDice() {
    const cap=50, amount=5, interval=3600000;
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
    const before=s.coins; const bet=s.bet; const free=s.freeRolls>0;
    if(free)s.freeRolls--;else s.dice-=bet;
    const dice=[this.die(),this.die()];const steps=dice[0]+dice[1];const from=s.position;const path=[];
    for(let i=0;i<steps;i++){s.position=(s.position+1)%40;path.push(s.position);if(s.position===0)s.coins+=Math.round(this.data.squares[0].param*this.inflation*bet);}
    if(dice[0]===dice[1])s.coins+=Math.round(60*bet);
    s.turns++;const event=this.land(bet);this.record(`第${s.turns}次投点：${dice.join('+')}，${this.nameOf(this.tile.type)}`);
    return {from,path,dice,steps,bet,free,event,gain:s.coins-before,tile:clone(this.tile)};
  }
  land(bet=this.state.bet,forceBlind=false) {
    const s=this.state;const tile=this.tile;let result=null;
    if([3,9].includes(tile.type))s.coins+=Math.round((tile.param*this.inflation+(s.level-1)*5)*bet);
    if(tile.type===4)s.coins=Math.max(0,s.coins-Math.round(tile.param*this.inflation));
    if(tile.type===2){const value=Math.round(tile.param*this.inflation*bet);s.fund+=value;result={kind:'fund-add',value};}
    if(tile.type===6){const pool=this.data.chances.filter(c=>c.pool===1 && c.weight>0 && c.type<=6);const card=clone(this.weighted(pool));s.pending={kind:'chance',card,bet};}
    if(tile.type===7)s.pending={kind:'prison',bet,attempts:0,history:[],fine:Math.round(tile.param*this.inflation)};
    if(tile.type===8) {
      const target=this.int(s.opponents.length);const blind=forceBlind || this.random()<.35;
      if(blind){const tier=this.weighted([{tier:0,weight:10},{tier:1,weight:60},{tier:2,weight:30}]).tier;const other=[0,1,2].filter(n=>n!==tier);s.pending={kind:'blind',bet,target,tier,picks:[],sequence:[tier,other[0],other[1],tier,other[0],other[1],tier],finished:false};}
      else s.pending={kind:'attack',bet,target};
    }
    if(s.shields.includes(s.position)){
      const awarded=Math.min(bet,s.shieldCap-s.shield);const returned=bet-awarded;s.shield+=awarded;s.dice+=returned;this.replaceEvent('shield',s.position);s.pending={kind:'shield',awarded,returned};
    }else if(s.rents.includes(s.position)){
      const value=Math.round((60+(s.level-1)*5)*bet);s.coins+=value;this.replaceEvent('rent',s.position);s.pending={kind:'rent',value,target:this.int(s.opponents.length)};
    }
    return s.pending || result;
  }
  dismiss() {if(['shield','rent'].includes(this.state.pending?.kind)){this.state.pending=null;return true;}return false;}
  resolveChance() {
    const s=this.state,p=s.pending;if(p?.kind!=='chance')return null;s.pending=null;
    const c=p.card;let result={kind:'reward',coins:0,dice:0,free:0};
    if(c.type===1){result.coins=Math.round(c.param*this.inflation*p.bet);s.coins+=result.coins;}
    if(c.type===2){result.coins=-Math.min(s.coins,Math.round(c.param*this.inflation));s.coins+=result.coins;}
    if(c.type===3){result.dice=c.param*p.bet;s.dice+=result.dice;}
    if(c.type===4){result.free=c.param;s.freeRolls+=c.param;}
    if(c.type===5 || c.type===6){const from=s.position,path=[];do{s.position=(s.position+1)%40;path.push(s.position);if(s.position===0)s.coins+=Math.round(this.data.squares[0].param*this.inflation*p.bet);}while(this.tile.type!==8 && path.length<40);this.land(p.bet,c.type===6);result={kind:'move',from,path,event:s.pending};}
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
    const coins=Math.round((blocked?3000:6000)*p.bet);s.coins+=coins;s.pending=null;this.record(`${blocked?'被护盾挡住':'捣蛋成功'}：${target.name}，获得${coins}美金`);return {blocked,coins,name:target.name,index};
  }
  openBlind(index) {
    const s=this.state,p=s.pending;if(p?.kind!=='blind'||!Number.isInteger(index)||index<0||index>=12||p.picks.some(v=>v.index===index))return null;
    const symbol=p.sequence[p.picks.length];p.picks.push({index,symbol});
    const matched=p.picks.filter(v=>v.symbol===symbol).length;
    if(matched>=3){const coins=Math.round([5000,10000,15000][symbol]*p.bet);s.coins+=coins;const result={finished:true,coins,symbol,picks:clone(p.picks)};s.pending=null;this.record(`盲盒匹配成功，获得${coins}美金`);return result;}
    return {finished:false,symbol,picks:clone(p.picks)};
  }
  buildingCost(index) {
    const b=this.state.buildings[index];if(!b)return 0;
    const id=this.mapConfig.buildIds[index];const level=b.damaged?Math.max(1,b.level):b.level+1;
    const original=this.data.buildCosts.find(c=>c.id===id&&c.level===level)?.cost;
    const raw=original || Math.round((4000+index*1600)*Math.pow(1.8,level-1)*Math.pow(1.4,this.state.map-1));
    return b.damaged?Math.max(1,Math.floor(raw*(this.data.globals.BUILDING_FIXED_AMOUNT_RATIO || 20)/100)):raw;
  }
  build(index) {
    const s=this.state;if(s.pending)return {error:'请先完成棋盘事件'};const b=s.buildings[index];if(!b)return {error:'建筑不存在'};
    if(!b.damaged&&b.level>=this.maxBuildLevel)return {error:'已满级'};
    const cost=this.buildingCost(index);if(s.coins<cost)return {error:'美金不足'};
    s.coins-=cost;const repaired=b.damaged;
    if(repaired){b.damaged=false;b.level=Math.max(1,b.level);}else{b.level++;s.gacha+=(this.data.globals.BUILDING_UPGRADE_GIVE_GACHA_NUM || 1);}
    s.level++;this.record(`${repaired?'修复':'升级'}建筑${index+1}至${b.level}级`);return {index,cost,level:b.level,repaired,complete:this.canUpgradeMap};
  }
  upgradeMap() {
    if(!this.canUpgradeMap||this.state.pending)return false;
    const s=this.state;s.map++;s.position=0;s.buildings=Array.from({length:5},()=>({level:0,damaged:false}));s.fund=0;this.refreshEvents();s.dice+=50;s.coins+=10000;this.record(`进入第${s.map}张地图`);return true;
  }
  openFund() {
    const s=this.state;if(s.pending)return {error:'请先完成棋盘事件'};if(s.fund<=0)return {error:'踩到存钱罐格子，积累奖励'};
    const coins=s.fund;s.fund=0;s.coins+=coins;this.record(`领取存钱罐${coins}美金`);return {coins};
  }
  drawGacha() {
    const s=this.state;if(s.pending)return {error:'请先完成棋盘事件'};if(s.gacha<this.gachaCost)return {error:`建造或升级获得扭蛋币，集满${this.gachaCost}个可扭蛋`};
    const prize=this.weighted(this.data.gacha);if(!prize)return {error:'奖池不可用'};
    s.gacha-=this.gachaCost;s.gachaDraws++;let coins=0,dice=0,card=0;
    for(const reward of prize.rewards){if(reward.id===1){coins+=Math.round(reward.count*this.inflation);}else if(reward.id===2){dice+=reward.count;}else card+=reward.count;}
    s.coins+=coins;s.dice+=dice;s.stickers=(s.stickers || 0)+card;this.record(`扭蛋奖励：${coins?coins+'美金':dice?dice+'骰子':card+'张贴纸'}`);return {coins,dice,card,icon:prize.icon};
  }
}