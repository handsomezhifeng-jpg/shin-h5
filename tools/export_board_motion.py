from pathlib import Path
import json,re,math
# Reuse tested original-bundle and transform helpers without re-exporting images.
helper=Path(__file__).with_name('inspect_board_scene.py').read_text(encoding='utf8').split('slots={};issues=[];font_names=set()')[0]
exec(compile(helper,'board helpers','exec'))
ANIMS=ROOT/'client/SHIN/Assets/Art/UI_Effect/EF_Animations'
def numeric(s):
 if s.startswith('{'):return {k:float(v) for k,v in re.findall(r'(\w+):\s*([-+\d.eE]+)',s)}
 try:
  v=float(s)
  return v if math.isfinite(v) else s
 except:return s

def curve_list(s,section):
 found=re.search(r'^  '+section+r':[^\n]*\n(.*?)(?=^  \w+:|\Z)',s,re.S|re.M)
 if not found:return []
 result=[]
 for block in re.split(r'^  - (?:serializedVersion: \d+\s*\n    )?curve:\s*\n',found.group(1),flags=re.M)[1:]:
  path=re.search(r'^    path: ?(.*)$',block,re.M)
  if not path:continue
  keys=[]
  for raw in re.split(r'^      - serializedVersion: \d+\s*\n',block,flags=re.M)[1:]:
   key={}
   for k in ['time','value','inSlope','outSlope','tangentMode','weightedMode','inWeight','outWeight']:
    v=re.search(r'^        '+k+r': ([^\n]+)',raw,re.M)
    if v:key[k]=numeric(v.group(1))
   if key:keys.append(key)
  record={'path':path.group(1),'keys':keys}
  for k in ['attribute','classID','flags']:
   v=re.search(r'^    '+k+r': ?([^\n]*)',block,re.M)
   if v:record[k]=numeric(v.group(1))
  for k in ['m_PreInfinity','m_PostInfinity','m_RotationOrder']:
   v=re.search(r'^      '+k+r': ([^\n]+)',block,re.M)
   if v:record[k]=numeric(v.group(1))
  result.append(record)
 return result

def clip(name):
 path=ANIMS/(name+'.anim');s=path.read_text(encoding='utf-8-sig')
 tracks={}
 for sect,prop in [('m_PositionCurves','position'),('m_RotationCurves','rotation'),('m_EulerCurves','euler'),('m_ScaleCurves','scale')]:
  for row in curve_list(s,sect):tracks.setdefault(row.pop('path'),{})[prop]=row
 duration=float(re.search(r'^    m_StopTime: ([^\n]+)',s,re.M).group(1))
 return {'name':name,'source':str(path.relative_to(ROOT)).replace('\\','/'),'duration':duration,'sampleRate':float(re.search(r'^  m_SampleRate: ([^\n]+)',s,re.M).group(1)),'wrapMode':int(re.search(r'^  m_WrapMode: (\d+)',s,re.M).group(1)),'tracks':tracks,'floatCurves':curve_list(s,'m_FloatCurves')}

source=ROOT/'client/SHIN/Assets/ResourcesAssets/Prefabs/Model/City/NormalChessboard_01.prefab';text=source.read_text(encoding='utf-8-sig')
groups=[]
for match in re.finditer(r'^  - groupName: (BuddyTrick_[^\n]+)\n(.*?)(?=^  - groupName:|^  \w+:|^---|\Z)',text,re.S|re.M):
 group={'name':match.group(1),'tracks':[{'squarePos':int(pos),'animation':name}for pos,name in re.findall(r'squarePos: (\d+)\s+animationName: ([^\n]+)',match.group(2))]};groups.append(group)
needed={'ani_gezi_jingguo','ani_gezi_stop'}|{t['animation']for g in groups for t in g['tracks']}
clips={name:clip(name)for name in sorted(needed)}
targets={'' ,'Root','Root/Root_model'}
for c in clips.values():targets.update(c['tracks']);targets.update(row['path']for row in c['floatCurves'])
slots={};issues=[]
def traverse(t,p=''):
 rows={p:t}
 for ptr in t.m_Children:
  child=ptr.read();name=child.m_GameObject.read().m_Name;rows.update(traverse(child,p+'/'+name if p else name))
 return rows
