import fs from 'node:fs/promises';import path from 'node:path';import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');const dist=path.join(root,'dist');
const nativeRules=JSON.parse(await fs.readFile(path.join(root,'assets/board-rules.json'),'utf8'));await fs.writeFile(path.join(root,'src/native-rules.mjs'),'export default '+JSON.stringify(nativeRules)+';\n');
const files=['index.html','style.css','sanguo-ui.css','construction.css','game-data.js','fgui-data.js'];
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

const constructionUI=JSON.parse(await fs.readFile(path.join(dist,'assets/construction/ui.json'),'utf8'));
for(const name of ['TaskDailog','TransitionRestDecorSelectPopUp'])if(!constructionUI.prefabs[name])throw Error('缺少原建设UI '+name);
for(const item of [...Object.values(constructionUI.sprites),...Object.values(constructionUI.fonts)])await fs.access(path.join(dist,item.url));
if(!constructionUI.animationEndStates?.TaskDailog?.nodes)throw Error('缺少原任务书打开状态');
const constructionScene=JSON.parse(await fs.readFile(path.join(dist,'assets/construction/scene.json'),'utf8'));
for(const item of Object.values(constructionScene.sprites))await fs.access(path.join(dist,'assets/construction',item.url));
await fs.access(path.join(dist,'assets/construction/portraits/npc_1016-preview.png'));
const constructionHammer=JSON.parse(await fs.readFile(path.join(dist,'assets/construction/hammer.json'),'utf8'));
for(const item of Object.values(constructionHammer.sprites))await fs.access(path.join(dist,item.url));
console.log(`建设原资源检查通过：${Object.keys(constructionScene.sprites).length}张场景切图、${Object.keys(constructionUI.sprites).length}张UI切图`);

const sourceStory=JSON.parse(await fs.readFile(path.join(dist,'assets/construction/story-ui.json'),'utf8'));
for(const item of [...Object.values(sourceStory.sprites),...Object.values(sourceStory.fonts),...Object.values(sourceStory.textures)])if(item.url)await fs.access(path.join(dist,item.url));
let originalRoles=0;for(const folder of['portraits','scene-npcs']){const meta=JSON.parse(await fs.readFile(path.join(dist,'assets/construction',folder,folder==='portraits'?'npc-animations.json':'animations.json'),'utf8'));for(const[name,role]of Object.entries(meta.roles)){const base=path.join(dist,'assets/construction',folder);if(role.kind==='static')await fs.access(path.join(base,role.image.url));else{await fs.access(path.join(base,role.binaryUrl||name+'.skel'));const atlas=path.join(base,role.atlasUrl||name+'.atlas');const text=await fs.readFile(atlas,'utf8');for(const page of text.matchAll(/(?:^|\n\n)([^\r\n]+\.png)\r?\nsize:/g))await fs.access(path.join(path.dirname(atlas),page[1]));}originalRoles++;}}
for(const file of['config/Data/Common/MainQuestVo.json','config/Common/PlayerExp.json','plot-plans/manifest.json','story-effects.json','fog.json','task-content.json','newlook.json'])await fs.access(path.join(dist,'assets/construction',file));
const sourceEffects=JSON.parse(await fs.readFile(path.join(dist,'assets/construction/story-effects.json'),'utf8'));
for(const item of[...Object.values(sourceEffects.cg||{}),...Object.values(sourceEffects.bg||{}),...Object.values(sourceEffects.sounds||{})])if(item.available&&item.url)await fs.access(path.join(dist,'assets/construction',item.url));
console.log(`建设剧情/等级/长按/人物资源检查通过：${originalRoles}种原人物，${Object.keys(sourceStory.prefabs).length}套剧情与状态栏组件`);

