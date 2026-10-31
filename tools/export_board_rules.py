"""Export the audited three-map board rules without changing existing exports."""
from pathlib import Path
import hashlib
import json
import re

import openpyxl

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'shin-h5/assets/board-rules.json'
BASE = ROOT / 'client/SHIN/Assets/ResourcesAssets/Config/Data/Default'
PROTO = ROOT / 'client/SHIN/Assets/ScriptGenerated/Config/temp_allinone.proto'
XLSX = ROOT / 'shin-research/3xlsx'


def varint(data, pos):
    value = shift = 0
    while pos < len(data):
        part = data[pos]
        pos += 1
        value |= (part & 127) << shift
        if not part & 128:
            return value, pos
        shift += 7
        if shift > 70:
            raise ValueError('Invalid protobuf varint')
    raise ValueError('Truncated protobuf varint')


def fields(data):
    result = {}
    pos = 0
    while pos < len(data):
        tag, pos = varint(data, pos)
        number, wire = tag >> 3, tag & 7
        if wire == 0:
            value, pos = varint(data, pos)
        elif wire == 2:
            length, pos = varint(data, pos)
            value, pos = data[pos:pos + length], pos + length
        elif wire in (1, 5):
            length = 8 if wire == 1 else 4
            value, pos = data[pos:pos + length], pos + length
        else:
            raise ValueError(f'Unsupported protobuf wire {wire}')
        result.setdefault(number, []).append(value)
    return result


def integer(row, number, default=0, bits=64):
    value = row.get(number, [default])[0]
    if not isinstance(value, int):
        raise TypeError(f'Field {number} is not an integer')
    mask = (1 << bits) - 1
    value &= mask
    return value - (1 << bits) if value >= 1 << (bits - 1) else value


def text(row, number):
    return row.get(number, [b''])[0].decode('utf-8')


def integers(row, number):
    result = []
    for value in row.get(number, []):
        if isinstance(value, int):
            result.append(value)
        else:
            pos = 0
            while pos < len(value):
                item, pos = varint(value, pos)
                result.append(item)
    return result


def rows(name):
    return [fields(row) for row in fields((BASE / (name + '.bytes')).read_bytes()).get(1, [])]


def source(path, **details):
    return {'path': path.relative_to(ROOT).as_posix(), **details}


def workbook_rows(path):
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sheet = workbook.worksheets[0]
    iterator = sheet.iter_rows(values_only=True)
    next(iterator)
    headers = next(iterator)
    result = []
    for number, values in enumerate(iterator, 3):
        if number < 7 or not values or not isinstance(values[0], (int, float)) or values[0] <= 0:
            continue
        result.append(({key: value for key, value in zip(headers, values) if key}, source(path, sheet=sheet.title, row=number)))
    workbook.close()
    return result


def vector(value, width):
    if value is None or value == '':
        return []
    parts = [int(part) for part in str(value).split(';')]
    if len(parts) != width:
        raise ValueError(f'Expected {width} values: {value}')
    return parts


def vectors(value, width):
    return [vector(part, width) for part in str(value).split('|')] if value is not None and value != '' else []


def assets(value):
    return [{'type': kind, 'id': ident, 'count': count} for kind, ident, count in vectors(value, 3) if kind and ident and count]


def byte_assets(row, field):
    result = []
    for value in row.get(field, []):
        item = fields(value)
        kind, ident, count = [integer(item, key, bits=32) for key in (1, 2, 3)]
        if kind and ident and count:
            result.append({'type': kind, 'id': ident, 'count': count})
    return result


