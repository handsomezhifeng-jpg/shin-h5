"""Export original MHXC construction map assets, preserving Unity transforms.

Input packages are read only. Sprite and tilemap visibility choices remain data;
the game runtime must choose the current construction state.
"""
from pathlib import Path
import argparse, collections, hashlib, json, math, re, zipfile,os
import UnityPy
from UnityPy.helpers.MeshHelper import MeshHandler

APK = Path(r"C:\Users\zhfzhang\Downloads\梦幻消除战.apk")
DOWNLOADED = Path(r"C:\dev\mhxcz-analysis\downloaded")
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "construction"
CACHE = Path(r"C:\dev\mhxcz-analysis\scene-bundle-index.json")
MANIFEST = Path(r"C:\dev\mhxcz-analysis\remote-Base_1.4.93.1.bytes")

def strict_source_index(records):
    if not MANIFEST.exists():return records
    from mhx_public_resources import parse_catalog
    catalog=parse_catalog(MANIFEST.read_bytes());allowed={b['hash']:b['size']for b in catalog['bundles']};accepted=[];excluded=[]
    with zipfile.ZipFile(APK)as archive:
        for record in records:
            source=record['source'];path=Path(source[4:]if source.startswith('apk:')else source);key=path.parent.name if path.name=='__data'else path.stem
            if key not in allowed:excluded.append({'source':source,'reason':'bundle hash is not present in original 1.4.93.1 catalog'});continue
            raw=package_bytes(source,archive)
            if len(raw)!=allowed[key]or hashlib.md5(raw).hexdigest()!=key:raise ValueError('Source bundle differs from .1 catalog '+key)
            accepted.append(record)
    write_json(OUT/'source-version-audit.json',{'version':catalog['version'],'manifestSHA256':catalog['sha256'],'acceptedBundles':len(accepted),'excludedBundles':excluded,'hashAndSizeVerified':True})
    return accepted


def json_safe(value):
    if isinstance(value,float)and not math.isfinite(value):return 'NaN'if math.isnan(value)else'Infinity'if value>0 else'-Infinity'
    if isinstance(value,dict):return{k:str(v)if k=='m_PathID'else json_safe(v)for k,v in value.items()}
    if isinstance(value,(list,tuple)):return[json_safe(v)for v in value]
    return value

