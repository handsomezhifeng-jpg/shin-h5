"""Hash exported UI and audit source bindings without asserting full fidelity."""
from pathlib import Path
import hashlib
import json
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "construction"
ui = json.loads((OUT / "ui.json").read_text(encoding="utf8"))
story=json.loads((OUT/'story-ui.json').read_text(encoding='utf8')) if (OUT/'story-ui.json').exists() else {}
task=json.loads((OUT/'task-content.json').read_text(encoding='utf8')) if (OUT/'task-content.json').exists() else {}
all_sprites={**ui['sprites'],**story.get('sprites',{}),**{row['sprite']['sourceObject']:row['sprite']for row in task.get('items',{}).values() if row.get('sprite')}}
def digest(data):
    return hashlib.sha256(data).hexdigest()
def walk(node):
    yield node
    for child in node.get("children", []):
        yield from walk(child)
images = []
for key, sprite in all_sprites.items():
    path = ROOT / sprite["url"]
    im = Image.open(path)
    assert im.size == (sprite["width"], sprite["height"]), sprite["url"]
    images.append({"sourceObject": key, "name": sprite["name"], "url": sprite["url"], "sha256": digest(path.read_bytes())})
transforms = []
for name, prefab in {**ui["prefabs"],**story.get('prefabs',{})}.items():
    for node in walk(prefab):
        canonical = json.dumps(node.get("transform", {}), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf8")
        transforms.append({"prefab": name, "path": node["path"], "sourceObject": node["sourceObject"], "transformSha256": digest(canonical), "authoringActive": node["active"]})
fonts = []
for key, font in {**ui["fonts"],**story.get('fonts',{})}.items():
    if font["url"]:
        raw = (ROOT / font["url"]).read_bytes()
        assert raw[:4] in (b"\x00\x01\x00\x00", b"OTTO", b"ttcf"), font["url"]
        fonts.append({"sourceObject": key, **font, "sha256": digest(raw), "bytes": len(raw)})
bindings = {}
for role, name in ui["visualBindings"].items():
    record = ui["spritesByName"][name]
    bindings[role] = {"spriteName": name, "url": record["url"], "sourceObject": record["sourceObject"], "sha256": digest((ROOT / record["url"]).read_bytes())}
assert "\ufffd" not in (OUT / "ui.json").read_text(encoding="utf8"), "Corrupt Unicode in prefab strings"
bindings['currencySource']=ui.get('currencySource')
bindings['sourceFxAudit']='assets/construction/fx-audit.json'
bindings['sourceLongTap']={'nativeConstructorTolerancePixels':15,'gestureStartSeconds':.2,'fillSeconds':1.5,'nativeEvidence':'经验/outputs/梦幻消除战-资源核查/longtap-easytouch.json'}
bindings['taskItems']={key:{k:v for k,v in row.items()if k in ['id','name','photoId','resourcePath','sourceTable','sourceBundle','icon','sha256']}for key,row in task.get('items',{}).items()}
result = {"imageSha256": {"count": len(images), "images": images, "semanticReview": "Original currency102 and experience104 were visually checked from their standalone source images. Task1/2/3/4/7 screenshots cover the original portraits, exp15, reward20601/30201/10701 and chapter previews; see outputs/construction-task-content. Hash checks alone do not certify every unused atlas sprite's meaning."}, "prefabTransform": {"count": len(transforms), "records": transforms, "taskAnimationEndState": ui["animationEndStates"]["TaskDailog"], "derivation": "Original RectTransform records and original AnimationClip bindings are retained. CanvasScaler and Horizontal/GridLayout/Slider runtime changes are implemented from source fields in the H5 helpers."}, "font": {"files": fonts, "replacementCharacters": 0,"remainingDifference":"The UI uses the recovered font files. TextMeshPro numeric nodes currently use the bundled TTF renderer rather than the original SDF atlas shader; edge rasterization can differ."}, "sourceBindings": bindings, "unresolved": ["Server MainQuestSubmit response.rewards and unlockChapterId are not available offline; the port explicitly uses original static reward tables and a local CN-schedule choice. Source table/Lua rules are recovered in source-rules.json.", "Unity native particle RNG, shape distribution, velocity integration, stretched billboard pivot and trail tessellation remain numerical approximations. Original hammer18, newlook7, fly terminal3+5 and six non-Hammer unlock24 systems, textures/materials and shader evidence are retained and replayed; see fx-audit.json.", "AssetKits.ParticleImage fly icons use source circle, lifetime, size/speed and weighted attractor curves with a deterministic H5 integrator. Native RNG and internal motion are not bit-identical; terminal glow replay status is documented by the fly helper.", "Native camera capture/blur, complete postprocessing/color-space/depth and TMP SDF text rasterization are not pixel-identical to DOM/WebGL composition. Source prefab/shader fields remain available for further comparison.", "The source merge-board/store/activity controls are hidden where those source systems are not integrated with the host. No invented board objective, exchange rate or currency conversion is attributed to the source."]}
(OUT / "ui-audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
print(json.dumps({"images": len(images), "transforms": len(transforms), "fonts": len(fonts), "criticalBindings": len(bindings), "unresolved": len(result["unresolved"])}))
