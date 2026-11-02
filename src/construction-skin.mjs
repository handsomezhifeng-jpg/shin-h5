const BASE=new URL('../',import.meta.url),MANIFEST=new URL('../assets/construction/skins/jiangdong-c/skin.json',import.meta.url);
let active=null,pending;
const mode=()=>new URLSearchParams(globalThis.location?.search||'').get('constructionSkin');
export async function loadConstructionSkin(){
 if(mode()==='original')return null;
 return pending??=(async()=>{const r=await fetch(MANIFEST);if(!r.ok)throw Error('江东酒楼美术清单读取失败');const data=await r.json();if(data.enabled||mode()==='jiangdong-c')active=data;return active;})();
}
export function constructionSkin(){return active;}
export function resolveConstructionArtURL(url){
 if(typeof url!=='string'||!active)return url;
 let key=url;try{const parsed=new URL(url,BASE);key=parsed.origin===BASE.origin&&parsed.pathname.startsWith(BASE.pathname)?parsed.pathname.slice(BASE.pathname.length):parsed.pathname.replace(/^\//,'');}catch{}
 const replacement=active.files?.[key];return replacement?new URL(replacement,BASE).href:url;
}
export function patchConstructionSceneData(data){
 if(!active)return data;
 const sprites={...data.sprites};for(const[id,record]of Object.entries(active.sprites||{}))if(sprites[id])sprites[id]={...sprites[id],url:record.url,skinSource:record.sourceURL};
 return{...data,sprites,artSkin:active.id,artPalette:active.palette};
}
export function patchConstructionPack(data,root='assets/construction/'){
 if(!active||!data||typeof data!=='object')return data;
 const visit=value=>{if(Array.isArray(value))return value.map(visit);if(!value||typeof value!=='object')return value;const out={};for(const[k,v]of Object.entries(value)){if(['url','icon'].includes(k)&&typeof v==='string'){const candidate=/^(?:https?:|data:|blob:|\/|assets\/)/.test(v)?v:root+v,replacement=resolveConstructionArtURL(candidate);out[k]=replacement!==candidate?replacement:v;}else out[k]=visit(v);}return out;};
 return visit(data);
}
export function patchConstructionRoles(data,root){
 if(!active)return data;
 const roles={...data.roles};for(const[key,record]of Object.entries(active.roles||{}))if(roles[key])roles[key]={...roles[key],...(record.atlasURL?{atlasUrl:new URL(record.atlasURL,BASE).href}:{}),...(record.imageURL?{image:{...roles[key].image,url:new URL(record.imageURL,BASE).href}}:{}),artSkin:active.id};
 return{...data,roles};
}
