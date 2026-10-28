import fs from 'node:fs/promises';import path from 'node:path';import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');const dist=path.join(root,'dist');
const files=['index.html','style.css','game-data.js','fgui-data.js'];
await fs.mkdir(dist,{recursive:true});
for(const name of files)await fs.copyFile(path.join(root,name),path.join(dist,name));
for(const name of ['src','assets','vendor'])await fs.cp(path.join(root,name),path.join(dist,name),{recursive:true,filter:source=>!source.endsWith('_parts_preview.jpg')});
const sandbox={window:{}};const {default:vm}=await import('node:vm');vm.runInNewContext(await fs.readFile(path.join(root,'fgui-data.js'),'utf8'),sandbox);
let checked=0;for(const pkg of Object.values(sandbox.window.FGUI_DATA.packages))for(const item of Object.values(pkg.items))if(item.url){await fs.access(path.join(dist,item.url));checked++;}
const prefabs=JSON.parse(await fs.readFile(path.join(dist,'assets/scene/grid-prefabs.json'),'utf8'));if(Object.keys(prefabs.prefabs).length!==40)throw new Error('原棋盘格子数量错误');
console.log(`构建通过：40格原布局，${checked}个原UI素材地址，输出 ${dist}`);