def write_json(path, value,ensure_ascii=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary=path.with_name(path.name+'.'+str(os.getpid())+'.tmp')
    temporary.write_text(json.dumps(json_safe(value), ensure_ascii=ensure_ascii, separators=(",", ":"),allow_nan=False), encoding="utf8")
    temporary.replace(path)


def package_bytes(source, archive):
    return archive.read(source[4:]) if source.startswith("apk:") else Path(source).read_bytes()


def make_index():
    if CACHE.exists():
        return strict_source_index(json.loads(CACHE.read_text(encoding="utf8")))
    records = []
    with zipfile.ZipFile(APK) as z:
        sources = ["apk:" + n for n in z.namelist() if n.startswith("assets/Bundles/Android/") and n.endswith(".bytes") and not n.endswith("Catalog.bytes")]
        sources += [str(p) for p in DOWNLOADED.rglob("__data")]
        for i, source in enumerate(sources):
            try:
                env = UnityPy.load(package_bytes(source, z))
                assets = [{"name": a.name, "external": [e.path.rsplit("/", 1)[-1] for e in a.externals]} for a in env.assets]
                containers = []
                for obj in env.objects:
                    if obj.type.name == "AssetBundle":
                        containers += [name for name, _ in obj.read().m_Container]
                records.append({"source": source, "assets": assets, "containers": containers})
            except Exception:
                pass
            if i % 500 == 0:
                print("index", i, "/", len(sources), flush=True)
    write_json(CACHE, records)
    return records


def load_environment(index, predicate):
    cab = {a["name"].lower(): r for r in index for a in r["assets"]}
    chosen = {r["source"]: r for r in index if any(predicate(n) for n in r["containers"])}
    missing = set()
    todo = list(chosen.values())
    while todo:
        r = todo.pop()
        for a in r["assets"]:
            for name in a["external"]:
                dep = cab.get(name.lower())
                if not dep:
                    missing.add(name)
                elif dep["source"] not in chosen:
                    chosen[dep["source"]] = dep
                    todo.append(dep)
    env = UnityPy.Environment()
    with zipfile.ZipFile(APK) as z:
        for r in chosen.values():
            env.load_file(package_bytes(r["source"], z), name=r["source"])
    return env, chosen, sorted(missing)


def vec(v, dims="xyz"):
    return [float(getattr(v, k)) for k in dims]


def color(v):
    return vec(v, "rgba")

def nonfinite_tile_records(prefabs):
    records=[]
    for path,prefab in prefabs.items():
        for node in prefab['nodes']:
            tilemap=node.get('tilemap')
            if not tilemap:continue
            for kind,field in [('matrices','m_TileMatrixIndex'),('colors','m_TileColorIndex')]:
                references=collections.Counter(tile[field]for _,tile in tilemap['tiles'])
                for index,values in enumerate(tilemap[kind]):
                    invalid={key:json_safe(value)for key,value in values.items()if isinstance(value,float)and not math.isfinite(value)}
                    if invalid:records.append({'prefab':path,'node':node['name'],'sourceObject':tilemap.get('sourceObject'),'kind':kind,'index':index,'fields':invalid,'tileReferences':references[index]})
    return records


def ptr_id(ptr):
    return ptr.m_PathID if ptr else 0


def affine(transform):
    p, q, s = transform.m_LocalPosition, transform.m_LocalRotation, transform.m_LocalScale
    # Column-major XY affine plus Z. X/Y quaternion components are retained in trs.
    return [(1-2*(q.y*q.y+q.z*q.z))*s.x, 2*(q.x*q.y+q.w*q.z)*s.x,
            2*(q.x*q.y-q.w*q.z)*s.y, (1-2*(q.x*q.x+q.z*q.z))*s.y, p.x, p.y, p.z]


class Exporter:
    def __init__(self, env):
        self.env = env
        self.sprites = {}
        self.meshes = {}
        self.errors = []

    def mesh(self,ptr):
        if not ptr:return None
        obj=ptr.deref();ident=hashlib.sha256((obj.assets_file.name+str(obj.path_id)).encode()).hexdigest()[:12]
        if ident not in self.meshes:
            source=ptr.read();mesh=MeshHandler(source,obj.version);mesh.process()
            self.meshes[ident]={"name":source.m_Name,"vertices":mesh.m_Vertices,"indices":mesh.m_IndexBuffer,"source":{"serializedFile":obj.assets_file.name,"pathID":str(obj.path_id)}}
        return ident

    def sprite(self, ptr):
        if not ptr:
            return None
        obj = ptr.deref()
        ident = hashlib.sha256((obj.assets_file.name+str(obj.path_id)).encode()).hexdigest()[:12]
        if ident in self.sprites:
            return ident
        s = ptr.read()
        image = s.image
        name = re.sub(r"[^\w.-]", "_", s.m_Name)
        url = "sprites/"+name+"-"+ident+".png"
        image.save(OUT / url)
        ppu = s.m_PixelsToUnits
        off = s.m_RD.textureRectOffset
        pivot = s.m_Pivot
        record = {"name": s.m_Name, "url": url, "pixelsToUnits": ppu,
                  "rect": [s.m_Rect.x,s.m_Rect.y,s.m_Rect.width,s.m_Rect.height],
                  "pivot": vec(pivot,"xy"), "textureRectOffset": vec(off,"xy"),
                  "imageSize": list(image.size),
                  "bounds": [(off.x-pivot.x*s.m_Rect.width)/ppu,(off.y-pivot.y*s.m_Rect.height)/ppu,image.width/ppu,image.height/ppu],
                  "source": {"serializedFile": obj.assets_file.name, "pathID": str(obj.path_id)}}
        mesh = MeshHandler(s.m_RD, obj.version)
        mesh.process()
        record["mesh"] = {"vertices":mesh.m_Vertices,"uv":mesh.m_UV0,"indices":mesh.m_IndexBuffer}
        self.sprites[ident] = record
        return ident

    def prefab(self, obj):
        nodes = []

        def walk(go_ptr, parent=None):
            go = go_ptr.read()
            comps = [co.component.read() for co in go.m_Component]
            transform = next((c for c in comps if type(c).__name__ == "Transform"), None)
            if not transform:
                return
            ni = len(nodes)
            node = {"name":go.m_Name,"sourceGameObjectPathID":str(go_ptr.m_PathID),"active":go.m_IsActive,"layer":go.m_Layer,"parent":parent,
                    "matrix":affine(transform),"trs":{"position":vec(transform.m_LocalPosition),"rotation":vec(transform.m_LocalRotation,"xyzw"),"scale":vec(transform.m_LocalScale)}}
            nodes.append(node)
            for comp in comps:
                cname = type(comp).__name__
                if cname == "SpriteRenderer" and comp.m_Sprite:
                    node["sprite"]={"id":self.sprite(comp.m_Sprite),"enabled":comp.m_Enabled,
                                    "color":color(comp.m_Color),"flipX":comp.m_FlipX,"flipY":comp.m_FlipY,
                                    "sortingLayer":comp.m_SortingLayer,"sortingOrder":comp.m_SortingOrder,"sortPoint":comp.m_SpriteSortPoint}
                elif cname == "SortingGroup":
                    node["sortingGroup"]={"order":comp.m_SortingOrder,"layer":comp.m_SortingLayerID}
                elif cname == "Tilemap":
                    tree = comp.object_reader.read_typetree()
                    sprite_ids = [self.sprite(v.m_Data) if v.m_Data else None for v in comp.m_TileSpriteArray]
                    node["tilemap"]={"sourceObject":comp.object_reader.assets_file.name+':'+str(comp.object_reader.path_id),"sprites":sprite_ids,"tiles":[[[p["x"],p["y"],p["z"]],v] for p,v in tree["m_Tiles"]],
                                     "matrices":[v["m_Data"] for v in tree["m_TileMatrixArray"]],
                                     "colors":[v["m_Data"] for v in tree["m_TileColorArray"]],
                                     "anchor":tree["m_TileAnchor"],"origin":tree["m_Origin"],"size":tree["m_Size"],"orientation":tree["m_TileOrientationMatrix"],"enabled":tree["m_Enabled"]}
                elif cname == "TilemapRenderer":
                    node["tilemapRenderer"]={"enabled":comp.m_Enabled,"sortingOrder":comp.m_SortingOrder,"sortingLayer":comp.m_SortingLayer}
                elif cname == "MeshRenderer":
                    node["meshRenderer"]={"enabled":comp.m_Enabled,"sortingOrder":comp.m_SortingOrder,"sortingLayer":comp.m_SortingLayer}
                elif cname == "MeshFilter":node["emissionMesh"]=self.mesh(comp.m_Mesh)
                elif cname == "MonoBehaviour":
                    tree=comp.object_reader.read_typetree()
                    if tree.get("srpBatchingGO",{}).get("m_PathID"):node["srpBatchingGOPathID"]=str(tree["srpBatchingGO"]["m_PathID"])
            for child in transform.m_Children:
                walk(child.read().m_GameObject,ni)

        walk(obj)
        by_id={n["sourceGameObjectPathID"]:n for n in nodes}
        for node in nodes:
            target=by_id.get(node.get("srpBatchingGOPathID"))
            if target is not None and node.get("sprite"):
                target["emissionMeshSprite"]=node["sprite"]["id"]
                target["emissionMeshStatus"]="MeshFilter asset reference is null; original SRPBatchingSpriteRenderer maps this MeshRenderer to the exact source Sprite mesh. Native generation method is not decompiled."
        return {"nodes":nodes}


if __name__ == "__main__":
    index = make_index()
    from mhx_public_resources import PublicBundleSource
    public=PublicBundleSource();config_asset=public.asset('MapGame/Configs/world_1/UnitViewConfig.json');config_bundle=public.catalog['bundles'][config_asset['bundleId']];config_raw=public.asset_bytes(config_asset['path']);config_env=UnityPy.load(config_raw)
    config_text=next(o.read().m_Script for o in config_env.objects if o.type.name=='TextAsset');config=json.loads(config_text)['units']
    config_source={'asset':config_asset['path'],'bundleMD5':config_bundle['hash'],'bundleSHA256':hashlib.sha256(config_raw).hexdigest(),'decodedSHA256':hashlib.sha256(config_text.encode('utf8')).hexdigest(),'catalogVersion':public.version}
    units = {k:v["prefabData"] for k,v in config.items()}
    required = {("Assets/BundleResources/"+v["prefabPath"]).lower() for v in units.values()}
    stems={re.sub(r'_skin\d+','_skin',n)for n in required}
    match=lambda n:re.sub(r'_skin\d+','_skin',n.lower())in stems or any(x in n.lower() for x in ['/roomgate','/room00','/bad_roomgate','/bad_room00'])
    env, chosen, missing = load_environment(index, match)
    print("loaded", len(chosen), "missing", missing, "objects", len(list(env.objects)), flush=True)
    (OUT / "sprites").mkdir(parents=True,exist_ok=True)
    exporter = Exporter(env)
    prefabs = {}
    # Container paths from downloaded updates occur last, taking precedence.
    lookup = {n.lower():obj for n,obj in env.container.items()}
    for n, obj in lookup.items():
        if not n.endswith(".prefab") or obj.type.name != "GameObject":
            continue
        if not match(n):
            continue
        try:
            prefabs[n.removeprefix("assets/bundleresources/")] = exporter.prefab(obj)
        except Exception as exc:
            exporter.errors.append({"prefab":n,"error":repr(exc)})
    boundRows=json.loads((OUT/'config/Data/Map/world_1/UnitBoundsVo.json').read_text('utf8'))['rows']
    unitBounds={str(r['id']):[float(n)for n in r['bounds'].split(';')]for r in boundRows}
    scene={"format":1,"units":units,"unitBounds":unitBounds,"prefabs":prefabs,"sprites":exporter.sprites,"emissionMeshes":exporter.meshes,"nonfiniteSourceValues":nonfinite_tile_records(prefabs),"unitViewConfigSource":config_source,
           "coordinateSystem":"Unity XY plane, +Y up; sprite bounds are local bottom-left x,y,width,height in original Unity units",
           "tileGrid":{"status":"source verified","cellSize":[1,.5,1],"layout":"Isometric","basis":[[0.5,0.25],[-0.5,0.25]],"source":"Game/MapGame/Map/MapMgr.lua:Init Grid.cellSize"},
           "runtimePrefabRoot":"MapMgr.AsyncLoadPrefabUnit resets loaded prefab root localPosition=0 / localRotation=identity / localScale=1; retain exported root transform as source evidence only.",
           "visibility":"Default prefab active/enabled flags only. Unit-level construction visibility and selected skin require runtime state.",
           "unresolvedUnitPrefabs":sorted({v["prefabPath"] for v in units.values() if v["prefabPath"].lower() not in prefabs}),
           "errors":exporter.errors}
    with zipfile.ZipFile(APK) as archive:
        main_scene = UnityPy.load(archive.read("assets/Bundles/Android/Base/cdc7c9c12c4a085fedae16db4fef2543.bytes"))
        cameras = []
        for obj in main_scene.objects:
            if obj.type.name == "Camera":
                camera = obj.read_typetree()
                cameras.append({"orthographic":camera["orthographic"],"orthographicSize":camera["orthographic size"],"near":camera["near clip plane"],"far":camera["far clip plane"],"cullingMask":camera["m_CullingMask"]["m_Bits"]})
        scene["packagedCameras"] = {"source":"Assets/BundleResources/Scenes/MainGame.unity","cameras":cameras,"limitation":"Packaged defaults. Runtime camera focus and zoom are not established by this scene."}
        packages = [{"source":s,"sha256":hashlib.sha256(package_bytes(s,archive)).hexdigest()} for s in chosen]
    write_json(OUT / "source-scene.json",{"apkSHA256":hashlib.sha256(APK.read_bytes()).hexdigest(),"unitViewConfigSource":config_source,"packages":packages,"missingDependencies":missing,"unresolvedUnitPrefabs":scene["unresolvedUnitPrefabs"],"exportedUnits":len(units),"exportedPrefabs":len(prefabs),"exportedSprites":len(exporter.sprites),"errors":exporter.errors})
    validation={"counts":{"sprites":len(exporter.sprites),"prefabs":len(prefabs),"units":len(units),"tileCells":sum(len(n.get("tilemap",{}).get("tiles",[]))for p in prefabs.values()for n in p["nodes"]),"spriteNodes":sum("sprite"in n for p in prefabs.values()for n in p["nodes"])},"errors":exporter.errors,"unresolvedUnitPrefabs":scene["unresolvedUnitPrefabs"],"spritePNGHashes":{s["url"]:hashlib.sha256((OUT/s["url"]).read_bytes()).hexdigest()for s in exporter.sprites.values()}}
    scene["transparencySort"]={"mode":3,"axis":[0,1,0],"source":"QualityPresets/RenderPipelineAssets-High_Renderer.asset and Medium_Renderer.asset","bundle":"apk:assets/Bundles/Android/Base/e47fcfc158a7b3d23f8b0adc68d386ed.bytes"}
    scene["excludedMainCameraLayers"]=[26]
    scene["cameraAPP"]={"x":-4.57,"y":-9.75,"orthographicSize":5.625,"min":3.125,"max":7.5,"source":"MapCameraController + Define.MapGame Android GLOBAL_APP"}
    write_json(OUT / "scene.json",scene)
    write_json(OUT / "scene-validation.json",validation)
    print("exported",len(prefabs),"prefabs",len(exporter.sprites),"sprites","errors",len(exporter.errors))
    print(exporter.errors[:5])
