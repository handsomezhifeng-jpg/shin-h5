"""Read-only extraction of shipped MHXC construction UI prefabs and sprites.

Uses APK bytes plus the user's already-downloaded Unity bundles. No APK code is
executed. Default active states are authoring data, not observed runtime state.
"""
import hashlib
import json
import copy
from pathlib import Path
import re
import zipfile
import math
from PIL import Image

import UnityPy
from UnityPy.files import SerializedFile
from UnityPy.helpers import TypeTreeHelper

# On this Windows host the optional native reader corrupts some UTF-8 text.
# The Python reader preserves the original Chinese strings.
NATIVE_TYPETREE_READER = TypeTreeHelper.read_typetree_boost

def read_tree(obj):
    TypeTreeHelper.read_typetree_boost = None
    try:
        return obj.read_typetree()
    finally:
        TypeTreeHelper.read_typetree_boost = NATIVE_TYPETREE_READER

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT.parent / "经验" / "outputs" / "梦幻消除战-资源核查"
APK = Path(r"C:\Users\zhfzhang\Downloads\梦幻消除战.apk")
OUT = ROOT / "assets" / "construction"
OUT.mkdir(parents=True, exist_ok=True)
IMAGES = OUT / "images-ui"
IMAGES.mkdir(exist_ok=True)
FONT_DIR = OUT / "fonts"
FONT_DIR.mkdir(exist_ok=True)

# Resolve every bundle and its transitive dependencies through the exact
# catalog matching the APK. Device caches can contain multiple builds with
# identical internal CAB names and must never be used as an unversioned lookup.
import sys
sys.path.insert(0, r"C:\dev\mhxcz-analysis")
from public_bundle_source import PublicBundleSource
public_source = PublicBundleSource()
records = []
source_bundle_ids = {}
source_by_bundle_id = {}
asset_dependencies = {}
for asset_row in public_source.catalog['assets']:
    asset_dependencies.setdefault(asset_row['bundleId'], set()).update(asset_row['dependencies'])
for bundle_id, row in enumerate(public_source.catalog['bundles']):
    filename = row['hash'] + Path(row['name']).suffix
    member = 'assets/Bundles/Android/Base/' + filename
    if member in public_source._apk_names:
        source, kind = member, 'apk'
    else:
        source, kind = str(public_source.destination / row['hash'][:2] / row['hash'] / '__data'), 'download'
    records.append((source, [row['name']], kind))
    source_bundle_ids[source] = bundle_id
    source_by_bundle_id[bundle_id] = source
by_source = {r[0]: r for r in records}
apk = zipfile.ZipFile(APK)

def source_bytes(source):
    bundle_id = source_bundle_ids[source]
    verified = public_source.ensure_bundle(bundle_id)
    return apk.read(verified[4:]) if verified.startswith('apk:') else Path(verified).read_bytes()

def serialized_files(file, name=None):
    if isinstance(file, SerializedFile):
        if not file.name and name:
            file.name = name
        yield file
        return
    for key, inner in (getattr(file, "files", None) or {}).items():
        yield from serialized_files(inner, key)

cabinet_sources = {}
environment = UnityPy.Environment()
loaded = set()
loaded_sources = {}
unknowns = []
sprites = {}
fonts = {}

def bundle_closure(bundle_id):
    ordered, seen = [], set()
    def visit(index):
        if index in seen:
            return
        seen.add(index)
        for dependency in set(public_source.catalog['bundles'][index]['dependencies']) | asset_dependencies.get(index,set()):
            visit(dependency)
        ordered.append(index)
    visit(bundle_id)
    return ordered

def load(source):
    if source in loaded:
        return
    bundle_id = source_bundle_ids[source]
    for index in bundle_closure(bundle_id):
        verified = public_source.ensure_bundle(index)
        path = verified[4:] if verified.startswith('apk:') else verified
        if path in loaded:
            continue
        loaded.add(path)
        data = source_bytes(path)
        row = public_source.catalog['bundles'][index]
        loaded_sources[path] = {'bundle': [row['name']], 'sha256': hashlib.sha256(data).hexdigest(), 'md5': row['hash'], 'size': row['size'], 'originalCatalogVersion': public_source.catalog['version'], 'originalCatalogSha256': public_source.catalog['sha256']}
        outer = environment.load_file(data, name=path)
        for file in serialized_files(outer):
            cabinet_sources[file.name.lower()] = path

