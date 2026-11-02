"""Export first-chapter Q NPC skeletons and exact SkeletonData import scales."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile
from PIL import Image
import UnityPy

ROOT=Path(__file__).resolve().parents[1]
APK=Path(r"C:\Users\zhfzhang\Downloads\梦幻消除战.apk")
INDEX=Path(r"C:\dev\mhxcz-analysis\scene-bundle-index.json")
OUT=ROOT/"assets/construction/scene-npcs"


def export_roles(ids,kind="scene"):
    destination=OUT if kind=="scene" else ROOT/"assets/construction/portraits"
    destination.mkdir(exist_ok=True)
    from export_mhx_construction_scene import make_index
    records=make_index()
    output={}
    with zipfile.ZipFile(APK)as archive:
        for role_id in ids:
            role=("q_npc_"if kind=="scene"else"npc_")+str(role_id)
            folder="role"if kind=="scene"else"bustrole"
            entries=[r for r in records if any(("/spines/"+folder+"/"+role+"/")in n.lower() for n in r["containers"])]
            target=destination/role;target.mkdir(exist_ok=True)
            result={"roleId":role_id,"role":role,"source":[],"material":{},"scene":{"skeletonDataScale":None,"defaultMix":None},"pages":[]}
            textures={}
            for entry in entries:
                source=entry["source"];raw=archive.read(source[4:])if source.startswith("apk:")else Path(source).read_bytes();env=UnityPy.load(raw)
                result["source"].append({"bundle":source,"sha256":hashlib.sha256(raw).hexdigest()})
                for obj in env.objects:
                    if obj.type.name=="TextAsset":
                        data=obj.read()
                        if data.m_Name in [role+".atlas",role+".skel"]:
                            text=data.m_Script.encode("utf8","surrogateescape")if isinstance(data.m_Script,str)else bytes(data.m_Script)
                            (target/data.m_Name).write_bytes(text)
                    elif obj.type.name=="Texture2D":
                        data=obj.read();textures[data.m_Name]=data.image
                    elif obj.type.name=="MonoBehaviour":
                        tree=obj.read_typetree()
                        if tree.get("m_Name")==role+"_SkeletonData":result["scene"]={"skeletonDataScale":tree["scale"],"defaultMix":tree["defaultMix"],"sourceObject":obj.assets_file.name+":"+str(obj.path_id)}
                    elif obj.type.name=="Material":
                        tree=obj.read_typetree();result["material"][tree["m_Name"]]={"floats":dict(tree["m_SavedProperties"]["m_Floats"]),"sourceObject":obj.assets_file.name+":"+str(obj.path_id)}
            atlas=(target/(role+".atlas")).read_text(encoding="utf8")
            pages=re.findall(r"(?:^|\n\n)([^\r\n]+\.png)\r?\nsize:\s*(\d+),\s*(\d+)",atlas)
            for name,width,height in pages:
                image=textures.get(Path(name).stem)
                if image is None:raise ValueError("Missing original NPC atlas texture "+role+"/"+name)
                original_size=list(image.size);authored=(int(width),int(height))
                # Unity's POT importer stretches the whole page. Original atlas
                # coordinates refer to the authored page dimensions.
                if image.size!=authored:image=image.resize(authored,Image.Resampling.LANCZOS)
                image.save(target/name)
                result["pages"].append({"file":name,"unityTextureSize":original_size,"authoredAtlasSize":list(authored),"restoredAtlasSize":image.size!=tuple(original_size),"sha256":hashlib.sha256((target/name).read_bytes()).hexdigest()})
            result["binaryUrl"]=role+"/"+role+".skel";result["atlasUrl"]=role+"/"+role+".atlas";output[role]=result
        metadata={"roles":output}
        if kind=="scene":
            for entry in records:
                if not any(n.lower().endswith("/roleshadow/common_img_shadow.png")for n in entry["containers"]):continue
                source=entry["source"];raw=archive.read(source[4:])if source.startswith("apk:")else Path(source).read_bytes();env=UnityPy.load(raw)
                for obj in env.objects:
                    if obj.type.name!="Sprite"or obj.peek_name()!="common_img_shadow":continue
                    sp=obj.read();image=sp.image;image.save(destination/"common_img_shadow.png");off=sp.m_RD.textureRectOffset;pivot=sp.m_Pivot;ppu=sp.m_PixelsToUnits
                    metadata["shadow"]={"url":"common_img_shadow.png","bounds":[(off.x-pivot.x*sp.m_Rect.width)/ppu,(off.y-pivot.y*sp.m_Rect.height)/ppu,image.width/ppu,image.height/ppu],"pixelsToUnits":ppu,"source":source,"sourceSHA256":hashlib.sha256(raw).hexdigest()}
            metadata["rules"]={"modelScale":.45,"defaultRootScale":1,"dirX":{"1":-1,"2":1},"floorLayer":{"1":3,"2":5,"3":7},"shadowLocalY":.01,"shadowScale":.45,"randomNpcMax":3,"fixedNpcMax":0,"npcAvoidDistance":2,"cameraAPP":{"orthographicSize":5.625,"min":3.125,"max":7.5,"z":-30},"grid":{"cellSize":[1,.5,1],"layout":"Isometric","basis":[[.5,.25],[-.5,.25]]}}
            lua_root=Path(r"C:\dev\mhxcz-analysis\construction-lua")
            metadata["sourceLua"]=[{"module":n,"sha256":hashlib.sha256((lua_root/n).read_bytes()).hexdigest()}for n in ["Game/MapGame/Role/BaseMapRole.lua","Game/MapGame/Role/MapRoleMgr.lua","Game/MapGame/MapGameUtils.lua","Game/MapGame/Npc/IdleNpcMgr.lua","Defines/Module/MapGameDefine.lua","Game/MapGame/Map/MapMgr.lua"]]
    (destination/("source.json"if kind=="scene"else"additional-source.json")).write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding="utf8")
    return output


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--roles",nargs="+",type=int,default=[1002,1011,1016,1028,1029,1030]);parser.add_argument("--kind",choices=["scene","portrait"],default="scene");args=parser.parse_args()
    result=export_roles(args.roles,args.kind);print(json.dumps({role:{"scale":v["scene"]["skeletonDataScale"],"pages":v["pages"]}for role,v in result.items()}))