def level_growth(name, workbook_path):
    excel = {int(row['id']): (row, ref) for row, ref in workbook_rows(workbook_path)}
    result = []
    for row in rows(name):
        level = integer(row, 1, bits=32)
        if level <= 0:
            continue
        parameters = []
        for value in row.get(2, []):
            pair = fields(value)
            ident, amount = integer(pair, 1), integer(pair, 2)
            if ident:
                parameters.append({'id': ident, 'value': amount})
        rewards = byte_assets(row, 3)
        excel_row, ref = excel[level]
        expected = [{'id': ident, 'value': amount} for ident, amount in vectors(excel_row['param'], 2) if ident]
        assert parameters == expected, ('Level attribute mismatch', name, level)
        assert rewards == assets(excel_row['reward']), ('Level reward mismatch', name, level)
        result.append({'level': level, 'parameters': parameters, 'rewards': rewards, 'source': ref})
    return {'source': source(BASE / (name + '.bytes')), 'levels': sorted(result, key=lambda item: item['level'])}


def effective_attributes(initial, growth, max_role_level):
    result = {str(key): item['baseValue'] for key, item in initial.items()}
    contribution = {}
    for row in growth['levels']:
        if row['level'] > max_role_level:
            break
        for item in row['parameters']:
            contribution[str(item['id'])] = item['value']
    for key, value in contribution.items():
        result[key] = result.get(key, 0) + value
    return result