def resolve(ref, file):
    if not ref or not ref.get("m_PathID"):
        return None
    fid, pid = ref["m_FileID"], ref["m_PathID"]
    target = file if fid == 0 else environment.get_cab(file.externals[fid-1].path)
    return target.objects.get(pid) if target is not None else None

def identity(obj):
    return f"{obj.assets_file.name}:{obj.path_id}"

def export_sprite(obj):
    key = identity(obj)
    if key in sprites:
        return key
    data = obj.read()
    name = data.m_Name
    stem = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
    filename = f"{stem}-{hashlib.sha256(key.encode()).hexdigest()[:8]}.png"
    try:
        img = data.image
        img.save(IMAGES / filename)
        tree = read_tree(obj)
        sprites[key] = {"name": name, "url": "assets/construction/images-ui/" + filename,
                        "width": img.width, "height": img.height,
                        "border": tree.get("m_Border"), "rect": tree.get("m_Rect"),
                        "pivot": tree.get("m_Pivot"), "pixelsPerUnit": tree.get("m_PixelsToUnits"),
                        "sourceObject": key}
    except Exception as exc:
        unknowns.append({"sprite": key, "error": str(exc)})
    return key

def export_font(obj):
    key = identity(obj)
    if key in fonts:
        return key
    data = read_tree(obj)
    raw = data.get("m_FontData")
    if raw:
        filename = hashlib.sha256(key.encode()).hexdigest()[:12] + ".ttf"
        (FONT_DIR / filename).write_bytes(bytes(raw))
        fonts[key] = {"name": data.get("m_Name"), "url": "assets/construction/fonts/" + filename}
    else:
        fonts[key] = {"name": data.get("m_Name"), "url": None}
    return key

def component(obj):
    tree = read_tree(obj)
    result = {"type": obj.type.name, "sourceObject": identity(obj)}
    if obj.type.name == "MonoBehaviour":
        script = resolve(tree.get("m_Script"), obj.assets_file)
        if script:
            result["script"] = read_tree(script).get("m_ClassName") or script.peek_name()
    # Preserve exact public serialized fields; UI adaptation can select what it uses.
    result["fields"] = tree
    for field in ("m_Sprite", "m_OverrideSprite"):
        target = resolve(tree.get(field), obj.assets_file)
        if target and target.type.name == "Sprite":
            result[field] = export_sprite(target)
    if result.get('script') == 'UISwitchImage':
        result['switchSprites'] = []
        for config in tree.get('spriteConfigs', []):
            target = resolve(config.get('sprite'), obj.assets_file)
            result['switchSprites'].append(export_sprite(target) if target and target.type.name == 'Sprite' else None)
    font = resolve(tree.get("m_FontData", {}).get("m_Font"), obj.assets_file)
    if font and font.type.name == "Font":
        result["font"] = export_font(font)
    return result

def node(go, parent_path=""):
    tree = read_tree(go)
    name = tree["m_Name"]
    path = parent_path + "/" + name if parent_path else name
    comps = [resolve(x["component"], go.assets_file) for x in tree["m_Component"]]
    trans = next((o for o in comps if o and o.type.name in ("RectTransform", "Transform")), None)
    result = {"name": name, "path": path, "active": bool(tree.get("m_IsActive", True)),
              "sourceObject": identity(go), "components": []}
    if trans:
        t = read_tree(trans)
        result["transform"] = {k: v for k, v in t.items() if k not in ("m_GameObject", "m_Children", "m_Father")}
        result["children"] = []
        for ref in t["m_Children"]:
            child = resolve(ref, trans.assets_file)
            if child:
                child_go = resolve(read_tree(child)["m_GameObject"], child.assets_file)
                result["children"].append(node(child_go, path))
    for obj in comps:
        if obj and obj.type.name not in ("RectTransform", "Transform", "CanvasRenderer"):
            result["components"].append(component(obj))
    return result

selected = []
for source, names, _ in records:
    if any(any(term in name for term in ("_prefabs_transition_transitionhomeview", "_prefabs_transition_transitiondecoration", "_prefabs_transition_transitionrestdecorselectpopup", "_prefabs_transition_transitionnewareaunlockpopup", "_prefabs_task.bytes")) for name in names):
        selected.append(source)

for source in selected:
    load(source)

