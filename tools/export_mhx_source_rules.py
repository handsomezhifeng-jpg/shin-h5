"""Join original decoded tables; retain source Lua evidence for construction rules.

This does not simulate server responses or convert merge-board item rewards.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/construction'
CONFIG = OUT / 'config'
LUA = Path(r'C:/dev/mhxcz-analysis/construction-lua')

def table(path):
    return json.loads((CONFIG / path).read_text(encoding='utf8'))

def group(rows, key):
    result = {}
    for row in rows:
        result.setdefault(str(row[key]), []).append(row)
    return result

def rewards(ids, nums):
    if ids in ('', None):
        return []
    return [dict(goodsId=int(i),goodsNum=int(n)) for i,n in zip(str(ids).split(';'),str(nums).split(';'))]

table_paths = ['Data/Common/MainQuestVo.json','Data/Common/MainQuestScheduleVo.json','Data/Common/AvatarVo.json','Data/Common/BaseParamsVo.json','Data/Map/world_1/UnitUnlockVo.json','Data/Map/world_1/Unit31Vo.json','Data/Plot/Main/PlotIndexVo.json','Data/Plot/Main/stage_1/PlotVo.json','Data/Plot/Main/stage_1/PlotDialogueVo.json','Data/Plot/Main/stage_1/PlotAnimationVo.json','Data/Plot/Main/stage_1/PlotStandPointVo.json','Common/PlayerExp.json']
tables = {p:table(p) for p in table_paths}
quests = tables[table_paths[0]]['rows']
unlocks = tables['Data/Map/world_1/UnitUnlockVo.json']['rows']
unlock_index = {str(r['index']):r for r in unlocks}
unlock_unit = group(unlocks,'unitId')
plot_groups = group(tables['Data/Plot/Main/stage_1/PlotVo.json']['rows'],'groupId')
dialogue_groups = group(tables['Data/Plot/Main/stage_1/PlotDialogueVo.json']['rows'],'groupId')
animation_groups = group(tables['Data/Plot/Main/stage_1/PlotAnimationVo.json']['rows'],'groupId')
standpoints = {str(r['id']):r for r in tables['Data/Plot/Main/stage_1/PlotStandPointVo.json']['rows']}
avatars = {str(r['id']):r for r in tables['Data/Common/AvatarVo.json']['rows']}

def resolve_unlocks(task, step):
    params = step['performParams']
    if params in ('',None):
        return [r for r in unlocks if str(r['unlockType'])=='6' and str(r['unlockNum'])==str(task['id']+1)], 'condition:6_'+str(task['id']+1)
    resolved = []
    for token in str(params).split(','):
        if not token:
            continue
        if '_' in token:
            vos = sorted(unlock_unit.get(token, []),key=lambda r:(float(r['unlockNum']) if str(r['unlockNum']).replace('.','',1).isdigit() else 0,r['index']))
            matching = [r for r in vos if str(r['unlockType'])=='6' and float(r['unlockNum']) <= task['id']]
            if matching:
                resolved.append(matching[-1])
            elif vos:
                resolved.append(vos[0])
        elif token in unlock_index:
            resolved.append(unlock_index[token])
    if step['plotType']==3:
        resolved = resolved[:1]
    return resolved, 'explicit:'+str(params)

plans = []
for task in quests:
    plot = plot_groups.get(str(task['plotId']))
    if plot is None:
        continue
    steps = []
    for row in sorted(plot,key=lambda r:r['subId']):
        step = dict(row)
        kind = row['plotType']
        if kind==1:
            step.update(action='dialogue',dialogueRows=sorted(dialogue_groups.get(str(row['performId']),[]),key=lambda r:r['dialogueId']))
        elif kind==2:
            step.update(action='animationTimeline',animationRows=sorted(animation_groups.get(str(row['performId']),[]),key=lambda r:r['order']))
        elif kind in (3,4):
            selected, method = resolve_unlocks(task,row)
            step.update(action='chooseOneOfThreeThenUnlock' if kind==3 else 'fixedUnitUnlock',unlockRows=selected,resolution=method,reviewSkipsThisStep=kind==3)
        elif kind==10:
            step.update(action='newAreaPopup',prefab='TransitionNewAreaUnlockPopup',showSeconds=2.5,afterCloseSeconds=.5)
        else:
            step['action']={5:'emptyBranch',6:'emptyBranch',7:'switchWorldUnlessSkipped',8:'unlockWhenPlotHasGoods',9:'showCGUnlessSkipped',11:'activityUnitUnlock',12:'playBGM'}.get(kind,'unresolved')
        steps.append(step)
    plans.append(dict(task=task,rewards=rewards(task['rewardId'],task['rewardNum']),showRewards=rewards(task['showRewardId'],task['showRewardNum']),avatar=avatars.get(str(task['avatar'])),standPoint=standpoints.get(str(task['plotId'])),steps=steps))

lua_paths = ['Game/MainQuest/MainQuestMgr.lua','Game/Plot/PlotMgr.lua','Game/Plot/PlotDialogue.lua','Game/Plot/PlotDialogueChatNode.lua','Game/MapGame/Scripts/Perform/PerformScripts.lua','Game/MapGame/UnitChangeSkin/Unit31Mgr.lua','Game/MapGame/UnitSkin/UnitSkinMgr.lua','Game/MapGame/Map/MapMgr.lua','Game/MapGame/Map/MapConfigMgr.lua','Game/UI/Unit31/UIUnit31Dialog.lua','Game/UI/MainQuest/UIMainQuestDialog.lua','Game/UI/MainQuest/UIMainQuestDaySlide.lua','Game/UI/MainQuest/UIMainQuestReviewListQuestNode.lua','Game/UI/MainQuest/UIMainQuestReviewListChapterNode.lua','Game/Dojo/PlayerDojo.lua','Game/Setting/ConfigModule.lua','Game/StartView/PlayerLevelDialog.lua','Game/StartView/PlayerLevelUpDialog.lua','Game/Constants/ConstantsCommon.lua','Game/Constants/ConstantsGoods.lua','Game/Constants/ConstantsPath.lua','Game/UI/HeadTop/Unit/Node/UIUnitLongTapNode.lua','Game/UI/HeadTop/Unit/UIUnitRoot.lua']
evidence = {}
for path in lua_paths:
    p = LUA/path
    content = p.read_bytes()
    lines = content.decode('utf8').splitlines()
    evidence[path] = dict(path=str(p),sha256=hashlib.sha256(content).hexdigest(),functions=[dict(line=i+1,declaration=s) for i,s in enumerate(lines) if s.startswith('function ')])

level_rows = []
total = 0
for row in sorted(tables['Common/PlayerExp.json']['rows'],key=lambda r:r['lv']):
    level_rows.append(dict(**row,total=total,rewards=rewards(row['rewardId'],row['rewardNum']),showRewards=rewards(row['showRewardId'],row['showRewardNum'])))
    total += row['exp']

result = dict(
 formatVersion=1,
 evidenceType='Decoded shipped tables and decompiled Lua static control flow; no additional emulator actions.',
 evidence=evidence,
 tables={p:dict(url='assets/construction/config/'+p,sha256=hashlib.sha256((CONFIG/p).read_bytes()).hexdigest(),tsvSha256=v['tsvSha256'],columns=v['columns'],declaredTypes=v['declaredTypes'],rows=len(v['rows'])) for p,v in tables.items()},
 columnMeanings={
  'MainQuestVo':dict(id='Quest key; completion means id < curQuestId.',nextId='Configured following quest; source client updates current id from successful server response.',chapte='Chapter id (source spelling).',sec='Display section number within chapter.',exp='Experience credited immediately after submit succeeds.',avatar='AvatarVo id for task-book full portrait and name.',plotId='PlotVo.groupId in stage chosen by PlotIndexVo.toQuestId.',coinConsume='Base gold cost before the BaseParams 18/19 multiplier branch.',rewardId='Semicolon-separated actual configured reward ids; live submit uses response.rewards.',rewardNum='Semicolon-separated reward counts paired with rewardId.',showRewardId='Progress-bar preview reward ids; does not separately grant a chapter reward.',showRewardNum='Progress-bar preview reward counts.',appearanceReward='Parsed numeric field; all current rows blank.',status='Source row status; not a quest objective condition.'),
  'PlotVo':dict(groupId='MainQuestVo.plotId join.',subId='Sequential execution order; keep dialogue/construction interleaving.',plotType='Action dispatch type documented in plotTypes.',performId='Dialogue/animation group id or other type-specific resource id.',performParams='Comma-separated UnitUnlock indices for types3/4, empty means condition6 / completedQuest+1; legacy underscore tokens are unit ids.'),
  'UnitUnlockVo':dict(index='Record primary key, used by explicit PlotVo.performParams.',unitId='Map unit id; do not confuse with unlock record index.',unlockType='6 = ViewMainQuestId, evaluated against viewed quest progress.',unlockNum='Required viewed quest id; completing task N uses N+1.',unlockActive='0 add,1 remove,2 swap/reload skin; initial load always keeps type2 units.',unlockActiveParam='Skin override; string0 disables default unlocked skin1 and Unit31 collider.',unlockAnimType='0 none,1 XYScaleDisappear,2 XYScaleShow,3 XScaleShow,4 DropShow,5 FadeOut,6 FadeIn.',unlockFxType='Comma-separated effect ids:0 none,1 NormalStar,2 Dust,3 Hammer,4 FireClean,5 WindClean,6 StarClean,7 DustClean.',unlockAnimDelay='Original tween delay in game seconds.',camPos='Camera world X,Y.',camScale='Orthographic half-height.',camMoveDuration='Camera movement game seconds.'),
  'PlayerExp':dict(lv='Current level whose row defines the cost and rewards for leaving that level.',exp='Experience needed for this single level.',total='Cumulative start threshold reconstructed as sum of previous exp rows, consistent with original IDGroup.',rewardId='Actual reward ids for upgrading from this level.',showRewardId='Preview ids used by level info; may intentionally differ from actual reward ids.')
 },
 stateMachine=dict(
  initialization=dict(constructorCurrentQuest=1,constructorCurrentViewQuest=1,constructorUnlockChapter=0,note='Server sync overrides these fields. A clean local save can use quest1; existing source runtime screenshot started on quest2.'),
  submitGuard='Not all quests finished AND enough GoldId102 for computed cost. No merge-board task objective is checked here.',
  submitSuccessOrder=['consume GoldId102 cost','credit ExpId104 quest.exp (may queue level-up reward/popup)','credit server response.rewards','set current quest to server mainTaskInfo.id; final sentinel sets allFinished and lastQuest+1','update unlockChapterId; broadcast quest events','queue PlayMainPlot(completedQuestId)','queue exp/icon fly effects','close task book and hide main UI in caller'],
  failure='Nonzero server errCode returns before debit/reward/quest mutation.',
  cost=dict(base='MainQuestVo.coinConsume',multiplierChapterWindow=2,multiplier=3,condition='currentChapter + 2 > unlockChapterId',whenFalse='base cost',source='MainQuestMgr:GetQuestConsumeNum / BaseParamsVo18,19',unknown='Server unlockChapterId is not recoverable from offline tables. Any local schedule-derived replacement is an explicit port policy.'),
  plot='Process PlotVo by subId; dialogue and timelines can occur before or after the three-choice step. Update curViewQuestId to curQuestId only after the entire plot finishes.',
  choose=dict(initialSelection='UnitSkinMgr record for world+unit; missing is0.',confirmVisible='selectedSkinId != 0',choices=[1,2,3],selectionPreview='SwitchSkinId displays only selected preview; plot origin hides base after selecting >0.',confirm='ExitSwitchUnit records selection; PlayUnit31Unlock then runs construction effect and resumes remaining plot rows.',cancel='UIUnit31Dialog binds only 3 choices and confirm; no cancel handler in this source.',debit='No additional debit for choice or confirmation.',previewBrightness=dict(property='_Brightness',fromValue=.9,toValue=1.2,forwardSeconds=1,backSeconds=.6,ease='Linear',loop=True)),
  subsequentRedecoration=dict(guard='Unit31 collider available on unlocked unit; unlockActiveParam string0 disables it.',initialSelection='Recorded skin id.',sameSelection='Show existing unit.',changedSelection='Reload selected skin and record.',cost='No ConsumeGoods / currency request in Unit31Mgr or UnitSkinMgr record path.',effect='Direct non-plot confirm reloads unit; does not call PlayUnit31Unlock or construction hammer.'),
  redecorationEntry=dict(gestureStartGameSeconds=.2,progressSeconds=1.5,action='LongTapStart creates the original TransitionDecorationConfirm progress circle; after1.5 seconds UIUnitLongTapNode directly calls Unit31Mgr.SwitchUnit. Release removes node and stops its coroutine/tween.',unused='The old Choose button branch exists in the prefab but is not bound by UIUnitLongTapNode.',stationaryToleranceNativeDefaultPixels=15,stationaryComparison='(position-startPosition).sqrMagnitude <= tolerance²',nativeEvidence='经验/outputs/梦幻消除战-资源核查/longtap-easytouch.json'),
  initialMapSkin=dict(lockedUnit='Default prefab skin00.',unlockedUnit31WithoutRecord='Skin1, except unlockActiveParam string0 means skin0.',recordedSkin='Positive recorded value overrides default.'),
  unlockPerformance=dict(timeScale=1.6666666666666667,roleAnimationSpeed=.6,restoredTimeScale=1,hammerGameSeconds=1.5,hammerWallSeconds=.9,hammerPrefab='MapGame/Prefab/Fx/animation_hammer.prefab',completionPrefab='MapGame/Prefab/Fx/animation_newlook.prefab',completionGameSeconds=1.75,completionOrigin='Main camera position with z0',note='Hammer18 particles are internal to hammer prefab; animation_newlook is a separate completion effect.'),
  nonHammerFx=dict(normalStar=dict(kind=1,gameSeconds=2,phase='After show animation; waitFxTime at least2 seconds.',shape='MeshRenderer uses original unit triangle surface, scale1/position0/startSizeMultiplier1; Tilemap overrides with original UnitBoundsVo world rectangle and ceil(area/100) startSizeMultiplier.'),hide=dict(kinds=[2,4,5,6],gameSeconds=1.5,phase='Spawn independently on every child while its hide animation runs. Pool return is delayed1.5 seconds; the main sequence only waits for the hide tweens, not these effect lifetimes.'),dustClean=dict(kind=7,gameSeconds=2,phase='Construction leader effect replaces the Hammer stage; then reload/show animation and NewLook1.75 seconds.'),api='src/construction-unit-fx.mjs; independent original particle/Shader/SpriteRenderer instances support concurrent child effects.'),
  progress=dict(light='(chapterQuestIndex - 1) / chapterQuestCount',black='chapterQuestIndex / chapterQuestCount',rewardPreview='For each current/future quest in chapter with showRewards, display only its first showReward icon.',chapterReward='No separate chapter reward grant in UIMainQuestDaySlide; chapter end task rewards are regular submit rewards.'),
  review=dict(chapterUnlock='chapterId <= currentQuest.chapte',questUnlock='quest.id < curQuestId',lockedDisplay='name empty, number ???, lock icon; click toasts story not unlocked.',action='PlayMainPlot(selected old quest) then reopen main quest dialog preserving review list state.',charge='No RequestSubmit, cost, XP or reward grant.',threeChoice='PlotMgr type3 skips if reviewed completedQuestId < curViewQuestId. Type4/10 still execute as coded.'),
  level=dict(experienceStorage='PlayerDojo.mainExp stores cumulative experience.',level='Highest level whose original IDGroup total <= cumulative exp.',infoProgress='(mainExp - currentLevel.total) / currentLevel.exp',rewardTiming='PlayerDojo:PlayerMainExp grants GetPlayerLevelReward(oldLevel) immediately when computed level changes, then queues PlayLevelUp.',popup='PlayerLevelUpDialog displays newLevel and actual reward row oldLevel; claim button plays item fly/close only.',multiLevel='The decompiled setter takes only oldLevel reward once when level changes; it does not loop skipped levels. A per-crossed-level implementation is a port policy, not that client control flow.')
 ),
 plotTypes={1:'Await PlotDialogue group (not PlotDialog legacy list), unless skip.',2:'Await AnimationTimeline group; skip still handles black-switch events.',3:'Three-choice construction; skipped during already-viewed review; still runs even if ordinary story skip enabled.',4:'Fixed unit additions/removals/reloads, no selection; source executes on review.',5:'Empty dispatch branch.',6:'Empty dispatch branch.',7:'Switch world unless story skipped.',8:'Unlock units conditioned on plot-held goods.',9:'CG unless story skipped.',10:'New-area banner2.5 seconds then0.5 delay; not an experience reward.',11:'Activity skin unlock.',12:'BGM playback.'},
 firstChapter=[p for p in plans if p['task']['chapte']==1],
 stage1QuestPlans=plans,
 playerLevels=level_rows,
 ui=dict(pack='assets/construction/story-ui.json',bindingLookup='pack.luaBindings[prefab][ownerPath][LuaFieldName].path gives exact original target node.',dialogue='PlotDialogue; zh_CN/zh_TW uses PositionRoot, not PositionRoot_3.',dialogueAdvance='Tap completes typing first; next tap advances; last closes via PlotDialogue_Out. Skip button is a two-click confirmation.',dialogueType={1:'Normal framed dialogue with avatar palette name plate.',2:'Thought/alternate style: original UISwitchImage/UISwitchText2, line hidden, shadows disabled.',3:'Black-screen letter typer: AppearDuration0.2, PendingTime0.05.'},dialoguePortrait='AvatarVo npc id; faceId is original Spine animation. Main player reflected horizontally; other role positiveX. GLOBAL_APP scale1, others0.85.',dialogueTextSpeed='Lua string.len(desc)/60 seconds (byte length for UTF-8), immediate fill when tapped.',originalFonts='Use font references in story-ui; actual Chinese preserved by Python typetree reader.'),
 portBoundary=dict(originalSource='MainQuest submission only checks coins; its chapters have no merge-board win condition column.',existingBoard='Funding construction from existing 富甲天下 coins is integration policy; no source evidence defines an exchange rate or board win gate.',itemRewards='Preserve source goodsId/goodsNum and their inventory identity. Do not translate to dice/gacha/recruitment tokens without a separately approved rule.',server='Success response reward payload and unlocked chapter can differ from static table; offline reproduction explicitly substitutes local authoritative state.'),
 unresolved=['Server MainQuestSubmit response and unlockChapterId are not available offline.','Native Unity particle RNG/shape/integration and exact full-camera/color-space rendering remain in particle verification report.','PlotSingleRolePopup and TaskFinishPopup are not part of the current main-quest UI reconstruction.','EasyTouch15px is the recovered native constructor default; stripped scene typetrees cannot alone rule out a serialized runtime override.']
)
target=OUT/'source-rules.json'
target.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
print(json.dumps(dict(file=str(target),stage1Plans=len(plans),firstChapter=[dict(id=p['task']['id'],name=p['task']['name'],build=[u['unitId']for s in p['steps']for u in s.get('unlockRows',[])],types=[s['plotType']for s in p['steps']]) for p in result['firstChapter']],evidenceFiles=len(evidence),levels=len(level_rows)),ensure_ascii=True))
