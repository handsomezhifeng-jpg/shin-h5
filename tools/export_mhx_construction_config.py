"""Recover source construction TSVs by executing the APK's own NativeSeal.

The private password is read transiently at the native HMAC boundary. It is never
printed, serialized, or embedded here. Fast AES is cross-checked against a full
execution of the original ARM64 function for selected files.
"""
from pathlib import Path
import argparse, csv, hashlib, io, json, re, struct, tempfile, zipfile, zlib
from Crypto.Cipher import AES
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_X2, UC_ARM64_REG_X3
from native_seal_runtime import Seal, BASE

ROOT=Path(__file__).resolve().parents[1]
PREFIX='assets/SettingV2/'
COMMON={'MainQuestVo','MainQuestVoIDGroup','MainQuestScheduleVo','CommonFurnitureVo','BaseParamsVo','MatLevel','RandomRewardVo','CommonItemVo','TaskType','SoundPathVo','AvatarVo','CommonHeadIconVo','Atialas','Graphic','EnergyParamsVo'}
def selected(name):
    rel=name.removeprefix(PREFIX)
    return name.startswith(PREFIX) and name.endswith('.bytes') and (
        rel.startswith(('Data/Map/','Data/CustomHouse/','Data/Plot/Main/','Data/Guide/','Data/Goods/'))
        or rel in {'Common/PlayerExp.bytes','Common/PlayerExpIDGroup.bytes','Common/ProgressItemVo.bytes','Module/ModulePrefabs.bytes','Module/Scenes.bytes','Module/ResourcesPath.bytes','Data/Feeling/Roles.bytes','I18N/zh_CN.bytes','Goods/Currency.bytes','MainPlay/MotherPieceVo.bytes','MainPlay/PieceVo.bytes','MainPlay/FunctionalPieceVo.bytes'}
        or rel.startswith('Data/Common/') and Path(rel).stem in COMMON
        or rel.startswith('Data/Plot/') and len(Path(rel).parts)==3)

def native_parameters(seal,kind=3):
    symbol=next(s for s in seal.elf.get_section_by_name('.symtab').iter_symbols() if s.name=='hmac_sha1')
    captured=[]
    def stop_at_hmac(uc,address,size,user):
        keyptr=uc.reg_read(UC_ARM64_REG_X0);keylen=uc.reg_read(UC_ARM64_REG_X1)
        dataptr=uc.reg_read(UC_ARM64_REG_X2);datalen=uc.reg_read(UC_ARM64_REG_X3)
        if keylen!=16:raise ValueError('unexpected source NativeSeal KDF boundary')
        captured.append((bytes(uc.mem_read(keyptr,keylen)),bytes(uc.mem_read(dataptr,16))))
        uc.emu_stop()
    address=BASE+symbol['st_value']
    hook=seal.uc.hook_add(UC_HOOK_CODE,stop_at_hmac,begin=address,end=address)
    try:
        try:seal.unseal(bytes(16),kind=kind)
        except (RuntimeError,ValueError):
            if not captured:raise
    finally:seal.uc.hook_del(hook)
    if len(captured)!=1:raise ValueError('source NativeSeal KDF not reached')
    password,salt=captured[0]
    return hashlib.pbkdf2_hmac('sha1',password,salt,64,48)

def unpack(data,derived):
    if data[:4]!=bytes.fromhex('abee0803') or data[-4:]!=bytes.fromhex('abcdef05'):raise ValueError('unknown source setting wrapper')
    ciphertext=data[4:-4]
    if not ciphertext or len(ciphertext)%16:raise ValueError('invalid source AES block count')
    decoded=AES.new(derived[:32],AES.MODE_CBC,derived[32:]).decrypt(ciphertext)
    pad=decoded[-1]
    if not 1<=pad<=16 or decoded[-pad:]!=bytes([pad])*pad:raise ValueError('source PKCS7 mismatch')
    return zlib.decompress(decoded[:-pad])

def value(cell):
    if re.fullmatch(r'-?(?:0|[1-9]\d*)',cell):
        n=int(cell)
        if abs(n)<=9007199254740991:return n
    if re.fullmatch(r'-?(?:0|[1-9]\d*)\.\d+(?:[eE][+-]?\d+)?',cell):return float(cell)
    return cell