prefabs = {}
for source in selected:
    for outer in list(environment.files.values()):
        # Locate only the selected bundle's serialized files using original cabinet identity.
        for f in serialized_files(outer):
            if cabinet_sources.get(f.name.lower()) != source:
                continue
            for obj in f.objects.values():
                if obj.type.name != "AssetBundle":
                    continue
                for path, value in read_tree(obj).get("m_Container", []):
                    go = resolve(value["asset"], f)
                    if go and go.type.name == "GameObject":
                        root = node(go)
                        root["source"] = source
                        root["assetPath"] = path
                        prefabs[root["name"]] = root

# Export whole relevant UI atlases too: dynamic icons may not have a prefab reference.
for source, names, _ in records:
    if any(any(t in n for t in ("_uiatlas_task.bytes", "_uiatlas_uihomeview.bytes", "_uiatlas_common1.bytes", "_uiatlas_common2.bytes", "_uiatlas_common3.bytes", "_uiatlas_mainicon.bytes", "_uiatlas_mainicon2.bytes", "_uiatlas_mainicon3.bytes")) for n in names):
        load(source)
        for f in list(environment.cabs.values()):
            if hasattr(f, "objects") and cabinet_sources.get(f.name.lower()) == source:
                for obj in f.objects.values():
                    if obj.type.name == "Sprite":
                        export_sprite(obj)

portraits = {}
portrait_dir = OUT / "portraits"
portrait_dir.mkdir(exist_ok=True)
for source, names, _ in records:
    if any(name.endswith("_bustrole_npc_1016.bytes") for name in names):
        load(source)
        for f in list(environment.cabs.values()):
            if isinstance(f, SerializedFile) and cabinet_sources.get(f.name.lower()) == source:
                for obj in f.objects.values():
                    if obj.type.name == "Texture2D":
                        data = obj.read()
                        image = data.image
                        image.save(portrait_dir / (data.m_Name + "-unity-texture.png"))
                        image.save(portrait_dir / (data.m_Name + ".png"))
                    elif obj.type.name == "TextAsset":
                        data = obj.read()
                        raw = data.m_Script.encode("utf8", "surrogateescape") if isinstance(data.m_Script, str) else bytes(data.m_Script)
                        (portrait_dir / data.m_Name).write_bytes(raw)
        # Unity imported this atlas into a power-of-two texture. Restore the
        # atlas page's authored dimensions so its original region UVs line up.
        atlas_text = (portrait_dir / "npc_1016.atlas").read_text(encoding="utf8")
        size_match = re.search(r"^size:(\d+),(\d+)$", atlas_text, re.M)
        if size_match:
            size = tuple(map(int, size_match.groups()))
            image = Image.open(portrait_dir / "npc_1016-unity-texture.png")
            if image.size != size:
                image.resize(size, Image.Resampling.LANCZOS).save(portrait_dir / "npc_1016.png")
        portraits["npc_1016"] = {"skeleton": "assets/construction/portraits/npc_1016.skel", "atlas": "assets/construction/portraits/npc_1016.atlas", "texture": "assets/construction/portraits/npc_1016.png", "source": source, "identification": "Pink dress and paired flower hair buns match the observed task portrait; setup/animation runtime placement must be corroborated."}

task_base = "TaskDailog/Root/Container/"
task_normal = task_base + "MaskPanel/TaskPanel/Normal/"
bindings = {"title": task_base + "PanelBgGroup/TitleGroup/TxtTitle", "description": task_normal + "RoleGroup/TxtPlot", "portrait": task_normal + "RoleGroup/NpcMask/Spine", "rewardContainer": task_normal + "CommonGoodsListLight", "rewardLabel": task_normal + "TxtReward", "costButton": task_normal + "FontStyleWithIconButton2", "costText": task_normal + "FontStyleWithIconButton2/layout/Text", "costIcon": task_normal + "FontStyleWithIconButton2/layout/IconItem/ImgIcon", "chapter": task_base + "DaySlider/ImgCalendar/TxtDayNum", "close": task_base + "PanelBgGroup/BtnClose", "review": task_base + "BtnToReview", "progress": task_base + "DaySlider/ImgMask/SliderLight"}

def flatten(tree):
    yield tree
    for child in tree.get("children", []):
        yield from flatten(child)

