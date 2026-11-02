const ROOT='assets/scene/skins/zhangning/';
export const ZHANGNING_ASSETS=['variants.json',...['a','b','c'].flatMap(k=>[k+'.webp',k+'-portrait.png'])].map(n=>ROOT+n);
export function zhangNingVariant(search=typeof location==='undefined'?'':location.search){const key=new URLSearchParams(search).get('hero')?.replace(/^zhangning-/,'').toLowerCase();return ['a','b','c'].includes(key)?key:'a';}
let selectedPromise;
export function loadZhangNing(){return selectedPromise??=(async()=>{
 const response=await fetch(ROOT+'variants.json');if(!response.ok)throw Error('张宁角色清单加载失败');const manifest=await response.json(),key=zhangNingVariant(),variant=manifest.variants[key];
 const atlas=await new Promise((resolve,reject)=>{const i=new Image();i.onload=()=>resolve(i);i.onerror=()=>reject(Error('张宁角色贴图加载失败'));i.src=ROOT+variant.atlas;});
 const poses=variant.frames.map(record=>{const [x,y,w,h]=record.crop,canvas=document.createElement('canvas');canvas.width=w;canvas.height=h;canvas.getContext('2d').drawImage(atlas,x,y,w,h,0,0,w,h);return {...record,canvas};});
 return {key,name:variant.name,poses,frames:[poses[0],poses[2],poses[0],poses[2],poses[1],poses[3],poses[1],poses[3]],portraitURL:ROOT+variant.portrait};
})();}
