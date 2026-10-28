const DATA = window.FGUI_DATA;
const vec=(s,fallback=[0,0]) => typeof s === 'string' ? s.split(',').map(Number) : fallback;
const color=value => value?.length === 9 ? '#'+value.slice(3) : value;
export class OriginalUI {
  constructor() {this.data=DATA;this.images=new Map();for(const [pkg,p] of Object.entries(DATA.packages))for(const [id,item] of Object.entries(p.items))if(item.url)this.images.set(item.name,{...item,pkg,id});}
  resource(pkg,id) {return DATA.packages[pkg]?.items[id];}
  url(value) {if(!value?.startsWith('ui://'))return null;return this.resource(value.slice(5,13),value.slice(13));}
  image(name) {return this.images.get(name)?.url || '';}
  ref(name) {return DATA.roots[name];}
  create(name,options={}) {const ref=this.ref(name);if(!ref)throw new Error('缺少原UI组件：'+name);return this.component(ref.pkg,ref.id,options);}
  component(pkg,id,options={},depth=0) {
    if(depth>16)return document.createElement('div');
    const resource=this.resource(pkg,id);const outer=document.createElement('div');outer.className='fg-node fg-component';outer.dataset.pkg=pkg;outer.dataset.resource=id;
    const width=resource?.width || 0,height=resource?.height || 0;outer.style.width=width+'px';outer.style.height=height+'px';
    if(!resource?.xml)return outer;
    const root=resource.xml;const control={};
    for(const c of root.children.filter(c=>c.tag==='controller')){const pages=(c.attrs.pages || '0,').split(',');control[c.attrs.name]=pages[Number(c.attrs.selected || 0)*2] || pages[0] || '0';}
    Object.assign(control,options.controllers || {});outer.fgControls=control;
    const content=document.createElement('div');content.className='fg-content';content.style.width=width+'px';content.style.height=height+'px';outer.append(content);outer.fgContent=content;if(root.attrs.mask){content.style.borderRadius='50%';content.style.overflow='hidden';}
    const display=root.children.find(c=>c.tag==='displayList');
    if(!display)return outer;
    const groups=new Map(display.children.filter(n=>n.tag==='group').map(n=>[n.attrs.id,n]));
    const visible=node=>{
      if(node.attrs.visible==='false'||Number(node.attrs.alpha ?? 1)<=0)return false;
      for(const g of node.children.filter(c=>c.tag==='gearDisplay'))if(g.attrs.pages!==undefined && g.attrs.pages!=='' && !g.attrs.pages.split(',').includes(control[g.attrs.controller]))return false;
      const group=groups.get(node.attrs.group);return !group || visible(group);
    };
    for(const node of display.children){
      if(node.tag==='group'||!visible(node))continue;
      const a={...node.attrs};
      for(const gear of node.children){const ga=gear.attrs;if(!ga.controller || !['gearXY','gearSize','gearText','gearIcon','gearColor','gearFontSize'].includes(gear.tag))continue;const pages=(ga.pages || '').split(',');const index=pages.indexOf(control[ga.controller]);const values=(ga.values || '').split('|');const value=index>=0 ? values[index] : ga.default;
        if(value===undefined)continue;
        if(gear.tag==='gearXY')a.xy=value;
        if(gear.tag==='gearSize'){const v=vec(value);a.size=v.slice(0,2).join(',');if(v.length>2)a.scale=v.slice(2,4).join(',');}
        if(gear.tag==='gearText')a.text=value;if(gear.tag==='gearIcon')a.url=value;if(gear.tag==='gearFontSize')a.fontSize=value;if(gear.tag==='gearColor')a.color=value.split(',')[0];
      }
      let el;let res=null;
      if(node.tag==='component'){
        const childPkg=a.pkg || pkg;el=this.component(childPkg,a.src,{controllers:this.parseControllers(a.controller)},depth+1);res=this.resource(childPkg,a.src);
      }else{el=document.createElement('div');el.className='fg-node fg-'+node.tag;}
      el.dataset.name=a.name || '';el.dataset.node=a.id || '';el.fgAttrs=a;
      let [w,h]=vec(a.size,[res?.width || 0,res?.height || 0]);
      if(node.tag==='image'||node.tag==='loader'){
        res=node.tag==='image'?this.resource(a.pkg || pkg,a.src):this.url(a.url);
        if(!a.size){w=res?.width || w;h=res?.height || h;}
        this.setImage(el,res?.url || '',res,a.fill==='scale'||a.fill==='scaleFree'||a.aspect==='true');
      }
      if(node.tag==='text'||node.tag==='richtext'||node.tag==='inputtext'){
        el.textContent=(a.text || '').replace(/\[\/?[^\]]+\]/g,'');el.style.fontSize=(Number(a.fontSize)||24)+'px';el.style.color=color(a.color)||'#fff';el.style.fontWeight=a.bold==='true'?'bold':'600';el.style.textAlign=a.align || 'left';el.style.alignItems=a.vAlign==='middle'?'center':a.vAlign==='bottom'?'flex-end':'flex-start';el.style.justifyContent=a.align==='center'?'center':a.align==='right'?'flex-end':'flex-start';el.style.whiteSpace=a.singleLine==='true'?'nowrap':'pre-wrap';
        if(a.strokeColor)el.style.textShadow=`-1px -1px 0 ${color(a.strokeColor)},1px -1px 0 ${color(a.strokeColor)},-1px 1px 0 ${color(a.strokeColor)},1px 1px 0 ${color(a.strokeColor)}`;
      }
      if(node.tag==='graph'&&a.type==='rect'){el.style.background=color(a.fillColor)||'transparent';el.style.borderRadius=(a.corner?vec(a.corner)[0]:0)+'px';}
      const [x,y]=vec(a.xy),[px,py]=vec(a.pivot),[sx,sy]=vec(a.scale,[1,1]);const anchor=a.anchor==='true';
      el.style.left=(x-(anchor?px*w:0))+'px';el.style.top=(y-(anchor?py*h:0))+'px';el.style.width=w+'px';el.style.height=h+'px';el.style.opacity=a.alpha ?? '1';
      if(el.fgContent && res && (w!==res.width || h!==res.height))el.fgContent.style.transform=`scale(${w/res.width || 1},${h/res.height || 1})`;
      if(sx!==1||sy!==1||a.rotation){el.style.transform=`rotate(${a.rotation || 0}deg) scale(${sx},${sy})`;el.style.transformOrigin=`${px*100}% ${py*100}%`;}
      if(a.touchable==='false')el.style.pointerEvents='none';content.append(el);
      const label=node.children.find(c=>['Label','Button'].includes(c.tag));
      if(label){if(label.attrs.title!==undefined)this.text(el,'title',label.attrs.title);if(label.attrs.icon){const icon=this.find(el,'icon');if(icon)this.setImage(icon,this.url(label.attrs.icon)?.url);}}
    }
    return outer;
  }
  parseControllers(value) {const result={};if(value){const values=value.split(',');for(let i=0;i+1<values.length;i+=2)result[values[i]]=values[i+1];}return result;}
  find(root,path){let node=root;for(const name of path.split('/')){const direct=node?.fgContent ? [...node.fgContent.children].find(el=>el.dataset.name===name) : null;node=direct || node?.querySelector(`[data-name="${CSS.escape(name)}"]`);if(!node)return null;}return node;}
  text(root,path,value){const node=this.find(root,path);if(node)node.textContent=String(value);return node;}
  hide(root,path){const node=this.find(root,path);if(node)node.style.display='none';}
  setImage(el,url,res=null,contain=true){if(!el)return;el.replaceChildren();if(!url)return;if(res?.scale==='9grid' && res.scale9grid){const [l,t,w,h]=res.scale9grid;const right=Math.max(0,res.width-l-w),bottom=Math.max(0,res.height-t-h);el.style.borderStyle='solid';el.style.borderWidth=`${t}px ${right}px ${bottom}px ${l}px`;el.style.borderImageSource=`url("${url}")`;el.style.borderImageSlice=`${t} ${right} ${bottom} ${l} fill`;el.style.borderImageRepeat='stretch';return;}const img=document.createElement('img');img.src=url;img.alt='';img.draggable=false;img.style.width='100%';img.style.height='100%';img.style.objectFit=contain?'contain':'fill';el.append(img);}
  action(root,path,name,aria){const node=this.find(root,path);if(node){node.dataset.action=name;node.style.pointerEvents='auto';node.style.cursor='pointer';node.setAttribute('role','button');node.tabIndex=0;node.setAttribute('aria-label',aria || name);}return node;}
}