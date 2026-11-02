"""Promote the selected 20/24 review frames without modifying their pixels."""
from pathlib import Path
import hashlib
import json
import shutil

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/scene/skins/ink'


def main():
    manifest = {'version': 1, 'generator': 'Seedance 2.5', 'atlases': {},
                'notes': 'User requested integration of the original sweeper. Atlas pixels and sequence timing are identical to the action simulator; fixed shoe anchors retain authored motion.'}
    for key, ident, count in [('sweeperSweep', 'original-sweep-20', 20),
                              ('sweeperWalk', 'original-sweeper-walk-24', 24)]:
        folder = ROOT / 'action-lab/media' / (ident + '-draft-v3')
        source = json.loads((folder / 'frames.json').read_text(encoding='utf8'))
        assert source['count'] == count
        width, height = source['width'], source['height']
        anchors, body_heights, frames = [], [], []
        atlas = Image.open(folder / source['sheets'][0]).convert('RGBA')
        for index in range(count):
            cell = Image.open(folder / 'frames' / f'{index:04d}.png').convert('RGBA')
            col, row = index % source['columns'], index // source['columns']
            crop = [col * width, row * height, width, height]
            assert atlas.crop((crop[0], crop[1], crop[0]+width, crop[1]+height)).tobytes() == cell.tobytes()
            pixels = np.asarray(cell)
            rgb = pixels[:, :, :3].astype(float)
            opaque = pixels[:, :, 3] > 200
            ys, _ = np.where(opaque)
            top, bottom = int(ys.min()), int(ys.max()+1)
            # Neutral dark shoes, excluding the warm brown broom below them.
            shoe = opaque & (rgb.mean(axis=2) < 90) & ((rgb.max(axis=2)-rgb.min(axis=2)) < 24)
            shoe[:top + round((bottom-top)*.67)] = False
            fy, fx = np.where(shoe)
            assert len(fx) > 0
            anchors.append([(int(fx.min())+int(fx.max()))/2, int(fy.max()+1)])
            body_heights.append(int(fy.max()+1)-top)
            frames.append({'crop': crop, 'row': row, 'column': col})
        anchor = np.median(anchors, axis=0).tolist()
        body_height = float(np.median(body_heights))
        for frame in frames:
            frame.update(anchor=anchor, bodyHeight=body_height)
        target = OUT / f'residents-{ident}-v1.webp'
        shutil.copyfile(folder / source['sheets'][0], target)
        manifest['atlases'][key] = {
            'url': target.name, 'size': list(atlas.size), 'frames': frames,
            'count': count, 'fps': source['fps'], 'faceRight': False,
            'columns': source['columns'], 'rows': source['rows'],
            'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
            'reviewClip': ident, 'reviewVersion': source['version'],
            'reviewFrames': str((folder / 'frames.json').relative_to(ROOT)).replace('\\', '/'),
            'sourceSha256': source['sourceSha256'],
            'sourceFrameIndices': source['sourceFrameIndices'],
            'registration': {'anchor': anchor, 'bodyHeight': body_height, 'method': 'Fixed median shoe contact and head-to-shoe height across the complete clip.'}
        }
    (OUT / 'residents-seedance-sweeper-v1.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(json.dumps({key: {'frames': a['count'], 'fps': a['fps'], 'anchor': a['registration']} for key, a in manifest['atlases'].items()}))


if __name__ == '__main__':
    main()