const constructionRoot=path.join(dist,'assets/construction');
let constructionChunks=0;
for(const name of['scene-runtime.json','environment-runtime.json']){
 const data=JSON.parse(await fs.readFile(path.join(constructionRoot,name),'utf8'));
 for(const file of Object.values(data.prefabFiles||{})){await fs.access(path.join(constructionRoot,file.url));constructionChunks++;}
 for(const image of Object.values(data.textures||{}))await fs.access(path.join(constructionRoot,image.url));
}
for(const name of['newlook.json','unitfx-star.json','unitfx-dust.json','unitfx-fire-clean.json','unitfx-wind-clean.json','unitfx-star-clean.json','unitfx-dust-clean.json']){
 const data=JSON.parse(await fs.readFile(path.join(constructionRoot,name),'utf8'));
 for(const group of['sprites','particleTextures'])for(const image of Object.values(data[group]||{}))if(image.url)await fs.access(path.join(image.url.startsWith('assets/')?dist:constructionRoot,image.url));
}
const unitTimelines=JSON.parse(await fs.readFile(path.join(constructionRoot,'unit-timelines.json'),'utf8'));
if(unitTimelines.version!=='1.4.93.1'||unitTimelines.missingDependencies?.length)throw Error('后期建设Timeline版本或依赖不一致');
await fs.access(path.join(constructionRoot,'config/Data/Map/world_1/MapParamVo.json'));
console.log(`建设分片/环境/施工/后期动画检查通过：${constructionChunks}份运行分片`);

const tavernSkin=JSON.parse(await fs.readFile(path.join(constructionRoot,'skins/jiangdong-c/skin.json'),'utf8'));
if(!tavernSkin.enabled||tavernSkin.pendingGroups.length||tavernSkin.pendingExtras.length||Object.keys(tavernSkin.sprites).length!==177||tavernSkin.extras.length!==103||Object.keys(tavernSkin.roles).length!==17)throw Error('江东C版前十步美术未完整接入');
const {createHash}=await import('node:crypto');
for(const replacement of new Set(Object.values(tavernSkin.files)))await fs.access(path.join(dist,replacement));
for(const record of [...Object.values(tavernSkin.sprites).map(r=>({...r,url:'assets/construction/'+r.url})),...tavernSkin.extras]){const bytes=await fs.readFile(path.join(dist,record.url));if(createHash('sha256').update(bytes).digest('hex')!==record.sha256)throw Error('江东C版美术校验失败：'+record.url);}
for(const role of Object.values(tavernSkin.roles))if(role.atlasURL){const atlas=path.join(dist,role.atlasURL),text=await fs.readFile(atlas,'utf8');for(const page of text.matchAll(/(?:^|\n\n)([^\r\n]+\.png)\r?\nsize:/g))await fs.access(path.join(path.dirname(atlas),page[1]));}else if(role.imageURL)await fs.access(path.join(dist,role.imageURL));
console.log('江东C版检查通过：177张场景、103张界面/奖励/剧情/施工素材、17个人物配置');

const {INK_ASSETS}=await import('../src/ink-environment.mjs');for(const url of INK_ASSETS)await fs.access(path.join(dist,url));console.log('Watercolor scene panels and transparent cast assets verified');
const residents=JSON.parse(await fs.readFile(path.join(dist,'assets/scene/skins/ink/residents-v4.json'),'utf8'));
const residentFrames=Object.values(residents.atlases).reduce((sum,a)=>sum+a.frames.length,0);
if(residentFrames!==38)throw Error('市集居民动作数量不完整');
for(const atlas of Object.values(residents.atlases))await fs.access(path.join(dist,'assets/scene/skins/ink',atlas.url));
console.log(`市集人物循环动作资源检查通过：${residentFrames}帧`);
const seedanceSweeper=JSON.parse(await fs.readFile(path.join(dist,'assets/scene/skins/ink/residents-seedance-sweeper-v1.json'),'utf8'));
for(const[key,count]of[['sweeperSweep',20],['sweeperWalk',24]]){const clip=seedanceSweeper.atlases[key];if(clip?.frames.length!==count||!(clip.fps>0))throw Error('扫地人Seedance序列不完整：'+key);await fs.access(path.join(dist,'assets/scene/skins/ink',clip.url));}
console.log('原扫地角色Seedance动作检查通过：扫地20帧、走路24帧');

// Provenance stays in source control; only the extracted runtime panels ship.
for(const name of ['source-master.png','source-clean-v3.png','source-clean-hd-v1.png','scene-hd-v1.prompts.json','villagers-v3.prompts.txt','residents-v4.prompts.md','source.json','cast-watercolor-v2.prompt.txt','cast-watercolor-v2.png','north-courtyard.png','market-square.png','south-market.png','market-ground-v1.png','market-ground-v1.prompt.txt','market-ground-v1.source.json'])await fs.rm(path.join(dist,'assets/scene/skins/ink',name),{force:true});

const {ZHANGNING_ASSETS}=await import('../src/zhangning-art.mjs');for(const url of ZHANGNING_ASSETS)await fs.access(path.join(dist,url));console.log('张宁三版角色/头像素材检查通过');
