"""Export only board hooks, without rebuilding background image files."""
from pathlib import Path
p=Path(__file__).with_name('inspect_board_scene.py')
s=p.read_text(encoding='utf8').split('# Parse the CURRENT source prefab')[0]
exec(compile(s,str(p),'exec'))
assert len(slots)==40 and all(v['dicePositions']for v in slots.values())
assert all(len(hook['matrixInNormalPrefab'])==16 for slot in slots.values()for hook in slot['dicePositions'])
print('Verified 40 original _DicePositionList hooks; all contain Root Y45, exclude MainCityRoot/Chessboard scale0.9.')