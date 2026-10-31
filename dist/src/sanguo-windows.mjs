import{loadSpriteAtlas}from './sanguo-cast.mjs';
const ROOT='assets/scene/skins/sanguo/';
const CLEAR='data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs=';
// Scene cards are rectangular paintings, so crop their atlas cells explicitly rather
// than treating soft painted gutters as disconnected character silhouettes.
const loadChanceScenes=url=>new Promise((resolve,reject)=>{const image=new Image();image.onerror=()=>reject(new Error('机缘插画加载失败'));image.onload=()=>resolve([[.045,.072,.442,.429],[.51,.072,.458,.429],[.045,.531,.442,.429],[.51,.531,.458,.429]].map(([x,y,w,h])=>{const canvas=document.createElement('canvas');canvas.width=Math.round(image.width*w);canvas.height=Math.round(image.height*h);canvas.getContext('2d').drawImage(image,image.width*x,image.height*y,image.width*w,image.height*h,0,0,canvas.width,canvas.height);return{canvas};}));image.src=url;});
// Presentation-only routing. Native windows continue to own values, controllers and actions.
export class SanguoWindows{
 static async load(icons){const skin=new SanguoWindows();skin.icons=icons;const [district,buildings,milestone,cast,lord,chance,audit]=await Promise.all([loadSpriteAtlas(ROOT+'district-v4.png',2,2),loadSpriteAtlas(ROOT+'buildings-v3.png',2,2),fetch('assets/scene/milestone/ui.json').then(r=>r.json()),loadSpriteAtlas(ROOT+'cast-v4.png',4,2),loadSpriteAtlas(ROOT+'lord-v4.png',4,2),loadChanceScenes(ROOT+'chance-scenes-v10.png'),fetch('assets/scene/audit-ui.json').then(r=>r.json())]);skin.buildings=[district[0],buildings[0],buildings[1],district[1],district[3]].map(f=>f.canvas.toDataURL());skin.figures=[lord[0],cast[0],cast[1],cast[2]].map(f=>f.canvas.toDataURL());skin.chance=chance.map(f=>f.canvas.toDataURL());skin.dynamicNames=new Map([...Object.entries(milestone.dynamicImages).map(([name,r])=>[r.url,name]),...Object.entries(audit.images).map(([name,url])=>[url,name])]);return skin;}
 install(ui){this.ui=ui;ui.sanguoActivityIcon=this.icons[14];this.names=new Map(this.dynamicNames);for(const p of Object.values(ui.data.packages))for(const r of Object.values(p.items))if(r.url)this.names.set(r.url,r.name);
  const set=ui.setImage.bind(ui);ui.setImage=(el,url,res,contain=true)=>{const name=res?.name||this.names.get(url)||String(url||'').split('/').pop(),replacement=this.image(name,url,el);if(replacement!==undefined)return set(el,replacement,null,!el?.classList.contains('sanguo-panel-image')&&!el?.classList.contains('sanguo-background-image'));return set(el,url,res,contain);};
  const renderText=ui.renderText.bind(ui);ui.renderText=(el,value)=>renderText(el,this.text(value));
  const action=ui.action.bind(ui);ui.action=(root,path,code,label)=>action(root,path,code,label===undefined?label:this.text(label));
  const component=ui.component.bind(ui);ui.component=(pkg,id,options,depth)=>{const v=component(pkg,id,options,depth),name=ui.resource(pkg,id)?.name||'';v.classList.add('sanguo-window-skin');if(/PlayerInfoWindow/.test(name))v.classList.add('sanguo-profile-window');return v;};
 }
 text(value){let text=String(value);for(const[from,to]of [['欢迎来到春日部','蜀地新城'],['春日部','蜀地'],['防卫队','军团'],['小新（本机）','主公（本机）'],['小新','主公'],['幼儿园巴士格','驿站格'],['幼儿园','书院'],['动感超人','武将'],['巧克比','军粮'],['埼玉红蝎队','巡城军'],['松坂老师','先生'],['阿呆','友人'],['广志','老将'],['蜡笔森林','山林'],['小白','灵犬'],['电视节目','集市演出'],['秋田','故乡'],['扭蛋','宝匣'],['美金','铜钱']])text=text.replaceAll(from,to);return text;}
 image(name,url,el){const icon=i=>this.icons[i],panel=()=>{el?.classList.add('sanguo-panel-image');return ROOT+'parchment-panel-v9.png';};
  const title=text=>{if(el){el.dataset.sanguoTitle=text;el.classList.add('sanguo-event-title');}return CLEAR;};
  if(String(url).includes('/scene/chance/')){if(name==='title.png')return title('机缘');const card=(window.GAME_DATA?.chances||[]).find(c=>String(url).endsWith(c.pic+'_01.png'));const frame=card?(card.type===2?1:[5,6].includes(card.type)?2:[3,4].includes(card.type)?3:0):0;return this.chance[frame];}
  if(/img_gacha_title_0[12]/.test(name))return title(/_02/.test(name)?'珍藏宝匣':'寻宝');
  if(/img_BlindBox_title_01/.test(name))return title('寻得珍藏');if(/img_BlindBox_title_02/.test(name))return title('揭晓宝匣');if(/img_Guessing_box_Lucky/.test(name))return title('鸿运');
  if(/^img_GachaMachine05(?:_red)?\.png$/.test(name)){el?.classList.add('sanguo-background-image');return ROOT+'treasure-cabinet-v10.png';}
  if(/^img_GachaMachine03(?:_red)?\.png$/.test(name))return ROOT+'milestone-banner-v9.png';
  if(/^img_GachaMachine04(?:_red)?\.png$/.test(name))return panel();
  if(/^img_GachaMachine0(?:1|11)\.png$/.test(name)){el?.classList.add('sanguo-cabinet-glass');return CLEAR;}
  if(/^img_GachaMachine0[26](?:_red)?\.png$/.test(name)){el?.classList.add('sanguo-wood-trim');return CLEAR;}
  if(/^img_GachaMachine07(?:_red)?\.png$/.test(name))return icon(0);
  if(/img_gacha_deco_(?:heart|cloud)/.test(name))return CLEAR;
  if(/^bg_gacha(?:_02)?\.png$/.test(name)){el?.classList.add('sanguo-background-image');return ROOT+'build-courtyard-v9.png';}
  if(/img_gacha_tab|bg_gacha_btn/.test(name))return panel();
  const figure=name.match(/icon_BlindBox_figure0([1-4])/);if(figure)return this.figures[Number(figure[1])-1];
  if(/^img_BlindBox_(?:blue|red)\.png$/.test(name))return icon(9);
  if(/^bg_BlindBox_/.test(name))return panel();
  if(/icon_CardPack_0[1-4]/.test(name)){if(el)el.dataset.sanguoRarity=name.match(/_0([1-4])/)[1];return icon(5);}
  if(/^bg_card_0[1-4]\.png$/.test(name))return panel();
  const build=String(url).match(/icon_build_(?:s_)?\d+_(\d+)_\d+\.png/);if(build)return this.buildings[(Number(build[1])-1)%5];
  if(/bg_build_\d+\.png/.test(name)){el?.classList.add('sanguo-background-image');return ROOT+'build-courtyard-v9.png';}
  if(/(?:img_milestone_banner_|img_rules_banner_|img_tournament_banner_)/.test(name)){el?.classList.add('sanguo-background-image');return ROOT+'milestone-banner-v9.png';}
  if(/img_milestone_title_|tips_milestone_title|tipsTitle/.test(name)){el?.classList.add('sanguo-activity-title');return CLEAR;}
  if(/icon_milestone_/.test(name))return icon(14);
  if(/hely_icon_10/.test(name))return this.buildings[0];if(/hely_icon_11/.test(name))return icon(9);
  const card={jia:4,dujia:10,youzhiyuan:12,xianjing:13,binggan:1,che:10,dunpai:2,jihui:5,jijin:9,jinbi:0,lichengbei:7,luzhang:13};const cardName=name.match(/^img_card_([^_.]+)/);if(cardName&&card[cardName[1]]!==undefined)return icon(card[cardName[1]]);
  if(/(?:icon_money|icon_coin)(?:_|\.)/.test(name))return icon(0);
  if(/icon_(?:shield|sheild)/i.test(name)||['assets/scene/shield.png','assets/scene/shield-front.png'].includes(url))return icon(2);
  if(/icon_(?:level|kb)(?:_|\.)/i.test(name))return icon(1);
  if(name==='icon_friend.png')return icon(6);if(name==='icon_map.png')return icon(4);
  const menu=name.match(/^icon_main_more_(\d+)/);if(menu)return icon(({2:3,3:4,4:8,6:5,7:9,8:15,12:12,13:5,14:5,15:7})[Number(menu[1])]??5);
  if(/icon_main_gacha/.test(name))return icon(9);
  if(/img_main_menu_(?:pen|pig)|(?:^|_)crayons?\d*|^clip\.|img_build_decor|img_build_deco_|bg_build_board_deco|img_player_deco/.test(name))return CLEAR;
  if(/bg_main_menu_0[1-4]|bg_playerinfo_(?:cardholder|panel)|^bg_info\.|img_playerinfo_base|bg_milestone_main|bg_common_panel|img_milestone_skinstand|bg_build_blackboard|img_build_notebook|img_build_bottom|bg_build_top|^paper[123]\.|img_build_paper/.test(name))return panel();
  if(/img_event_shinchan/.test(name))return ROOT+'portrait-v4.png';
  return undefined;
 }
}
