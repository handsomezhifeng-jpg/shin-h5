// RectTransforms and sprites come from the original Unity prefabs, in Unity UI units.
import{constructionSkin,patchConstructionPack,resolveConstructionArtURL}from './construction-skin.mjs';
const color=c=>c?`rgba(${Math.round(c.r*255)},${Math.round(c.g*255)},${Math.round(c.b*255)},${c.a})`:'#fff';
const esc=s=>String(s??'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const imageTints=new Map();let tintDefinitions;
function imageTint(c){if(!c||(c.r===1&&c.g===1&&c.b===1))return'none';const key=[c.r,c.g,c.b].join(',');if(imageTints.has(key))return`url(#${imageTints.get(key)})`;if(!tintDefinitions?.isConnected){tintDefinitions=document.createElementNS('http://www.w3.org/2000/svg','svg');tintDefinitions.setAttribute('aria-hidden','true');tintDefinitions.style.cssText='position:absolute;width:0;height:0;pointer-events:none';tintDefinitions.innerHTML='<defs></defs>';document.body.append(tintDefinitions);}const id='construction-source-tint-'+imageTints.size,filter=document.createElementNS('http://www.w3.org/2000/svg','filter'),matrix=document.createElementNS('http://www.w3.org/2000/svg','feColorMatrix');filter.id=id;filter.setAttribute('color-interpolation-filters','sRGB');matrix.setAttribute('type','matrix');matrix.setAttribute('values',`${c.r} 0 0 0 0 0 ${c.g} 0 0 0 0 0 ${c.b} 0 0 0 0 0 1 0`);filter.append(matrix);tintDefinitions.firstElementChild.append(filter);imageTints.set(key,id);return`url(#${id})`;}
export class ConstructionUnityUI {
 constructor(data){this.data=patchConstructionPack(data);this.byName=new Map(Object.entries(this.data.sprites).map(([key,v])=>[v.name,{key,...v}]));}
 sprite(name){const s=this.data.sprites[name]||this.byName.get(name);return s?{...s,url:resolveConstructionArtURL(s.url)}:s;}
 create(name,{width=1440,height=2560}={}){
  const prefab=this.data.prefabs[name];if(!prefab)throw new Error('缺少原建设界面 '+name);
  const nodes=new Map();
  const build=(n,pw,ph,root=false)=>{
   const el=document.createElement('div');el.className='construction-unity-node';el.dataset.unity=n.name;el.dataset.path=n.path;nodes.set(n.path,el);el.source=n;
   const end=this.data.animationEndStates?.[name]?.nodes?.[n.path],t={...(n.transform||{}),...(end?.transform||{})},min=t.m_AnchorMin||{x:.5,y:.5},max=t.m_AnchorMax||min,p=t.m_Pivot||{x:.5,y:.5},d=t.m_SizeDelta||{x:0,y:0},a=t.m_AnchoredPosition||{x:0,y:0},sc=t.m_LocalScale||{x:1,y:1},q=t.m_LocalRotation||{x:0,y:0,z:0,w:1},angle=2*Math.acos(Math.max(-1,Math.min(1,q.w)));
   const w=root?width:pw*(max.x-min.x)+d.x,h=root?height:ph*(max.y-min.y)+d.y;
   const x=root?0:pw*(min.x+(max.x-min.x)*p.x)+a.x-w*p.x,y=root?0:ph-(ph*(min.y+(max.y-min.y)*p.y)+a.y+h*(1-p.y));
   Object.assign(el.style,{left:x+'px',top:y+'px',width:Math.max(0,w)+'px',height:Math.max(0,h)+'px',transformOrigin:`${p.x*100}% ${(1-p.y)*100}%`,transform:`rotate3d(${q.x},${-q.y},${-q.z},${angle}rad) scale(${sc.x},${sc.y})`});
   if(end?.alpha!==undefined)el.style.opacity=end.alpha;
   el.hidden=(end?.active??n.active)===false;el.rect={x,y,w,h};
   for(const c of n.components||[]){
    const f=c.fields||{};
    if(c.script==='Image'&&c.m_Sprite){this.setImage(el,c.m_Sprite,f);}
    if(c.script==='Text'||c.script==='CustomText'||c.script==='TextMeshProUGUI'){
     const text=document.createElement('div');text.className='construction-unity-text';const fd=f.m_FontData||{},align=fd.m_Alignment??(c.script==='TextMeshProUGUI'?({1:0,2:1,4:2}[f.m_HorizontalAlignment]??1)+3*({256:0,512:1,1024:2}[f.m_VerticalAlignment]??1):4);
     Object.assign(text.style,{fontSize:(fd.m_FontSize||f.m_fontSize||48)+'px',fontFamily:this.data.fonts?.[c.font]?.name?.includes('title')?'ConstructionTitle':'ConstructionText',fontWeight:fd.m_FontStyle===1?'bold':'normal',color:color(f.m_fontColor||f.m_Color),textAlign:['left','center','right'][align%3]||'center',justifyContent:['flex-start','center','flex-end'][align%3]||'center',alignItems:['flex-start','center','flex-end'][Math.floor(align/3)]||'center'});
     text.innerHTML=esc(f.m_Text||f.m_text||'').replace(/\n/g,'<br>');el.append(text);el.textNode=text;
    }
    if(['RectMask2D','Mask','SoftMask'].includes(c.script))el.style.overflow='hidden';
    if(c.script==='UguiRichOutline'&&el.textNode){el.textNode.style.webkitTextStroke=`${Math.abs(f.m_EffectDistance?.x||1)}px ${color(f.m_EffectColor)}`;el.textNode.style.paintOrder='stroke fill';}
    if(c.script==='Shadow'&&el.textNode)el.textNode.style.textShadow=`${f.m_EffectDistance?.x||0}px ${-(f.m_EffectDistance?.y||0)}px ${color(f.m_EffectColor)}`;
   }
   for(const c of n.children||[])el.append(build(c,w,h));return el;
  };
  const el=build(prefab,width,height,true);el.classList.add('construction-unity-root');if(constructionSkin())el.dataset.artSkin=constructionSkin().id;
  const find=path=>nodes.get(path)||[...nodes.values()].find(n=>n.dataset.path.endsWith('/'+path));
  const reflowChildren=parent=>{for(const child of parent.children){if(!child.source)continue;const end=this.data.animationEndStates?.[name]?.nodes?.[child.source.path],t={...child.source.transform,...end?.transform},min=t.m_AnchorMin||{x:.5,y:.5},max=t.m_AnchorMax||min,p=t.m_Pivot||{x:.5,y:.5},a=t.m_AnchoredPosition||{x:0,y:0},d=t.m_SizeDelta||{x:0,y:0},pw=parent.rect.w,ph=parent.rect.h,w=child.preferredBaseRect?child.rect.w:pw*(max.x-min.x)+d.x,h=ph*(max.y-min.y)+d.y,x=pw*(min.x+(max.x-min.x)*p.x)+a.x-w*p.x,y=ph-(ph*(min.y+(max.y-min.y)*p.y)+a.y+h*(1-p.y));child.rect={x,y,w,h};Object.assign(child.style,{left:x+'px',top:y+'px',width:Math.max(0,w)+'px',height:Math.max(0,h)+'px'});reflowChildren(child);}};
  return{el,nodes,find,text:(path,value)=>{const n=find(path);if(n?.textNode){n.textNode.textContent=value;const fit=n.source.components.some(c=>c.script==='ContentSizeFitter'&&c.fields.m_HorizontalFit===2);if(n.rect.w===0||fit||n.preferredBaseRect){n.preferredBaseRect??={...n.rect};const size=parseFloat(n.textNode.style.fontSize),context=document.createElement('canvas').getContext('2d');context.font=`${n.textNode.style.fontWeight} ${size}px ${n.textNode.style.fontFamily}`;const w=Math.max(size,...String(value).split('\n').map(line=>context.measureText(line).width)),x=n.preferredBaseRect.x+(n.preferredBaseRect.w-w)*(n.source.transform?.m_Pivot?.x??.5);n.rect={...n.rect,x,w};n.style.width=w+'px';n.style.left=x+'px';reflowChildren(n);}}},show:(path,on=true)=>{const n=find(path);if(n)n.hidden=!on;},image:(path,name)=>{const n=find(path);if(n)this.setImage(n,name);},switch:(path,index)=>this.setSwitch(find(path),index),action:(path,action,label)=>{const n=find(path);if(n){n.dataset.action=action;n.classList.add('construction-unity-button');n.setAttribute('role','button');n.setAttribute('aria-label',label);n.tabIndex=0;}return n;}};
 }
 setSwitch(el,index){
  if(!el)return;for(const c of el.source.components||[]){const f=c.fields||{};
   if(c.script==='UISwitchImage'){const config=f.spriteConfigs?.[index-1],key=c.switchSprites?.[index-1];if(!config)continue;if(!config.disableSprite&&key){this.setImage(el,key);if(f.isNativeSize){const s=this.sprite(key),r=el.rect,p=el.source.transform?.m_Pivot||{x:.5,y:.5},w=s.width,h=s.height;el.style.left=(r.x+(r.w-w)*p.x)+'px';el.style.top=(r.y+(r.h-h)*(1-p.y))+'px';el.style.width=w+'px';el.style.height=h+'px';el.rect={...r,x:parseFloat(el.style.left),y:parseFloat(el.style.top),w,h};}}
    if(!config.disableColor){const graphic=el.querySelector(':scope > .construction-unity-image');if(graphic){graphic.style.filter=imageTint(config.color);graphic.style.opacity=String(config.color.a);}}if(config.enableLocalScale)el.style.transform=`scale(${config.localScale.x},${config.localScale.y})`;
   }else if(c.script==='UISwitchText'){const config=f.textConfigs?.[index-1],text=el.textNode;if(!config||!text)continue;if(!config.disableColor)text.style.color=color(config.color);if(!config.disableFontSize)text.style.fontSize=config.fontSize+'px';if(!config.disableText&&config.text)text.textContent=config.text;}
  }
 }
 setImage(el,key,fields){
  fields??=el.source?.components?.find(c=>c.script==='Image')?.fields||{};
  const s=this.sprite(key);if(!s)return false;let image=el.querySelector(':scope > .construction-unity-image');if(!image){image=document.createElement('div');image.className='construction-unity-image';el.prepend(image);}image.dataset.sprite=s.name;
  const b=s.border||{},sliced=fields.m_Type===1&&(b.x||b.y||b.z||b.w);
  if(sliced){Object.assign(image.style,{backgroundImage:'none',borderStyle:'solid',borderWidth:`${b.w}px ${b.z}px ${b.y}px ${b.x}px`,borderImageSource:`url("${s.url}")`,borderImageSlice:`${b.w} ${b.z} ${b.y} ${b.x} fill`,borderImageWidth:'1',boxSizing:'border-box'});}
  else Object.assign(image.style,{border:'0',backgroundImage:`url("${s.url}")`,backgroundSize:fields.m_PreserveAspect?'contain':'100% 100%'});
  image.style.filter=imageTint(fields.m_Color);image.style.opacity=String(fields.m_Color?.a??1);
  return true;
 }
}
