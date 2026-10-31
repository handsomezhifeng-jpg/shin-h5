import fs from 'node:fs/promises';import path from 'node:path';import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');const dist=path.join(root,'dist');
const nativeRules=JSON.parse(await fs.readFile(path.join(root,'assets/board-rules.json'),'utf8'));await fs.writeFile(path.join(root,'src/native-rules.mjs'),'export default '+JSON.stringify(nativeRules)+';\n');
const files=['index.html','style.css','sanguo-ui.css','game-data.js','fgui-data.js'];
await fs.mkdir(dist,{recursive:true});
for(const name of files)await fs.copyFile(path.join(root,name),path.join(dist,name));
for(const name of ['src','assets','vendor'])await fs.cp(path.join(root,name),path.join(dist,name),{recursive:true,filter:source=>!source.endsWith('_parts_preview.jpg')});
const sandbox={window:{}};const {default:vm}=await import('node:vm');vm.runInNewContext(await fs.readFile(path.join(root,'fgui-data.js'),'utf8'),sandbox);
// The original FGUI TTF and the main CSS font are byte-identical; ship one copy.
const duplicateFont='assets/ui/Common/qe9t1ke46ym.ttf',sharedFont='assets/fonts/NotoSansSCBold.ttf';
const [fgFont,mainFont]=await Promise.all([fs.readFile(path.join(root,duplicateFont)),fs.readFile(path.join(root,sharedFont))]);
if(fgFont.equals(mainFont)){for(const pkg of Object.values(sandbox.window.FGUI_DATA.packages))for(const item of Object.values(pkg.items))if(item.url===duplicateFont)item.url=sharedFont;await fs.writeFile(path.join(dist,'fgui-data.js'),'window.FGUI_DATA='+JSON.stringify(sandbox.window.FGUI_DATA)+';\n');await fs.unlink(path.join(dist,duplicateFont));}
let checked=0;for(const pkg of Object.values(sandbox.window.FGUI_DATA.packages))for(const item of Object.values(pkg.items))if(item.url){await fs.access(path.join(dist,item.url));checked++;}
const prefabs=JSON.parse(await fs.readFile(path.join(dist,'assets/scene/grid-prefabs.json'),'utf8'));if(Object.keys(prefabs.prefabs).length!==40)throw new Error('原棋盘格子数量错误');
const meshData=JSON.parse(await fs.readFile(path.join(dist,'assets/scene/grid-meshes.json'),'utf8'));for(const prefab of Object.values(prefabs.prefabs))if(!meshData[prefab.meshName])throw new Error('缺少原网格：'+prefab.meshName);
console.log(`构建通过：40格原布局，${checked}个原UI素材地址，输出 ${dist}`);
const milestone=JSON.parse(await fs.readFile(path.join(dist,'assets/scene/milestone/ui.json'),'utf8'));for(const key of ['dynamicImages','rewardImages','referenceSkinImages'])for(const item of Object.values(milestone[key] || {}))if(item.url)await fs.access(path.join(dist,item.url));await fs.access(path.join(dist,milestone.stringsURL));const activities=JSON.parse(await fs.readFile(path.join(dist,'assets/activities/config.json'),'utf8'));if(activities.activities.length<2||Object.values(activities.stages).some(rows=>rows.some(s=>!s.resolvedOfflineRewards.length||!s.resolvedNormalOfflineRewards.length)))throw new Error('活动原奖励解析不完整');

const characters=JSON.parse(await fs.readFile(path.join(dist,'assets/scene/board-characters.json'),'utf8'));for(const item of [...Object.values(characters.textures),...characters.localOpponentTextures])await fs.access(path.join(dist,item.url));if(Object.keys(characters.slots).length!==40)throw new Error('好友头像挂点数量不完整');const hooks=JSON.parse(await fs.readFile(path.join(dist,'assets/scene/grid-hooks.json'),'utf8'));for(const slot of Object.values(hooks.slots))if(slot.text?.settings&&!slot.text.rect.anchoredPosition)throw new Error('遗漏原格面文字锚定位置');

const gridProps=JSON.parse(await fs.readFile(path.join(dist,'assets/scene/grid-props.json'),'utf8'));if(Object.keys(gridProps.slots).length!==40)throw new Error('格上建筑清单未覆盖40格');for(const[id,slot]of Object.entries(gridProps.slots))for(const prop of slot.props){if(!gridProps.meshes[prop.mesh])throw new Error('缺少格上原建筑网格：'+id);for(const name of prop.materials){const mat=gridProps.materials[name];for(const t of Object.values(mat.textures || {}))if(t.texture)await fs.access(path.join(dist,gridProps.textures[t.texture].url));}}

for(const a of activities.activities){if(!milestone.packagingConfigs[a.skinId]||!milestone.dynamicImages[a.icon])throw new Error("排期缺少原美术："+a.id);const skin=milestone.packagingConfigs[a.skinId];for(const stem of(a.kind==='noRank'?[skin.noRankBg]:[skin.title,...skin.rankBg]))if(!milestone.dynamicImages[stem])throw new Error("排期缺少原海报："+a.id);}

const auditUI=JSON.parse(await fs.readFile(path.join(dist,'assets/scene/audit-ui.json'),'utf8'));for(const url of Object.values(auditUI.images))await fs.access(path.join(dist,url));const prison=JSON.parse(await fs.readFile(path.join(dist,'assets/scene/prison-prop.json'),'utf8'));if(prison.objects.length!==2)throw new Error('原监狱笼子渲染器不完整');for(const t of Object.values(prison.textures))await fs.access(path.join(dist,t.url));for(const key of ['ani_mesh_cage_01_into','ani_mesh_cage_01_out','ani_caju_into','ani_caju_out'])if(!prison.clips[key])throw new Error('缺少原监狱动画：'+key);

const mainReference=JSON.parse(await fs.readFile(path.join(dist,'assets/ui/reference-main/ui.json'),'utf8')).referenceUI.main;let referenceImages=0;for(const pkg of Object.values(mainReference.packages))for(const item of Object.values(pkg.items))if(item.url){await fs.access(path.join(dist,item.url));referenceImages++;}for(const name of ['MainWindow','Top_Bar','Main_Big_Button','MainSideBarWindow']){const ref=mainReference.roots[name];if(!ref||!mainReference.packages[ref.pkg]?.items[ref.id]?.xml)throw new Error('缺少原发布主UI组件：'+name);}console.log(`原发布主UI检查通过：${referenceImages}个素材地址`);

const {BOARD_SKIN}=await import('../src/board-skin.mjs');for(const url of new Set(Object.values(BOARD_SKIN.textures)))await fs.access(path.join(dist,url));console.log('棋盘三国贴图地址检查通过');

const {SANGUO_ENVIRONMENT_ASSETS}=await import('../src/sanguo-environment.mjs');for(const url of SANGUO_ENVIRONMENT_ASSETS)await fs.access(path.join(dist,url));console.log('三国场景地面/建筑资源检查通过');

const {SANGUO_CAST_ASSETS}=await import('../src/sanguo-cast.mjs');for(const url of SANGUO_CAST_ASSETS)await fs.access(path.join(dist,url));console.log('三国主公/周边人物与头像资源检查通过');
const {SANGUO_UI_ASSETS}=await import('../src/sanguo-ui.mjs');for(const url of SANGUO_UI_ASSETS)await fs.access(path.join(dist,url));console.log('三国主界面与事件窗口换肤资源检查通过');
