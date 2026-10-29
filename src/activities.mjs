// Original CN milestone schedules, score goals and rewards are in assets/activities/config.json.
export class MilestoneActivities {
 constructor(game,config,{clock=Date.now,enforceMapUnlock=false}={}){this.game=game;this.config=config;this.clock=clock;this.enforceMapUnlock=enforceMapUnlock;this.ensure();}
 ensure(){const s=this.game.state;if(s.milestoneActivities?.version!==1)s.milestoneActivities={version:1,progress:{},inventory:{}};for(const a of this.config.activities){const old=s.milestoneActivities.progress[a.id];if(!old||!Number.isSafeInteger(old.score)||old.score<0||!Array.isArray(old.awarded)||!Array.isArray(old.processed))s.milestoneActivities.progress[a.id]={score:0,awarded:[],processed:[],history:[],rankRewardClaimed:false};}return s.milestoneActivities;}
 activity(kind){return this.config.activities.find(a=>a.kind===kind);}
 state(activity){return this.ensure().progress[activity.id];}
 status(activity){const now=this.clock();return now<activity.startAtMs?'upcoming':now>=activity.endAtMs?'ended':this.enforceMapUnlock&&this.game.state.map<activity.mapUnlock?'locked':'active';}
 stages(activity){return this.config.stages[String(activity.seqId)];}
 current(activity){const state=this.state(activity),stages=this.stages(activity);return stages.find(s=>state.score<s.max)||null;}
 progress(activity){const stage=this.current(activity),state=this.state(activity);return{stage,score:state.score,value:stage?state.score-stage.min:0,total:stage?stage.singleValue:0,fraction:stage?(state.score-stage.min)/stage.singleValue:1};}
 rewards(stage){return this.game.state.level<3?stage.resolvedOfflineRewards:stage.resolvedNormalOfflineRewards;}
 grant(rewards){const s=this.game.state,inventory=this.ensure().inventory;for(const r of rewards){if(r.type===1){if(r.id===1)s.coins+=r.count;else if(r.id===2)s.dice+=r.count;else if(r.id===3)s.gacha+=r.count;else inventory[`resource:${r.id}`]=(inventory[`resource:${r.id}`]||0)+r.count;}else inventory[String(r.id)]=(inventory[String(r.id)]||0)+r.count;}}
 add(activity,points,eventId){if(this.status(activity)!=='active'||points<=0)return null;const state=this.state(activity);if(state.processed.includes(eventId))return null;state.processed.push(eventId);state.processed=state.processed.slice(-100);const before=state.score;state.score+=Math.round(points);const awards=[];for(const stage of this.stages(activity))if(state.score>=stage.max&&!state.awarded.includes(stage.index)){const rewards=this.rewards(stage);this.grant(rewards);state.awarded.push(stage.index);awards.push({stage:stage.index,rewards});}state.history.unshift({eventId,points:state.score-before,at:this.clock()});state.history=state.history.slice(0,20);return{activityId:activity.id,kind:activity.kind,before,score:state.score,points:state.score-before,awards};}
 landing(index,bet,eventId){const a=this.activity('noRank'),tile=this.game.data.squares[index],rules=this.config.goals[String(a.goalId)],points=rules.filter(g=>g.type===1&&tile.groups.includes(g.squareGroup)).reduce((n,g)=>n+g.score*bet,0);return this.add(a,points,eventId);}
 attack(blocked,bet,eventId){return this.outcome(blocked?2:3,bet,eventId);}
 blind(symbol,bet,eventId){return this.outcome(4+symbol,bet,eventId);}
 outcome(type,bet,eventId){const a=this.activity('rank'),rule=this.config.goals[String(a.goalId)].find(g=>g.type===type);return rule?this.add(a,rule.score*bet,eventId):null;}
 unlocked(){return this.state(this.activity('rank')).score>=this.config.rank.unlockScore;}
 // Local H5 has one real participant; never manufacture online players or scores.
 leaderboard(){if(!this.unlocked())return[];return[{rank:1,name:'小新（本机）',score:this.state(this.activity('rank')).score,rewards:this.config.rank.rewards.find(r=>r.minRank===1).rewards}];}
 claimRank(){const a=this.activity('rank'),s=this.state(a);if(this.status(a)!=='ended'||!this.unlocked()||s.rankRewardClaimed)return null;const entry=this.leaderboard()[0];s.rankRewardClaimed=true;this.grant(entry.rewards);return entry.rewards;}
}
export function activityTime(milliseconds){if(milliseconds<=0)return'已结束';let minutes=Math.floor(milliseconds/60000),days=Math.floor(minutes/1440),hours=Math.floor(minutes/60)%24;return days?`${days}天${hours}小时`:hours?`${hours}小时${minutes%60}分`:`${Math.max(1,minutes)}分`;}
