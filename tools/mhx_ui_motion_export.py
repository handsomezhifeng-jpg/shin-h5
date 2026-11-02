"""Append original TaskDailog animation curves without rewriting other UI data."""
import copy
import json
import math
from pathlib import Path
import zipfile
import UnityPy

APK = Path(r"C:\Users\zhfzhang\Downloads\梦幻消除战.apk")
SOURCE = "assets/Bundles/Android/Base/ad025ec1c4f6135665e0803934a947c6.bytes"


def finite_json(value):
    if isinstance(value, float) and not math.isfinite(value):
        return "Infinity" if value > 0 else "-Infinity" if value < 0 else "NaN"
    if isinstance(value, dict):
        return {key: finite_json(v) for key, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [finite_json(v) for v in value]
    return value


def export_task_dialog_motion(prefab):
    with zipfile.ZipFile(APK) as archive:
        env = UnityPy.load(archive.read(SOURCE))
    clips = {}
    for obj in env.objects:
        if obj.type.name != "AnimationClip":
            continue
        source = obj.read_typetree()
        name = source["m_Name"]
        if not name.startswith("TaskDailog_"):
            continue
        base = "TaskDailog" if name in ("TaskDailog_Entry", "TaskDailog_Out") else "TaskDailog/Root"
        curves = []
        for field, kind, attribute in [("m_FloatCurves", "float", None), ("m_RotationCurves", "rotation", "m_LocalRotation"), ("m_PositionCurves", "position", "m_LocalPosition"), ("m_ScaleCurves", "scale", "m_LocalScale"), ("m_EulerCurves", "euler", "m_LocalEulerAngles")]:
            for curve in source.get(field, []):
                c = curve["curve"]
                curves.append({"kind": kind, "path": base + ("/" + curve["path"] if curve["path"] else ""), "relativePath": curve["path"], "attribute": curve.get("attribute", attribute), "classID": curve.get("classID"), "keys": finite_json(c["m_Curve"]), "preInfinity": c["m_PreInfinity"], "postInfinity": c["m_PostInfinity"], "rotationOrder": c["m_RotationOrder"]})
        muscle = source["m_MuscleClip"]
        clips[name] = {"name": name, "bindingBase": base, "source": SOURCE, "sourceObject": obj.assets_file.name + ":" + str(obj.path_id), "duration": muscle["m_StopTime"] - muscle["m_StartTime"], "startTime": muscle["m_StartTime"], "stopTime": muscle["m_StopTime"], "keyDuration": max((k["time"] for c in curves for k in c["keys"]), default=0), "effectiveLastKeyTime": max((k["time"] for c in curves for k in c["keys"]), default=0), "sampleRate": source["m_SampleRate"], "wrapMode": source["m_WrapMode"], "loop": muscle["m_LoopTime"], "curves": curves, "events": finite_json(source.get("m_Events", [])), "pointerCurveCount": len(source.get("m_PPtrCurves", []))}

    bindings = []
    def visit(node):
        for component in node.get("components", []):
            if component["type"] == "Animation":
                bindings.append({"path": node["path"], "sourceObject": component["sourceObject"], "fields": copy.deepcopy(component["fields"])})
        for child in node.get("children", []):
            visit(child)
    visit(prefab)
    return {"clips": clips, "open": ["TaskDailog_Task", "TaskDailog_Entry"], "close": ["TaskDailog_Out"], "animationBindings": bindings, "sampling": "Original Unity key times, in/out tangents, weighted modes and weights. Entry runs at TaskDailog; Task/Review states run independently at TaskDailog/Root. Curve Infinity tangents are encoded as strings for standard JSON.", "eventPolicy": "Original Unity events are retained as data and are not executed by the DOM animation player."}


if __name__ == "__main__":
    target = Path(__file__).resolve().parents[1] / "assets/construction/ui.json"
    ui = json.loads(target.read_text(encoding="utf8"))
    ui.setdefault("animations", {})["TaskDailog"] = export_task_dialog_motion(ui["prefabs"]["TaskDailog"])
    target.write_text(json.dumps(ui, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf8")
    print(json.dumps({name: {"duration": c["duration"], "keyDuration": c["keyDuration"], "curves": len(c["curves"])} for name,c in ui["animations"]["TaskDailog"]["clips"].items()}))
