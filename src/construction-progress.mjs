export const CONSTRUCTION_BUILDINGS=[
 {unit:'0_11749',name:'茶摊',x:-5.1,y:-8.5},
 {unit:'0_11753',name:'水果摊',x:-7.1,y:-8.1},
 {unit:'0_11754',name:'甜品摊',x:-8.5,y:-8.8},
 {unit:'0_13009',linkedUnits:['0_11833'],name:'庭院',x:-5.1,y:-12.0},
 {unit:'0_13010',linkedUnits:['0_10879'],name:'门庭桌伞',x:-4.0,y:-10.6}
];
// The imported scene and decoration flow use the host game's existing building economy.
// Source-game encrypted story tasks are not treated as recovered configuration.
export class ConstructionProgress{
 constructor(engine){this.engine=engine;this.restore();}
 restore(){const s=this.engine.state;if(!s.construction||s.construction.version!==1||!s.construction.maps||typeof s.construction.maps!=='object'||Array.isArray(s.construction.maps))s.construction={version:1,maps:{}};const key=String(s.map);let m=s.construction.maps[key];if(!m||typeof m!=='object'||Array.isArray(m))m=s.construction.maps[key]={skins:{}};if(!m.skins||typeof m.skins!=='object'||Array.isArray(m.skins))m.skins={};for(const b of CONSTRUCTION_BUILDINGS)if(![1,2,3].includes(m.skins[b.unit]))delete m.skins[b.unit];return m;}
 get map(){return this.restore();}
 get next(){const i=this.engine.state.buildings.findIndex(b=>b.damaged||b.level<this.engine.maxBuildLevel);return i<0?null:i;}
 skin(index){const b=CONSTRUCTION_BUILDINGS[index],state=this.engine.state.buildings[index];return state.level&&!state.damaged?this.map.skins[b.unit]||1:0;}
 scene(preview=null){const skins={};for(const[b,i]of CONSTRUCTION_BUILDINGS.map((b,i)=>[b,i]))for(const unit of[b.unit,...b.linkedUnits||[]])skins[unit]=this.skin(i);if(preview){const b=CONSTRUCTION_BUILDINGS[preview.index];for(const unit of[b.unit,...b.linkedUnits||[]])skins[unit]=preview.skin;}return{skins};}
 commit(index,skin){if(!Number.isInteger(index)||index<0||index>=5||![1,2,3].includes(skin))return{error:'请选择装修样式'};const result=this.engine.build(index);if(result.error)return result;this.map.skins[CONSTRUCTION_BUILDINGS[index].unit]=skin;return{...result,skin};}
}
