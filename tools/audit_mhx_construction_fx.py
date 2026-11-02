"""Verify every exported FX pack against its own texture and GLSL hashes."""
from pathlib import Path
import hashlib,json,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'assets/construction'
ANALYSIS=Path(r'C:\dev\mhxcz-analysis');sys.path.insert(0,str(ANALYSIS))
from public_bundle_source import parse_catalog
catalog=parse_catalog((ANALYSIS/'remote-Base_1.4.93.1.bytes').read_bytes());catalog_bundles={b['hash']:b for b in catalog['bundles']}
apk=zipfile.ZipFile(r'C:\Users\zhfzhang\Downloads\梦幻消除战.apk')
paths=[OUT/'hammer.json',OUT/'newlook.json',OUT/'goods-boom.json',OUT/'icon-boom.json',*sorted(OUT.glob('unitfx-*.json'))]
records=[];urls={}
for path in paths:
    data=json.loads(path.read_text('utf8'));files=[];sources=[]
    for source,evidence in data['particleSources'].items():
        raw=apk.read(source)if source.startswith('assets/')else Path(source).read_bytes()
        sha=hashlib.sha256(raw).hexdigest();md5=hashlib.md5(raw).hexdigest()
        assert sha==evidence['sha256'],(path.name,source,'original bundle hash differs')
        assert md5 in catalog_bundles,(path.name,source,'bundle not in original1.4.93.1 catalog')
        assert len(raw)==catalog_bundles[md5]['size'],(path.name,source,'original catalog size differs')
        sources.append({'source':source,'sha256':sha,'md5':md5,'originalCatalogVersion':catalog['version']})
    for kind,rows in [('texture',list(data['particleTextures'].values())),('shader',[p for s in data['particleShaders'].values()for p in s['programs']])]:
        for row in rows:
            raw=(ROOT/row['url']).read_bytes();actual=hashlib.sha256(raw).hexdigest()
            assert actual==row['sha256'],(path.name,row['url'],'source hash differs')
            assert row['url']not in urls or urls[row['url']]==actual,(row['url'],'same filename differs across original packs')
            urls[row['url']]=actual;files.append({'kind':kind,'url':row['url'],'sha256':actual})
    records.append({'pack':path.name,'source':data['source'],'sourceSha256':data['sourceSha256'],'originalCatalog':data.get('originalCatalog'),'verifiedSourceBundles':sources,'systemCount':len(data['particleSettings']),'spriteRendererCount':len(data.get('spriteRenderers',{})),'shaderNames':[(s['name'],s['sourceObject'])for s in data['particleShaders'].values()],'files':files})
result={'packs':records,'uniqueFiles':len(urls),'checks':['Each JSON texture and GLSL SHA256 matches the file bytes.','A repeated path across packs has the same SHA256; shaders use the original CAB:PathID hash in the filename.','All six non-Hammer unlock packs use the same original1.4.93.1 catalog, with exact original bundle MD5/size validation.'],'remainingDifferences':['Unity native RNG, cone/sphere/donut/mesh sampling distributions, drag/noise/orbital integration and billboard/trail tessellation are not bit-identical to H5 numerical implementations.','The original GLES fragment bodies, original texture pixels and source material uniforms/blend are used. Native camera/depth/color-space and global shader phase are not fully reproduced.','MeshFilter references are null in the package SRP batches; the exact original Sprite triangles are used through the original SRPBatchingSpriteRenderer mapping. The native runtime mesh generator is not decompiled.','Source assets and deterministic H5 snapshots validate the static reconstruction; they do not establish pixel-perfect parity with an unavailable native capture at the same random seed.']}
(OUT/'fx-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'packs':len(records),'systems':sum(r['systemCount']for r in records),'uniqueFiles':len(urls)}))
