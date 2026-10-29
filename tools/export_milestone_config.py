#!/usr/bin/env python3
"""Export exactly two CN milestone activities from existing xlsx files, without modifying sources.

Run with the bundled Python (openpyxl is required). The exported JSON is deterministic.
All dates from the CN schedule are interpreted explicitly as Asia/Shanghai (UTC+08).
"""
from __future__ import annotations
import argparse
import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import openpyxl

CN_TZ = timezone(timedelta(hours=8))
ACTIVITY_IDS = {7010035: "noRank", 7110077: "rank"}
GOAL_NAMES = {1: "停留指定格", 2: "破坏失败", 3: "破坏成功", 4: "小型盲盒劫案",
              5: "中型盲盒劫案", 6: "大型盲盒劫案", 7: "超级盲盒劫案", 8: "棋盘拾取"}
RESOURCE_TYPES = {
    "1": {"name": "美金", "enum": "Dollar"},
    "2": {"name": "骰子", "enum": "Dice"},
    "3": {"name": "扭蛋值", "enum": "Gacha"},
    "4": {"name": "护盾", "enum": "Shield"},
    "5": {"name": "EX扭蛋值", "enum": "EXGacha"},
    "6": {"name": "宠物经验", "enum": "PetExp"},
    "7": {"name": "钻石", "enum": "Gem"},
}


def integer(value, default=0):
    if value is None or value == "":
        return default
    result = int(value)
    if float(value) != result:
        raise ValueError("Non-integer configuration value: " + str(value))
    return result


def groups(value):
    if value is None:
        return []
    return [integer(x) for x in str(value).split("|") if x.strip()]


def vector(value, length):
    if value is None or str(value).strip() in ("", "0", "0;0", "0;0;0"):
        return None
    parts = str(value).strip().split(";")
    if len(parts) != length:
        raise ValueError(f"Expected vector{length}: {value}")
    return [integer(part) for part in parts]


def rewards(value):
    if value is None or str(value).strip() in ("", "0", "0;0;0"):
        return []
    output = []
    for item in str(value).split("|"):
        parts = vector(item, 3)
        if parts is None:
            continue
        kind, item_id, count = parts
        if kind <= 0 or item_id <= 0 or count < 0:
            raise ValueError("Invalid reward: " + str(value))
        if count:
            output.append({"type": kind, "id": item_id, "count": count})
    return output


def timestamp(value):
    text = str(value).strip()
    parsed = datetime.fromisoformat(text).replace(tzinfo=CN_TZ)
    return text, parsed.isoformat(), int(parsed.timestamp() * 1000)


class Tables:
    def __init__(self, workspace):
        self.workspace = workspace
        self.sources = {}
        self.cache = {}

    def load(self, relative, sheet_name=None):
        file = self.workspace / relative
        if not file.is_file():
            raise FileNotFoundError(file)
        key = (relative, sheet_name)
        if key in self.cache:
            return self.cache[key]
        self.sources[relative] = {"path": relative, "sha256": hashlib.sha256(file.read_bytes()).hexdigest()}
        workbook = openpyxl.load_workbook(file, read_only=True, data_only=True)
        try:
            sheet = workbook[sheet_name] if sheet_name else workbook.worksheets[0]
            data = list(sheet.values)
            keys = data[1]
            output = []
            for row_number, row in enumerate(data[6:], 7):
                if not row or not any(value is not None for value in row):
                    continue
                record = {str(name): value for name, value in zip(keys, row) if name is not None}
                record["_source"] = {"path": relative, "sheet": sheet.title, "row": row_number}
                record["_cells"] = list(row)
                output.append(record)
        finally:
            workbook.close()
        self.cache[key] = output
        return output


def clean_record(row):
    return {key: value for key, value in row.items() if not key.startswith("_")}


def one(rows, key, value):
    found = [row for row in rows if row.get(key) == value]
    if len(found) != 1:
        raise ValueError(f"Expected one {key}={value}; got {len(found)}")
    return found[0]


