"""Read-only source check of construction tables and Lua against the supplied APK.

NativeSeal parameters are recovered into process memory from the original native
library. No key, salt, endpoint, or decrypted unrelated configuration is recorded.
"""
from pathlib import Path
import argparse,hashlib,json,tempfile,zipfile,zlib
from Crypto.Cipher import AES
from native_seal_runtime import Seal
from export_mhx_construction_config import native_parameters,unpack,table
from export_mhx_construction_lua import parse_package

ROOT=Path(__file__).resolve().parents[1]
digest=lambda raw:hashlib.sha256(raw).hexdigest()

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--apk',type=Path,default=Path(r'C:\Users\zhfzhang\Downloads\梦幻消除战.apk'))
 parser.add_argument('--config',type=Path,default=ROOT/'assets/construction/config')
 parser.add_argument('--lua',type=Path,default=Path(r'C:\dev\mhxcz-analysis\construction-lua'))
 parser.add_argument('--bytecode',type=Path,default=Path(r'C:\dev\mhxcz-analysis\decompiled-lua'))
 parser.add_argument('--output',type=Path,default=ROOT/'outputs/construction-audit/config-source-audit.json')
 args=parser.parse_args();manifest=json.loads((args.config/'manifest.json').read_text('utf8'));lua_manifest=json.loads((args.lua/'manifest.json').read_text('utf8'));issues=[];tables=[];modules=[]
 with args.apk.open('rb')as stream:apk_sha=hashlib.file_digest(stream,'sha256').hexdigest()
 if apk_sha!=manifest['apkSha256']:issues.append({'kind':'apk-sha256'})
 with zipfile.ZipFile(args.apk)as archive,tempfile.TemporaryDirectory(prefix='mhx-source-audit-')as temporary:
  native=Path(temporary)/'libxlua.so';native.write_bytes(archive.read('lib/arm64-v8a/libxlua.so'));native_sha=digest(native.read_bytes());seal=Seal(native);parameters=native_parameters(seal)
  if native_sha!=manifest['nativeSha256']or native_sha!=lua_manifest['nativeSha256']:issues.append({'kind':'native-runtime-sha256'})
  for record in manifest['tables']:
   source=record['source'];wrapped=archive.read(source);raw=unpack(wrapped,parameters);decoded=table(raw,source);exported=json.loads((args.config/record['json']).read_text('utf8'));tsv=(args.config/record['tsv']).read_bytes();checks={'wrappedSha256':digest(wrapped)==record['wrappedSha256'],'decodedSha256':digest(raw)==record['decodedSha256'],'tsvBytes':raw==tsv,'jsonSource':exported['source']==source,'jsonColumns':exported['columns']==decoded['columns'],'jsonTypes':exported['declaredTypes']==decoded['declaredTypes'],'jsonRows':exported['rows']==decoded['rows'],'jsonDecodedHash':exported['tsvSha256']==digest(raw)}
   failed=[key for key,passed in checks.items()if not passed]
   if failed:issues.append({'kind':'config-source-mismatch','source':source,'checks':failed})
   tables.append({'source':source,'json':record['json'],'rows':len(decoded['rows']),'wrappedSha256':digest(wrapped),'decodedSha256':digest(raw),'ok':not failed})
  sealed=archive.read('assets/Lua/lua.bytes')
  if digest(sealed)!=lua_manifest['sourceSha256']:issues.append({'kind':'lua-package-sha256'})
  parameters=native_parameters(seal,kind=1);decoded=AES.new(parameters[:32],AES.MODE_CBC,parameters[32:]).decrypt(sealed[4:]);padding=decoded[-1]
  if not 1<=padding<=16 or decoded[-padding:]!=bytes([padding])*padding:raise ValueError('Original Lua padding failed')
  original=dict(parse_package(zlib.decompress(decoded[:-padding])))
  bytecode_counts={'originalExact':0,'formatByteNormalized':0,'mismatch':0,'missing':0}
  for name,raw in original.items():
   path=args.bytecode/name
   if not path.exists():bytecode_counts['missing']+=1;issues.append({'kind':'cached-bytecode-missing','module':name});continue
   cached=path.read_bytes();normalized=bytearray(raw);normalized[5]=0
   if cached==raw:bytecode_counts['originalExact']+=1
   elif cached==normalized:bytecode_counts['formatByteNormalized']+=1
   else:bytecode_counts['mismatch']+=1;issues.append({'kind':'cached-bytecode-mismatch','module':name})
  for record in lua_manifest['modules']:
   raw=original.get(record['name']);readable=args.lua/record['name'];ok=raw is not None and digest(raw)==record['bytecodeSha256']and readable.exists()and digest(readable.read_bytes())==record['sourceSha256']
   if not ok:issues.append({'kind':'readable-lua-source-mismatch','module':record['name']})
   modules.append({'name':record['name'],'bytecodeSha256':record['bytecodeSha256'],'sourceSha256':record['sourceSha256'],'ok':ok})
 report={'ok':not issues,'apkSha256':apk_sha,'nativeSha256':native_sha,'scope':'Freshly unwrap exact embedded APK SettingV2 and Lua bytes; compare all exported table cells/raw TSVs and Lua bytecode/source hashes. Downloaded asset caches are never inputs. Secret material remains only in process memory.','summary':{'tables':len(tables),'rows':sum(row['rows']for row in tables),'luaPackageModules':len(original),'luaReadableModules':len(modules),'bytecode':bytecode_counts,'issues':len(issues)},'tables':tables,'lua':{'source':'assets/Lua/lua.bytes','sourceSha256':digest(sealed),'modules':modules},'issues':issues}
 args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'ok':report['ok'],**report['summary'],'output':str(args.output)}));raise SystemExit(0 if report['ok']else 1)

if __name__=='__main__':main()