def table(raw,source):
    text=raw.decode('utf-8-sig');lines=list(csv.reader(io.StringIO(text,newline=''),delimiter='\t'))
    if len(lines)<2:raise ValueError('source TSV has no schema')
    columns,types=lines[:2]
    if len(columns)!=len(set(columns)):raise ValueError('duplicate source TSV column')
    rows=[];bad=[]
    for i,row in enumerate(lines[2:],3):
        if not row or not any(row):continue
        if len(row)>len(columns):bad.append({'line':i,'cells':len(row),'columns':len(columns)});continue
        row+=['']*(len(columns)-len(row))
        rows.append({col:(v if '/I18N/' in source and col=='Id' else value(v)) for col,v in zip(columns,row)})
    if bad:raise ValueError('source TSV column mismatch '+str(bad[:3]))
    return {'source':source,'sourceFormat':'UTF-8 TSV; declared types retained verbatim, composite IDs and list expressions remain strings','columns':columns,'declaredTypes':types,'rowCount':len(rows),'tsvSha256':hashlib.sha256(raw).hexdigest(),'rows':rows}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apk',default=r'C:\Users\zhfzhang\Downloads\梦幻消除战.apk');parser.add_argument('--output',type=Path,default=ROOT/'assets/construction/config');args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True);manifest={'apkSha256':hashlib.sha256(Path(args.apk).read_bytes()).hexdigest(),'nativeFunction':'libxlua.so!xlua_seal_apply(kind=3,encrypt=0)','loaderEvidence':{'function':'SettingModule.AESCustomLoadSetting','logicalAddress':'0x3543de8','wrapperBytesRemoved':[4,4],'decompress':'zlib'},'tables':[],'errors':[],'nativeCrossChecks':[]}
    with zipfile.ZipFile(args.apk) as apk,tempfile.TemporaryDirectory(prefix='mhx-seal-') as temporary:
        native=Path(temporary)/'libxlua.so';native.write_bytes(apk.read('lib/arm64-v8a/libxlua.so'));manifest['nativeSha256']=hashlib.sha256(native.read_bytes()).hexdigest();seal=Seal(native);derived=native_parameters(seal)
        names=sorted(n for n in apk.namelist() if selected(n))
        validation={'Data/Map/world_1/UnitInteractVo.bytes','Common/PlayerExp.bytes','Data/Common/MainQuestVo.bytes'}
        for name in names:
            rel=Path(name.removeprefix(PREFIX));wrapped=apk.read(name)
            try:
                raw=unpack(wrapped,derived)
                if rel.as_posix() in validation:
                    original=zlib.decompress(seal.unseal(wrapped[4:-4]))
                    if original!=raw:raise ValueError('native replay differs from fast decode')
                    manifest['nativeCrossChecks'].append({'source':name,'equal':True,'decodedSha256':hashlib.sha256(raw).hexdigest()})
                decoded=table(raw,name);jsonrel=rel.with_suffix('.json');tsvrel=Path('_source')/rel.with_suffix('.tsv');out=args.output/jsonrel;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(decoded,ensure_ascii=False,indent=2)+'\n',encoding='utf8');tsv=args.output/tsvrel;tsv.parent.mkdir(parents=True,exist_ok=True);tsv.write_bytes(raw)
                manifest['tables'].append({'source':name,'json':jsonrel.as_posix(),'tsv':tsvrel.as_posix(),'rows':decoded['rowCount'],'wrappedSha256':hashlib.sha256(wrapped).hexdigest(),'decodedSha256':decoded['tsvSha256']})
            except Exception as error:manifest['errors'].append({'source':name,'error':str(error)})
        (args.output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'tables':len(manifest['tables']),'rows':sum(t['rows'] for t in manifest['tables']),'nativeCrossChecks':len(manifest['nativeCrossChecks']),'errors':manifest['errors']},ensure_ascii=False))
    if manifest['errors']:raise SystemExit(1)
if __name__=='__main__':main()
