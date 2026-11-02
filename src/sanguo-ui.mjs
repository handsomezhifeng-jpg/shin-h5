import {loadSpriteAtlas} from './sanguo-cast.mjs';
import {SanguoWindows} from './sanguo-windows.mjs';
const ROOT='assets/scene/skins/sanguo/';
export const SANGUO_UI_ASSETS=['ui-icons-v6.png','ui-panel-v6.png','notification-bell-v8.png','build-courtyard-v9.png','milestone-banner-v9.png','parchment-panel-v9.png','treasure-cabinet-v10.png','chance-scenes-v10.png'].map(name=>ROOT+name);
// A skin only: original FGUI hit areas, controllers and live game values remain authoritative.
export class SanguoUI {
 static async load(){const skin=new SanguoUI(),frames=await loadSpriteAtlas(ROOT+'ui-icons-v6.png',4,4);skin.icons=frames.map(f=>f.canvas.toDataURL());skin.sceneShield=frames[2].canvas;skin.windows=await SanguoWindows.load(skin.icons);return skin;}
 install(ui){this.ui=ui;this.windows.install(ui);const set=ui.setImage.bind(ui);ui.setImage=(el,url,res,contain=true)=>{let icon=-1;const name=el?.dataset.name;
  if(el?.closest('[data-name="topMoeny"]')&&['icon','icon_money','n6'].includes(name))icon=0;
  if(el?.closest('[data-name="topKbMini"]')&&['icon','icon_money','n6'].includes(name))icon=1;
  if(el?.closest('[data-name="topShield"]')&&['icon','n6','icon_shield'].includes(name))icon=2;
  if(name==='loader_need'&&el?.closest('[data-name="comp_mileStone"]'))icon=14;
  if(name==='loaderIcon'&&el?.closest('[data-name="activityView"]'))icon=14;
  return set(el,icon<0?url:this.icons[icon],icon<0?res:null,icon<0?contain:true);
 };}
 image(index){const img=document.createElement('img');img.src=this.icons[index];img.alt='';img.className='sanguo-ui-icon';return img;}
 mount(main){main.classList.add('sanguo-ui','ink-ui');const ui=this.ui;
  const fill=document.createElement('div');fill.className='sanguo-bottom-fill';main.fgContent.prepend(fill);
  const plate=document.createElement('img');plate.src=ROOT+'ui-panel-v6.png';plate.className='sanguo-bottom-plate';plate.alt='';fill.after(plate);
  for(const [path,index]of [['btn_guild',3],['btn_build',4],['btn_draw',5],['btn_friend',6]]){const n=ui.find(main,path);n.classList.add('sanguo-icon-button');n.append(this.image(index));}
  for(const [path,label]of [['text_guild','军团'],['text_build','城建'],['text_draw','图鉴'],['text_friend','好友']]){const n=ui.find(main,path);n.fgAttrs={...n.fgAttrs,font:undefined};ui.text(main,path,label);}
  ui.action(main,'btn_guild','unavailable:军团尚未开放','军团');
  // These are navigation shortcuts to existing flows; no fabricated event dates, prices or alerts.
  const entries=[['left',190,8,'将领','profile'],['left',337,9,'宝库','fund'],['left',484,5,'招募','gacha'],['left',631,10,'坐骑','unavailable:坐骑尚未开放'],['left',778,11,'军团','unavailable:军团尚未开放'],['left',925,12,'粮仓','fund'],['left',1072,5,'图鉴','album'],['right',353,5,'招募','gacha'],['right',500,8,'将领','profile'],['right',647,9,'宝库','fund'],['right',794,13,'征战','unavailable:征战尚未开放']];
  const rails=document.createElement('div');rails.className='sanguo-rails';
  for(const[side,top,index,label,action]of entries){const b=document.createElement('button');b.className='sanguo-side-entry '+side;b.style.top=top+'px';b.dataset.action=action;b.setAttribute('aria-label',label);b.append(this.image(index));const title=document.createElement('span');title.textContent=label;b.append(title);rails.append(b);}main.fgContent.append(rails);
  const gift=document.createElement('button');gift.className='sanguo-gift-entry';gift.dataset.action='milestone:open:noRank';gift.setAttribute('aria-label','活动奖励');gift.append(this.image(7));main.fgContent.append(gift);
  const bell=document.createElement('button');bell.className='sanguo-bell-entry';bell.dataset.action='report';bell.setAttribute('aria-label','棋盘消息');const bellIcon=document.createElement('img');bellIcon.src=ROOT+'notification-bell-v8.png';bellIcon.className='sanguo-ui-icon';bellIcon.alt='';bell.append(bellIcon);main.fgContent.append(bell);
  // Paint top resource icons over the published skin without changing its resizing logic.
  for(const [path,index]of [['topMoeny',0],['topKbMini',1],['topShield',2]]){const n=ui.find(main,'com_topBar/'+path);if(!n)continue;for(const child of n.querySelectorAll('[data-name="icon"],[data-name="icon_money"],[data-name="n6"]'))ui.setImage(child,this.icons[index]);}
 }
}