def main():
    assert not OUT.exists() or OUT.is_file()
    server_maps = {int(row['id']): (row, ref) for row, ref in workbook_rows(XLSX / '玩法/map.xlsx')}
    maps = {}
    for row in rows('map'):
        ident = integer(row, 1, bits=32)
        if ident not in (1, 2, 3):
            continue
        raw, ref = server_maps[ident]
        high_low = vector(raw['friend_event_deduction'], 2)
        parsed = {
            'id': ident, 'baseId': integer(row, 3, bits=32), 'buildIds': integers(row, 4),
            'inflationRaw': integer(row, 5), 'inflation': integer(row, 5) / 10000,
            'fundBase': integer(row, 6), 'destroyWinGain': integer(row, 7),
            'destroyLoseGain': integer(row, 8), 'newPlayerBets': integers(row, 9),
            'isBank': bool(integer(row, 10, bits=32)), 'buildTotalCost': integer(row, 11, bits=32),
            'sameDice': int(raw['same_dice']), 'friendEventToll': int(raw['friend_event_toll']),
            'friendEventDeduction': {'first': high_low[0], 'second': high_low[1]},
            'welcomeRewards': assets(raw['welcome_reward']),
            'destroyDeduct': vector(raw['destroy_deduct'], 2),
            'robGainRanges': [{'upper': first, 'lower': second, 'weight': weight} for first, second, weight in vectors(raw['rob_gain_range'], 3)],
            'robLevelWeights': dict(zip(('big', 'middle', 'small'), vector(raw['rob_level_weight'], 3))),
            'superRobRanges': [{'upper': first, 'lower': second, 'weight': weight} for first, second, weight in vectors(raw['super_rob'], 3)],
            'initialShield': [int(part) for part in str(raw['initial_shield']).split('|')],
            'serverRaw': {key: raw[key] for key in ('same_dice', 'friend_event_toll', 'friend_event_deduction', 'welcome_reward', 'destroy_deduct', 'rob_gain_range', 'rob_level_weight', 'super_rob', 'initial_shield')},
            'source': {'clientBytes': source(BASE / 'map.bytes', fields={'destroyWinGain': 7, 'destroyLoseGain': 8, 'newPlayerBets': 9}), 'serverWorkbook': ref},
        }
        for field, key in (('inflationRaw', 'inflation'), ('fundBase', 'fund'), ('destroyWinGain', 'destroy_win_gain'), ('destroyLoseGain', 'destroy_lose_gain')):
            assert parsed[field] == int(raw[key]), (ident, field)
        assert parsed['newPlayerBets'] == [int(part) for part in str(raw['newplayer_bet']).split('|')]
        assert all(1 <= item <= 40 for item in parsed['initialShield'])
        maps[str(ident)] = parsed
    assert len(maps) == 3

    enum_file = ROOT / 'server/shared/src/main/kotlin/com/youzu/crayon/shared/PlayerParamType.kt'
    enum_text = enum_file.read_text(encoding='utf-8-sig').split('enum class PlayerParamType', 1)[1]
    names = {int(ident): name for name, ident in re.findall(r'^\s+([A-Z][A-Z0-9_]+)\((\d+)', enum_text, re.M)}
    initial = {}
    for row in rows('player_variables'):
        ident = integer(row, 1, bits=32)
        if ident <= 0:
            continue
        initial[str(ident)] = {'id': ident, 'key': names.get(ident), 'baseValue': integer(row, 4, bits=32), 'valueType': integer(row, 6, bits=32), 'source': source(BASE / 'player_variables.bytes', id=ident, field=4)}

    wanted = {'BUDDY_TRICK_DAMAGE_WEIGHT', 'GRAB_TURN_NUM_WEIGHT', 'GRAB_BIG_SUCCESS_GIVE_DOLLAR_RATIO', 'GRAB_MIDDLE_SUCCESS_GIVE_DOLLAR_RATIO', 'GRAB_SMALL_SUCCESS_GIVE_DOLLAR_RATIO', 'GRAB_SUPER_RATE', 'MAP_SHIELD_EVENT_BASE_NUM', 'BUILDING_FIXED_AMOUNT_RATIO', 'DAY_GACHA_LIMIT', 'GACHA_ONCE_CONSUME', 'BUILDING_UPGRADE_GIVE_GACHA_NUM', 'GUIDE_NO_REWARD_BUILDING', 'GUIDE_INITIALZE_BUILDING_LV_ONE', 'FIVE_BUILDING_PLAYER_LEVEL_CHANGE_VALUE'}
    globals_out = {}
    for row in rows('global_variables'):
        key = text(row, 1)
        if key not in wanted:
            continue
        globals_out[key] = {'G123': integer(row, 2, bits=32), 'CN': integer(row, 4, bits=32), 'G123Text': text(row, 3), 'CNText': text(row, 5), 'source': source(BASE / 'global_variables.bytes', key=key, fields={'G123': 2, 'G123Text': 3, 'CN': 4, 'CNText': 5})}
    assert wanted <= globals_out.keys()

    growth = {'G123': level_growth('player_level', XLSX / 'G123排期/player_level.xlsx'), 'CN': level_growth('cn_player_level', XLSX / '国服排期/CN_player_level.xlsx')}
    snapshots = {}
    for channel, table in growth.items():
        snapshots[channel] = {str(level): {key: effective_attributes(initial, table, level)[key] for key in ('20000', '20003', '20004', '20006', '20007', '20130')} for level in (1, 18, 36, 40, 160, 190, 200)}
    assert snapshots['CN']['1']['20000'] == 3
    assert snapshots['CN']['18']['20003'] == 6
    assert snapshots['CN']['36']['20004'] == 40
    assert snapshots['G123']['36']['20004'] == 30
    assert snapshots['G123']['40']['20004'] == 40
    assert snapshots['CN']['160']['20000'] == 4
    assert snapshots['CN']['200']['20004'] == 50

    data = {
        'schemaVersion': 1, 'scope': 'Existing H5 maps 1/2/3; original local configuration only',
        'maps': maps, 'playerVariables': initial, 'levelGrowth': growth, 'globals': globals_out,
        'attributeGrowth': {'levelBasis': 'maxRoleLevel', 'mode': 'basePlusLatestLevelContributionPerAttribute', 'explanation': 'Select the last eligible level row for each attribute, do not sum its rows. Add that contribution to player_variables.value. Map changes do not directly add caps; reached KB milestones update the level contribution.', 'source': {'path': 'server/home/src/main/kotlin/com/youzu/crayon/home/utils/ParamOriginInterface.kt', 'lines': [32, 55]}, 'outsideLocalScope': ['month-card origin and dependent percentage attributes are not simulated here']},
        'formulas': {
            'squareDollar': 'floor3((floor(inflationBase * (10000 + attribute[20130]) / 10000) + attribute[typeAttribute]) * bet); typeAttribute: begin=20005, coin=20006, publicUtility=20007',
            'sameDice': '(map.sameDice + attribute[20108]) * bet',
            'friendRent': '(map.friendEventToll + attribute[20008] + rentColorAttribute) * bet',
            'damage': '((win ? map.destroyWinGain : map.destroyLoseGain) + attribute[20104] + attribute[20105] when failed + attribute[20106] when revenge applies) * bet; squareAddGive then applies original upward dollar rounding',
            'fundPool': 'map.fundBase + attribute[20107] + addValue; final draw additionally follows fund_schedule, not instant full-pool claim',
            'grab': 'Select map.robGainRanges by weight, choose integer base in inclusive [lower,upper], floor base to nearest 1000 only when >=10000, then add attribute[20103]. Multiply small/middle/big by global ratio/10000 and truncate, then bet; squareAddGive applies original upward dollar rounding. Super uses map.superRobRanges only when the original timed mechanism applies.',
            'welcome': 'map.welcomeRewards plus attribute[20009] dice; preserve every original reward type/id/count',
            'rounding': 'floor3(n)=floor(n/10^max(0,digits(n)-3))*10^max(0,digits(n)-3)',
        },
        'checks': {'effectiveAttributeSnapshots': snapshots, 'clientAndWorkbookMapFieldsMatch': True, 'clientAndWorkbookLevelFieldsMatch': True},
        'evidence': {
            'protobufSchema': source(PROTO, lines={'map': [1871, 1882], 'playerLevel': [1293, 1302], 'playerVariables': [4591, 4597], 'globals': [3158, 3164]}),
            'sameDice': {'path': 'server/home/src/main/kotlin/com/youzu/crayon/home/handlers/RollDiceHandler.kt', 'line': 88},
            'squareIncomeAndRent': {'path': 'server/home/src/main/kotlin/com/youzu/crayon/home/services/RollDiceSquareService.kt', 'lines': [134, 163, 315, 338]},
            'blindBox': {'path': 'server/home/src/main/kotlin/com/youzu/crayon/home/services/BuddyTrickChessBoardSquareService.kt', 'lines': [198, 204, 237, 263, 315, 333]},
            'grabRewards': {'path': 'server/home/src/main/kotlin/com/youzu/crayon/home/services/RollDiceSquareService.kt', 'lines': [195, 221]},
            'build': {'path': 'server/home/src/main/kotlin/com/youzu/crayon/home/handlers/BuildingHandler.kt', 'lines': [43, 63, 78]},
            'welcome': {'path': 'server/home/src/main/kotlin/com/youzu/crayon/home/services/RollDiceService.kt', 'lines': [838, 846]},
            'resourceRecovery': {'path': 'server/home/src/main/kotlin/com/youzu/crayon/home/services/ResourceService.kt', 'lines': [277, 282]},
        },
    }
    inputs = [BASE / (name + '.bytes') for name in ('map', 'player_variables', 'player_level', 'cn_player_level', 'global_variables')]
    inputs += [PROTO, enum_file, XLSX / '玩法/map.xlsx', XLSX / 'G123排期/player_level.xlsx', XLSX / '国服排期/CN_player_level.xlsx']
    data['sources'] = [source(path, sha256=hashlib.sha256(path.read_bytes()).hexdigest()) for path in inputs]
    data['rentColorAttributes']={str(integer(r,1)):20120+integer(r,2)-101 for r in rows('square_group') if 101 <= integer(r,2) <= 108}
    data['gachaMeta']={str(integer(r,1)):{'isGold':bool(integer(r,5)),'shell':text(r,4)}for r in rows('gacha')if integer(r,2)==1}
    data['gachaFirst']=[int(v)for r in rows('global_variables')if text(r,1)=='GACHA_NORMAL_NO'for v in (text(r,5)or text(r,3)).split(';')if v]
    data['gachaMetaSource']='client/SHIN/Assets/ResourcesAssets/Config/Data/Default/gacha.bytes'
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({'output': OUT.relative_to(ROOT).as_posix(), 'maps': len(maps), 'baseAttributes': len(initial), 'levelRows': {key: len(value['levels']) for key, value in growth.items()}, 'checkedSnapshots': snapshots}, ensure_ascii=False))


if __name__ == '__main__':
    main()
