"""Extract the original hammer prefab, animation curves and particle settings."""
import copy
import hashlib
import json
import math
import export_mhx_construction_ui as ui
from UnityPy.files import SerializedFile

source = next(path for path, names, _ in ui.records if any("_mapgame_prefab_fx_animation_hammer.bytes" in n for n in names))
ui.load(source)
files = [f for f in ui.environment.cabs.values() if isinstance(f, SerializedFile) and ui.cabinet_sources.get(f.name.lower()) == source]
root = None
for file in files:
    for obj in file.objects.values():
        if obj.type.name == "AssetBundle":
            for path, record in ui.read_tree(obj)["m_Container"]:
                root = ui.resolve(record["asset"], file)
                if root and root.type.name == "GameObject":
                    break
    if root:
        break
if root is None:
    raise RuntimeError("Original hammer prefab root was not found")
prefab = ui.node(root)
clips = {}
bindings = {}
particle_settings = []
sprite_keys = set()

def visit(node):
    for component in node["components"]:
        fields = component["fields"]
        if component["type"] == "Animation":
            cabinet, pid = component["sourceObject"].rsplit(":", 1)
            obj = ui.environment.get_cab(cabinet).objects[int(pid)]
            refs = fields.get("m_Animations", [])
            names = []
            default_name = None
            for ref in refs:
                clip_obj = ui.resolve(ref, obj.assets_file)
                if not clip_obj:
                    continue
                tree = ui.read_tree(clip_obj)
                name = tree["m_Name"]
                names.append(name)
                if ref == fields.get("m_Animation"):
                    default_name = name
                curves = {key: copy.deepcopy(tree.get(key, [])) for key in ("m_FloatCurves", "m_RotationCurves", "m_PositionCurves", "m_ScaleCurves", "m_EulerCurves", "m_PPtrCurves")}
                times = [key["time"] for curves2 in curves.values() for curve in curves2 for key in curve.get("curve", {}).get("m_Curve", [])]
                clips[name] = {"name": name, "duration": max(times, default=0), "sampleRate": tree["m_SampleRate"], "wrapMode": tree["m_WrapMode"], "curves": curves, "sourceObject": ui.identity(clip_obj)}
            bindings[node["path"]] = {"default": default_name, "clips": names, "playAutomatically": fields.get("m_PlayAutomatically")}
        elif component["type"] == "ParticleSystem":
            particle_settings.append({"path": node["path"], "fields": fields, "sourceObject": component["sourceObject"]})
        if component.get("m_Sprite"):
            sprite_keys.add(component["m_Sprite"])
    for child in node.get("children", []):
        visit(child)

visit(prefab)

def safe(value):
    if isinstance(value, float) and not math.isfinite(value):
        return "Infinity" if value > 0 else "-Infinity" if value < 0 else "NaN"
    if isinstance(value, dict):
        return {k: safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [safe(v) for v in value]
    return value

result = {"source": source, "sourceSha256": hashlib.sha256(ui.source_bytes(source)).hexdigest(), "prefab": prefab, "clips": clips, "animationBindings": bindings, "sprites": {key: ui.sprites[key] for key in sprite_keys}, "particleSettings": particle_settings, "limitations": ["Particle parameters are retained as source data. The H5 hammer renderer does not claim a complete Unity particle-system replay."]}
(ui.OUT / "hammer.json").write_text(json.dumps(safe(result), ensure_ascii=False, indent=2), encoding="utf8")
print(json.dumps({"prefab": prefab["name"], "clips": {name: clip["duration"] for name, clip in clips.items()}, "bindings": bindings, "sprites": len(sprite_keys), "particles": len(particle_settings)}, ensure_ascii=True))