animation_end_states = {}
task_nodes = {n["path"]: n for n in flatten(prefabs["TaskDailog"])}
end_nodes = {}
clip_sources = []
for source, names, _ in records:
    if not any("_uianimation_taskdailog.bytes" in name for name in names):
        continue
    load(source)
    for file in list(environment.cabs.values()):
        if not isinstance(file, SerializedFile) or cabinet_sources.get(file.name.lower()) != source:
            continue
        for obj in file.objects.values():
            if obj.type.name != "AnimationClip":
                continue
            clip = read_tree(obj)
            name = clip["m_Name"]
            if name not in ("TaskDailog_Entry", "TaskDailog_Task"):
                continue
            base = "TaskDailog" if name == "TaskDailog_Entry" else "TaskDailog/Root"
            clip_sources.append({"name": name, "source": source, "sourceObject": identity(obj)})
            for curve_type, transform_field in (("m_FloatCurves", None), ("m_RotationCurves", "m_LocalRotation"), ("m_PositionCurves", "m_LocalPosition"), ("m_ScaleCurves", "m_LocalScale"), ("m_EulerCurves", "m_LocalEulerAngles")):
                for curve in clip.get(curve_type, []):
                    keys = curve["curve"]["m_Curve"]
                    if not keys:
                        continue
                    path = base + ("/" + curve["path"] if curve["path"] else "")
                    original = task_nodes.get(path)
                    if original is None:
                        unknowns.append({"animationPath": path, "clip": name})
                        continue
                    state = end_nodes.setdefault(path, {"transform": copy.deepcopy(original.get("transform", {})), "active": original["active"], "attributes": {}})
                    value = keys[-1]["value"]
                    attribute = curve.get("attribute", transform_field)
                    state["attributes"][attribute] = value
                    if transform_field:
                        state["transform"][transform_field] = value
                    elif attribute == "m_IsActive":
                        state["active"] = bool(value)
                    elif attribute == "m_Alpha":
                        state["alpha"] = value
                    elif attribute == "m_Color.a":
                        state["colorAlpha"] = value
                    elif "." in attribute:
                        field, axis = attribute.split(".", 1)
                        if field in state["transform"]:
                            state["transform"][field][axis] = value
animation_end_states["TaskDailog"] = {"clips": clip_sources, "nodes": end_nodes, "sampling": "Last authored key per curve; Entry bound to TaskDailog, Task bound to TaskDailog/Root. Quaternion Y rotation must be respected for the turning page."}

result = {"provenance": {"apkSha256": "089e36860ad51f2ec8e155d9ce56382dcb9d4843f2d5aa62ecfa26f14483e193", "reaEvidence": "ev_5b4ddc1cbaee8d7e3f4a02aac62a71440d9b56c85df167cc274414fcc5879f6d", "sources": loaded_sources},
          "coordinateSystem": "Unity RectTransform; anchors and pivot in bottom-left coordinate system; UI scaling/reference resolution must be measured from runtime.",
          "limitations": ["Default prefab active state is preserved; runtime controller visibility is not inferred.", "Task progression and construction costs are not established by UI prefabs.", "Android code analysis through REA JADX was unavailable; UI extraction uses UnityPy shipped bytes."],
          "prefabs": prefabs, "sprites": sprites, "spritesByName": {record["name"]: record for record in sprites.values()}, "fonts": fonts, "portraits": portraits, "taskBindings": bindings, "animationEndStates": animation_end_states, "unknowns": unknowns}
result["visualBindings"] = {"currencyCoin": "item_icon_40101", "taskBook": "main_icon_task", "close": "common_button_close", "experience": "hud_icon_exp", "style1": "furnish_icon_type_1", "style2": "furnish_icon_type_2", "style3": "furnish_icon_type_3"}
result["visualBindingNotes"] = ["Bindings above were checked against exported pixels. The package's item_icon_40301 slot contains a red gemstone, while item_icon_40101 contains the yellow square-hole coin in the present atlas; item names alone do not establish visual semantics."]
from mhx_ui_motion_export import export_task_dialog_motion
result["animations"] = {"TaskDailog": export_task_dialog_motion(prefabs["TaskDailog"])}
(OUT / "ui.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf8")
print(json.dumps({"prefabs": list(prefabs), "sprites": len(sprites), "fonts": len(fonts), "unknowns": unknowns}, ensure_ascii=True))