for obj in env.objects:
 if obj.type.name!='MonoBehaviour':continue
 try:tree=obj.read_typetree()
 except:continue
 if '_Center' not in tree:continue
 go=raw_pointer(obj,tree['m_GameObject']);chain=chain_of(go)
 if chain[0]['name']!='NormalChessboard_01':continue
 instances=[(i,r)for i,r in enumerate(chain)if r['name'].isdigit()and 1<=int(r['name'])<=40]
 if not instances:continue
 ii,instance=instances[0];sid=instance['name'];anim=raw_pointer(obj,tree['_Animation']);adata=anim.read_typetree();aroot=transform_of(anim);nodes=traverse(aroot);names=[]
 for ref in adata['m_Animations']:
  ao=raw_pointer(anim,ref)
  if ao:names.append(ao.read().m_Name)
 localtargets=set(targets)
 for field in ['_Center','_PropRoot','_TextMeshPro']:
  ref=tree.get(field)
  if ref and ref.get('m_PathID'):
   h=hook(obj,ref,ii);prefix=chain_of(anim);localtargets.add('/'.join(h['path'][len(prefix):]))
 localtargets|={path.rsplit('/',i)[0] for path in list(localtargets) for i in range(1,path.count('/')+1)}
 bindings={}
 for path in sorted(localtargets):
  tr=nodes.get(path)
  if tr is None:continue
  tchain=chain_of(next(c.component for c in tr.m_GameObject.read().m_Component if c.component.type.name in ['Transform','RectTransform']))
  bindings[path]={'local':trs(tr),'matrixInInstance':combined(tchain[ii+1:]),'matrixInNormalPrefab':combined(tchain[1:]),'active':bool(tr.m_GameObject.read().m_IsActive)}
 used={name for name in names if name in clips}
 missing={name:[path for path in clips[name]['tracks']if path not in nodes]for name in sorted(used)}
 slots[sid]={'followCameraOffset':tree.get('_FollowCameraOffset'),'animationRoot':{'path':[r['name']for r in chain_of(anim)],'local':trs(aroot)},'availableClips':sorted(used),'bindingNodes':bindings,'unboundTransformTracks':{k:v for k,v in missing.items()if v},'unboundFloatTracks':{name:[row['path'] for row in clips[name]['floatCurves'] if row['path'] not in nodes] for name in sorted(used) if any(row['path'] not in nodes for row in clips[name]['floatCurves'])}}
assert len(slots)==40
for g in groups:
 for track in g['tracks']:
  if track['animation'] not in slots[str(track['squarePos'])]['availableClips']:issues.append({'group':g['name'],'squarePos':track['squarePos'],'unavailableClip':track['animation']})
# Explicit first-nonrest key times expose the authored wave delays, without inventing a stagger.
for c in clips.values():
 first=[]
 for path,track in c['tracks'].items():
  for prop,row in track.items():
   keys=row['keys']
   if keys:
    base=keys[0]['value']
    changed=next((k['time']for k in keys if k['value']!=base),None)
    if changed is not None:first.append(changed)
 c['firstChangedKeyTime']=min(first)if first else None
result={'source':str(source.relative_to(ROOT)).replace('\\','/'),'sourceBundle':primary['FileHash']+'.bundle','matrixLayout':'column-major','triggers':{'pass':{'clip':'ani_gezi_jingguo','speed':1.5,'effectiveDuration':clips['ani_gezi_jingguo']['duration']/1.5},'stop':{'clip':'ani_gezi_stop','speed':1.5,'effectiveDuration':clips['ani_gezi_stop']['duration']/1.5},'standGroup':{'nameRule':'BuddyTrick_{lineIndex}_{restStep}','speed':1,'trigger':'after moveDuration + standDuration for RunEndJump segment'}},'clips':clips,'animationGroups':groups,'slots':dict(sorted(slots.items(),key=lambda kv:int(kv[0]))),'notes':['Clip tracks are ABSOLUTE local TRS values relative to the square Animation component game object. Apply them to the named node; do not multiply them as extra deltas. Unbound paths are ignored by Unity and are explicitly listed per slot.','matrixInNormalPrefab includes Root Y45 and excludes prefab root scale0.9, matching grid-hooks.json.','Plain passing/landing uses ani_gezi_jingguo / ani_gezi_stop, at PIECE_MOVE_SPEED_RATE=1.5. There are no ani_gezi_come/ani_gezi_pass ordinary calls.','BuddyTrick animation groups play all listed tracks simultaneously at PIECE_JUMP_SPEED_RATE=1. Delays are authored INSIDE distinct shake clip curves; no separate delay field exists in AnimationGroupTrack.','Only ordinary enter/stop clips plus actual BuddyTrick stand/jump group clips are exported. FriendRent and other gameplay actions are outside this export.','Per-slot availableClips comes from the original bundled Animation reference list. Source .anim curves and source prefab AnimationGroup list are kept with their paths for verification.','Infinite scalar slopes are stored as the string Infinity or -Infinity; treat these as stepped/constant segments.','Hermite key slopes/tangentMode/weights are preserved. Quaternion components must be normalized after interpolation. Float curves are retained separately with exact attribute and classID; some animate material properties, not TRS.'],'issues':issues}
dest=SCENE/'board-motion.json';dest.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n',encoding='utf8')
print(json.dumps({'output':str(dest),'bytes':dest.stat().st_size,'slots':len(slots),'groups':[(g['name'],len(g['tracks']))for g in groups],'clips':{k:{'duration':v['duration'],'paths':list(v['tracks']),'floatCurves':len(v['floatCurves']),'firstChangedKeyTime':v['firstChangedKeyTime']}for k,v in clips.items()},'availableNormalCounts':{n:sum(n in s['availableClips']for s in slots.values())for n in ['ani_gezi_jingguo','ani_gezi_stop']}},ensure_ascii=False))