def export(workspace):
    tables = Tables(workspace)
    base = "shin-research/3xlsx/"
    main_rows = tables.load(base + "国服排期/CN_activity_main.xlsx")
    sub_rows = tables.load(base + "国服排期/CN_activity_sub.xlsx")
    goal_rows = tables.load(base + "活动/activity_milestone_goal.xlsx")
    stage_rows = tables.load(base + "活动/activity_milestone.xlsx")
    drop_rows = tables.load(base + "活动/activity_milestone_type.xlsx")
    skin_rows = tables.load(base + "活动/activity_milestone_ui.xlsx")
    rank_rows = tables.load(base + "活动/common_rank.xlsx")
    square_rows = tables.load(base + "玩法/square_group.xlsx")
    item_rows = tables.load(base + "养成/item.xlsx")
    global_rows = tables.load(base + "玩法/global_variables.xlsx")

    activities, goal_ids, seq_ids, skin_ids, rank_ids = [], set(), set(), set(), set()
    for activity_id, kind in ACTIVITY_IDS.items():
        main = one(main_rows, "activity_id", activity_id)
        sub = one([r for r in sub_rows if integer(r.get("sub_index")) == 1], "activity_id", activity_id)
        start_raw, start_iso, start_ms = timestamp(main["open_time_s1"])
        end_raw, end_iso, end_ms = timestamp(main["end_time_s1"])
        if start_ms >= end_ms:
            raise ValueError("Activity must end after start")
        entry = {
            "id": activity_id, "title": main["name"], "kind": kind,
            "skinId": integer(main["skin_id"]), "icon": sub["icon"],
            "iconSource": "client/SHIN/Assets/ResourcesAssets/TextureRule/Milestone/" + sub["icon"] + ".png",
            "seqId": integer(sub["seq_id"]), "goalId": integer(sub["goal_id"]),
            "rankId": integer(sub["rank_id"]), "mapUnlock": integer(main["map_id"]),
            "levelUnlock": integer(main.get("level")),
            "startAt": start_iso, "endAt": end_iso, "startAtMs": start_ms, "endAtMs": end_ms,
            "scheduleRaw": {"start": start_raw, "end": end_raw},
            "activityType": integer(main["main_activity_type"]),
            "subType": integer(sub["sub_type"]), "subIndex": integer(sub["sub_index"]),
            "showIcon": integer(sub["show_icon"]), "iconBg": sub.get("icon_bg"),
            "source": {"main": main["_source"], "sub": sub["_source"]},
        }
        if not (workspace / entry["iconSource"]).is_file():
            raise FileNotFoundError(entry["iconSource"])
        activities.append(entry)
        goal_ids.add(entry["goalId"])
        seq_ids.add(entry["seqId"])
        skin_ids.add(entry["skinId"])
        if entry["rankId"]:
            rank_ids.add(entry["rankId"])
    assert rank_ids == {101}
    assert [(a["id"], a["skinId"], a["goalId"], a["seqId"]) for a in activities] == [
        (7010035, 24, 2, 7010001), (7110077, 8, 5, 7110001)]

    goals, square_groups, group_ids = {}, {}, set()
    for goal_id in sorted(goal_ids):
        selected = sorted((r for r in goal_rows if integer(r.get("id")) == goal_id),
                          key=lambda r: integer(r.get("key2")))
        if not selected:
            raise ValueError("Missing goal rules")
        goals[str(goal_id)] = []
        for row in selected:
            group = integer(row.get("square_group")) if row.get("square_group") is not None else None
            if group is not None:
                group_ids.add(group)
            text = row.get("square_text")
            goals[str(goal_id)].append({
                "key": integer(row["key2"]), "type": integer(row["goal_type"]),
                "typeName": GOAL_NAMES[integer(row["goal_type"])],
                "squareGroup": group, "score": integer(row["score"]),
                "squareIcon": row.get("square_icon"),
                "textKey": text if isinstance(text, (int, float)) else None,
                "text": str(text) if text is not None else "",
                "spawnCount": integer(row.get("num")), "source": row["_source"],
            })
    for group_id in sorted(group_ids):
        selected = [r for r in square_rows if group_id in groups(r.get("group"))]
        square_groups[str(group_id)] = sorted(integer(row["id"]) for row in selected)
        if not square_groups[str(group_id)]:
            raise ValueError("Missing square group " + str(group_id))

    stages, used_drop_ids = {}, set()
    for seq_id in sorted(seq_ids):
        selected = sorted((r for r in stage_rows if integer(r.get("seq_id")) == seq_id),
                          key=lambda r: integer(r.get("index")))
        if not selected:
            raise ValueError("Missing stage list " + str(seq_id))
        stages[str(seq_id)] = []
        minimum = 0
        for row in selected:
            index, increment = integer(row["index"]), integer(row["single_value"])
            if increment <= 0:
                raise ValueError("Non-positive stage threshold")
            normal_drop, spare_drop = vector(row.get("drop_id"), 2), vector(row.get("spare_drop_id"), 2)
            for drop in (normal_drop, spare_drop):
                if drop:
                    used_drop_ids.add(drop[1])
            stages[str(seq_id)].append({
                "index": index, "threshold": minimum + increment, "singleValue": increment,
                "min": minimum, "max": minimum + increment,
                "rewards": rewards(row.get("reward")), "dropId": normal_drop,
                "spareRewards": rewards(row.get("reward_spare")), "spareDropId": spare_drop,
                "bigShow": integer(row.get("big_show")), "specialItem": integer(row.get("special_item")),
                "raw": {k: row.get(k) for k in ["reward", "drop_id", "reward_spare", "spare_drop_id"]},
                "source": row["_source"],
            })
            minimum += increment
        indices = [s["index"] for s in stages[str(seq_id)]]
        if len(indices) != len(set(indices)) or indices != list(range(1, len(indices) + 1)):
            raise ValueError("Stage indices are not unique contiguous indices")

    drop_groups = {}
    for row in drop_rows:
        if row.get("drop_id") is None or integer(row.get("drop_id")) not in used_drop_ids:
            continue
        activity_type, drop_id = integer(row["main_activity_type"]), integer(row["drop_id"])
        key = f"{activity_type}:{drop_id}"
        if key in drop_groups:
            raise ValueError("Duplicate drop group " + key)
        drop_groups[key] = {"activityType": activity_type, "dropId": drop_id,
                            "rewards": rewards(row.get("drop_reward")), "source": row["_source"]}

    def offline_reward(stage, spare):
        direct = stage["spareRewards" if spare else "rewards"]
        drop = stage["spareDropId" if spare else "dropId"]
        if direct:
            return [dict(x, source=stage["source"]) for x in direct], {"mode": "direct", "spare": spare}
        if not drop:
            raise ValueError(f"Unresolved stage {stage['index']}")
        key = "0:" + str(drop[1])
        if key not in drop_groups:
            raise ValueError("Missing original no-core-activity fallback: " + key)
        node = drop_groups[key]
        return [dict(x, source=node["source"]) for x in node["rewards"]], {
            "mode": "originalType0Fallback", "spare": spare, "dropRule": drop[0],
            "dropGroup": key, "source": node["source"]}
    for stage_list in stages.values():
        for stage in stage_list:
            stage["resolvedOfflineRewards"], stage["offlineResolution"] = offline_reward(stage, True)
            stage["resolvedNormalOfflineRewards"], stage["normalOfflineResolution"] = offline_reward(stage, False)

    chosen_rank = sorted((r for r in rank_rows if integer(r.get("rank_id")) == 101),
                         key=lambda r: integer(r["rank_range_id"]))
    if not chosen_rank:
        raise ValueError("Missing original rank 101")
    unlocks = {integer(r["rank_min_value"]) for r in chosen_rank}
    if len(unlocks) != 1:
        raise ValueError("Rank unlock values disagree")
    rank_reward_rows = []
    for row in chosen_rank:
        bounds = vector(row["rank_range"], 2)
        rank_reward_rows.append({
            "minRank": bounds[0], "maxRank": bounds[1], "rewards": rewards(row.get("reward")),
            "pointAdd": integer(row.get("point_add")), "pointReduce": integer(row.get("point_reduce")),
            "source": row["_source"],
        })
    rank = {"id": 101, "unlockScore": unlocks.pop(), "matchId": integer(chosen_rank[0]["match_id"]),
            "config": [dict(clean_record(r), source=r["_source"]) for r in chosen_rank],
            "rewards": rank_reward_rows, "onlineSettlementAvailable": False,
            "localPolicy": "仅列出本机真实玩家累计积分；排名奖励仅作原配置预览，不按伪造对手或本机单人第1名发放。",
            "source": chosen_rank[0]["_source"]}

    ui_skins = {}
    for skin_id in sorted(skin_ids):
        row = one(skin_rows, "skinId", skin_id)
        ui_skins[str(skin_id)] = {
            **clean_record(row), "displayName": row["_cells"][1],
            "rankBanners": str(row.get("rankBg") or "").split("|"), "source": row["_source"]}

    all_rewards = []
    for stage_list in stages.values():
        for stage in stage_list:
            all_rewards += stage["rewards"] + stage["spareRewards"] + stage["resolvedOfflineRewards"]
    for node in drop_groups.values():
        all_rewards += node["rewards"]
    for row in rank_reward_rows:
        all_rewards += row["rewards"]
    item_ids = {x["id"] for x in all_rewards if x["type"] == 2}
    items = {}
    for item_id in sorted(item_ids):
        row = one(item_rows, "id", item_id)
        items[str(item_id)] = {
            "id": item_id, "name": row["name"], "itemType": integer(row.get("type")),
            "subId": integer(row.get("son_id")), "quality": integer(row.get("quality")),
            "icon": row.get("icon"), "description": row.get("desc"),
            "useEffect": row.get("use_effect"), "useEnabled": integer(row.get("use_yn")),
            "source": row["_source"]}
    for resource in RESOURCE_TYPES.values():
        resource["source"] = {"path": "client/SHIN/Assets/Script/Game/GameEnum.cs", "line": 249}

    globals_export = {}
    for row in global_rows:
        if "MILESTONE_REWARD_DISTINGUISH_LEVEL" in row.values():
            globals_export["MILESTONE_REWARD_DISTINGUISH_LEVEL"] = {
                **clean_record(row), "source": row["_source"]}

    # In the source data, 10 points / 25 dice is stage 2, following the 5-point first stage.
    assert stages["7010001"][0]["singleValue"] == 5
    assert stages["7010001"][1]["singleValue"] == 10
    assert stages["7010001"][1]["rewards"] == [{"type": 1, "id": 2, "count": 25}]
    assert rank["unlockScore"] == 1
    return {
        "schemaVersion": 1, "channel": "CN", "timezone": "Asia/Shanghai",
        "activities": activities, "goals": goals, "squareGroups": square_groups,
        "squareGroupSources": {str(g): [r["_source"] for r in square_rows if g in groups(r.get("group"))]
                               for g in sorted(group_ids)},
        "stages": stages, "dropGroups": drop_groups, "rank": rank, "uiSkins": ui_skins,
        "items": items, "resourceTypes": RESOURCE_TYPES,
        "rewardTypes": {"1": "资源（编号见 resourceTypes）", "2": "物品（编号见 items）"},
        "globalRules": globals_export,
        "ruleNotes": {
            "scoring": "只有停留结果参与；命中 goal 后加 score × 本轮骰子倍率。goal2不因经过每格加分。",
            "stages": "singleValue为单档增量，threshold/min/max由按index升序累加得到；达到阈值自动奖励，每档只能领取一次。",
            "offlineDrop": "resolvedOfflineRewards使用原spare奖励分支；直接奖励为空时解析原drop_id到main_activity_type=0。不把未知物品替换成骰子或金币。",
            "money": "美金保留原配表基础数量，未乘玩家状态相关通胀；原服务端buildCommonDrop应用inflationService。",
            "schedule": "固定使用原国服起止时间；到期停止新积分，不在每次加载时重设倒计时。",
            "settlement": "离线仅补发已实际达到且未标记领取的阶段奖励；不得据本机单人成绩发放线上排名结算奖励。",
            "mapUnlock": "mapUnlock来自原activity_main.map_id，NoRank=3、Rank=6；若演示绕过门槛，应明确属于本地演示策略。",
        },
        "evidence": [
            {"path": "client/SHIN/Assets/Script/Game/moduls/Activity/ActivityHelper.cs", "line": 18,
             "claim": "按single_value累加形成档位范围；奖励图取当前档首个奖励"},
            {"path": "client/SHIN/Assets/Script/Game/moduls/MailStone/MileStoneData.cs", "line": 156,
             "claim": "原累计进度来自服务端bars.totalProcess"},
            {"path": "server/home/src/main/kotlin/com/youzu/crayon/home/services/MileStoneService.kt", "line": 58,
             "claim": "只计算停留结果"},
            {"path": "server/home/src/main/kotlin/com/youzu/crayon/home/services/MileStoneService.kt", "line": 122,
             "claim": "积分等于goalCfg.score乘本轮multiplier"},
            {"path": "server/home/src/main/kotlin/com/youzu/crayon/home/services/MileStoneService.kt", "line": 164,
             "claim": "直接奖励优先；活动掉落无法解析时回退原type0"},
            {"path": "server/home/src/main/kotlin/com/youzu/crayon/home/services/MileStoneService.kt", "line": 393,
             "claim": "累计跨档并以rewardFlag防重复自动发奖"},
        ],
        "sources": list(tables.sources.values()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).resolve().parents[1] / "assets/activities/config.json")
    parser.add_argument("--check", action="store_true", help="Validate source graph without writing output")
    args = parser.parse_args()
    data = export(args.workspace.resolve())
    if not args.check:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "ok": True, "written": not args.check, "output": str(args.output),
        "activityIds": [x["id"] for x in data["activities"]],
        "stageCounts": {k: len(v) for k, v in data["stages"].items()},
        "dropGroups": len(data["dropGroups"]), "items": len(data["items"]),
        "rank101Unlock": data["rank"]["unlockScore"],
    }, ensure_ascii=True))


if __name__ == "__main__":
    main()
