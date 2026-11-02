import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {normalizeNativeDialogue} from '../src/construction-native-plot.mjs';
import {preflightConstructionStoryEffects} from '../src/construction-story-effects.mjs';
const root=path.resolve(import.meta.dirname,'..'),assets=path.join(root,'assets/construction'),config=path.join(assets,'config/Data/Plot/Main');
const read=async file=>JSON.parse(await fs.readFile(file,'utf8')),data=await read(path.join(assets,'story-effects.json'));
const stages=(await fs.readdir(config)).filter(name=>/^stage_\d+$/.test(name)).sort((a,b)=>Number(a.slice(6))-Number(b.slice(6)));
const plotTypes={},effectCounts={},effectParams={},cases=[],stageResults=[];let narrationIgnored=0;
for(const stage of stages){
 const plots=(await read(path.join(config,stage,'PlotVo.json'))).rows,dialogues=(await read(path.join(config,stage,'PlotDialogueVo.json'))).rows.map(normalizeNativeDialogue),referencedGroups=new Set(plots.filter(row=>Number(row.plotType)===1).map(row=>String(row.performId)));
 for(const row of plots)plotTypes[row.plotType]=(plotTypes[row.plotType]||0)+1;
 for(const row of dialogues){
  if(!referencedGroups.has(String(row.groupId)))continue;
  for(const phase of ['Before','On'])for(const effect of row['effects'+phase]){
   if(Number(row.type)===3){narrationIgnored++;continue;}
   effectCounts[effect.type]=(effectCounts[effect.type]||0)+1;
   (effectParams[effect.type]||=new Set()).add(String(effect.params));
   cases.push({stage,rowId:row.id,phase,...effect});
  }
 }
 const groups=new Map();for(const row of dialogues){const key=String(row.groupId);if(!groups.has(key))groups.set(key,[]);groups.get(key).push(row);}
 const plan={steps:plots.map(row=>({...row,type:row.plotType,stepId:row.id,rows:groups.get(String(row.performId))||[]}))};
 stageResults.push({stage,...preflightConstructionStoryEffects(data,plan)});
}
const resources=[];
for(const[kind,collection]of Object.entries({CG:data.cg,BG:data.bg,SpineFX:data.fx,Sound:data.sounds}))for(const[id,asset]of Object.entries(collection))resources.push({kind,id:Number(id),path:asset.cgPath??asset.bgPath??asset.fxPath??asset.soundPath,available:!!asset.available,sha256:asset.sha256??asset.files,source:asset.source??asset.sources});
const files=[];for(const collection of [data.cg,data.bg,data.sounds])for(const asset of Object.values(collection))if(asset.available)files.push({url:asset.url,sha256:asset.sha256});
for(const fx of Object.values(data.fx))if(fx.available)for(const[url,sha256]of Object.entries(fx.files))files.push({url:'story-fx/'+url,sha256});
files.push({url:data.memory.shaderUrl,sha256:data.memory.shaderSha256});
const artifactCheck={checked:0,totalBytes:0,missing:[],hashMismatch:[]};
for(const file of files){let bytes;try{bytes=await fs.readFile(path.join(assets,file.url));}catch(error){if(error.code!=='ENOENT')throw error;artifactCheck.missing.push(file.url);continue;}artifactCheck.checked++;artifactCheck.totalBytes+=bytes.length;if(crypto.createHash('sha256').update(bytes).digest('hex')!==file.sha256)artifactCheck.hashMismatch.push(file.url);}
artifactCheck.ok=!artifactCheck.missing.length&&!artifactCheck.hashMismatch.length;
const result={catalog:data.catalog,stages:stages.length,plotTypes,effectCounts,effectParams:Object.fromEntries(Object.entries(effectParams).map(([id,params])=>[id,[...params].sort()])),narrationIgnored,resources,artifactCheck,preflight:{ok:stageResults.every(stage=>stage.ok),missing:stageResults.flatMap(stage=>stage.missing.map(row=>({stage:stage.stage,...row}))),warnings:stageResults.flatMap(stage=>stage.warnings.map(row=>({stage:stage.stage,...row})))},cases};
await fs.writeFile(path.join(assets,'story-effect-coverage.json'),JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify({stages:result.stages,plotTypes,effectCounts,narrationIgnored,resourceAvailable:resources.filter(row=>row.available).length,unusedMissing:resources.filter(row=>!row.available).map(row=>({kind:row.kind,id:row.id})),artifactCheck,preflight:result.preflight}));
if(!artifactCheck.ok||!result.preflight.ok)process.exitCode=1;
