import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {SanguoEnvironment} from '../src/sanguo-environment.mjs';

const original=JSON.parse(fs.readFileSync(new URL('../assets/scene/grid-meshes.json',import.meta.url),'utf8'));
const prefabs=JSON.parse(fs.readFileSync(new URL('../assets/scene/grid-prefabs.json',import.meta.url),'utf8')).prefabs;
function themed(){const owner={scene:{meshes:structuredClone(original)},removedEars:{}};SanguoEnvironment.prototype.prepareMeshes.call(owner);return owner.scene.meshes;}
function bounds(mesh,matrix=null){
 const points=[];
 for(let i=0;i<mesh.positions.length;i+=3){const[x,y,z]=mesh.positions.slice(i,i+3);points.push(matrix?[matrix[0]*x+matrix[4]*y+matrix[8]*z+matrix[12],matrix[2]*x+matrix[6]*y+matrix[10]*z+matrix[14]]:[x,z]);}
 return [Math.min(...points.map(p=>p[0])),Math.max(...points.map(p=>p[0])),Math.min(...points.map(p=>p[1])),Math.max(...points.map(p=>p[1]))];
}
const close=(a,b,message)=>a.forEach((n,i)=>assert(Math.abs(n-b[i])<1e-6,message+': '+JSON.stringify({actual:a,expected:b})));

test('all four replacement tiles retain the native footprint and orientation',()=>{
 const meshes=themed();
 for(const id of ['6','16','26','36']){const name=prefabs[id].meshName;close(bounds(meshes[name]),bounds(original[name]),'tile '+id);}
});

test('themed tiles introduce no extra overlap between any pair of forty slots',()=>{
 const meshes=themed(),slots=Object.values(prefabs);
 const worldBounds=(p,set)=>{const m=[...p.modelMatrix];m[12]+=p.instanceMatrix[12];m[13]+=p.instanceMatrix[13];m[14]+=p.instanceMatrix[14];return bounds(set[p.meshName],m);};
 const overlap=(a,b)=>Math.max(0,Math.min(a[1],b[1])-Math.max(a[0],b[0]))*Math.max(0,Math.min(a[3],b[3])-Math.max(a[2],b[2]));
 for(let i=0;i<slots.length;i++)for(let j=i+1;j<slots.length;j++){
  const a=slots[i],b=slots[j],native=overlap(worldBounds(a,original),worldBounds(b,original)),skin=overlap(worldBounds(a,meshes),worldBounds(b,meshes));
  assert(skin<=native+1e-6,'new overlap at slots '+a.id+'/'+b.id+': '+skin+' > '+native);
 }
});
