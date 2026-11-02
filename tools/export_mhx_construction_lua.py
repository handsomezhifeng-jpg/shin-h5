"""Recover the APK's construction Lua for local comparison (no secret material saved).

Requires an existing unluac JAR. Output defaults to the private analysis directory;
only construction-related modules are decompiled. The opcode map is obtained
from the shipped runtime, not guessed or manually substituted.
"""
from pathlib import Path
import argparse, concurrent.futures, hashlib, json, re, struct, subprocess, tempfile, zipfile, zlib
from Crypto.Cipher import AES
from elftools.elf.elffile import ELFFile
from native_seal_runtime import Seal
from export_mhx_construction_config import native_parameters

OPCODES=('MOVE LOADI LOADF LOADK LOADKX LOADFALSE LFALSESKIP LOADTRUE LOADNIL GETUPVAL SETUPVAL GETTABUP GETTABLE GETI GETFIELD SETTABUP SETTABLE SETI SETFIELD NEWTABLE SELF ADDI ADDK SUBK MULK MODK POWK DIVK IDIVK BANDK BORK BXORK SHRI SHLI ADD SUB MUL MOD POW DIV IDIV BAND BOR BXOR SHL SHR MMBIN MMBINI MMBINK UNM BNOT NOT LEN CONCAT CLOSE TBC JMP EQ LT LE EQK EQI LTI LEI GTI GEI TEST TESTSET CALL TAILCALL RETURN RETURN0 RETURN1 FORLOOP FORPREP TFORPREP TFORCALL TFORLOOP SETLIST CLOSURE VARARG VARARGPREP EXTRAARG').split()

def relevant(name):
    if name.startswith('Game/Setting/Vo/') and Path(name).stem in {
        'MainQuestVo','MainQuestScheduleVo','MapIdleNpcVo','MapParamVo','UnitBoundsVo','UnitDoorVo',
        'UnitUnlockVo','UnitSkinVo','UnitSkinGroupVo','UnitInteractVo','PlotVo','PlotIndexVo',
        'PlotStandPointVo','PlotDialogueVo','PlotAnimationVo','PlotCGVo','PlotBGVo','Roles'}:return True
    return name.startswith(('Game/MapGame/','Game/MainQuest/','Game/Plot/','Game/PlotOP/','Game/UI/MainQuest/','Game/UI/Map/','Game/UI/Plot/','Game/UI/Unit31/','Game/UI/HeadTop/MainQuest/','Game/UI/HeadTop/Unit/','Game/Store/','Game/Constants/')) or name in {
        'Game/Logic/Condition/ConditionMainQuest.lua','Game/Logic/Condition/ConditionViewMainQuest.lua',
        'Game/Logic/Condition/ConditionPlotHasTargetGood.lua','Game/Auto/AutoIds.lua','Defines/Module/MapGameDefine.lua',
        'Utils/GameUtils.lua','Utils/GoodsUtils.lua','Game/Dojo/PlayerDojo.lua','Game/StartView/PlayerLevelUpDialog.lua',
        'Game/StartView/PlayerLevelDialog.lua','Game/Setting/ConfigModule.lua','Game/Main/UITitleBar.lua',
        'Game/CommonView/CommonGoodsListLight.lua','Game/CommonView/GoodsNode.lua','Game/CommonView/CommonRewardPopWinDialog.lua',
        'Game/Res/ResUtil.lua',
        'Game/Main/UITitleBarResource.lua','Game/StartView/UIHomeView.lua',
        'Game/Entry/Config.lua','Game/Entry/XAppResourceUpdater.lua','init.lua',
        'Game/Logic/Condition/ModuleOpen.lua','Game/MainPlay/Data/GlobalStates.lua'}

def parse_package(payload):
    pos=0
    def number(fmt):
        nonlocal pos
        value=struct.unpack_from(fmt,payload,pos)[0];pos+=struct.calcsize(fmt);return value
    count=number('<I');modules=[]
    if count>100000:raise ValueError('invalid source Lua module count')
    for _ in range(count):
        size=number('<H');name=payload[pos:pos+size].decode('utf8');pos+=size
        size=number('<I');content=payload[pos:pos+size];pos+=size
        path=Path(name)
        if path.is_absolute() or '..' in path.parts or len(content)!=size:raise ValueError('invalid source Lua entry')
        modules.append((name,content))
    if pos!=len(payload):raise ValueError('source Lua payload tail mismatch')
    return modules

def opcode_map(native):
    with native.open('rb') as stream:
        elf=ELFFile(stream)
        symbol=next(s for s in elf.get_section_by_name('.symtab').iter_symbols() if s.name=='luaP_opdecode')
        segment=next(p for p in elf.iter_segments() if p['p_type']=='PT_LOAD' and p['p_vaddr']<=symbol['st_value']<p['p_vaddr']+p['p_filesz'])
        stream.seek(segment['p_offset']+symbol['st_value']-segment['p_vaddr'])
        mapping=stream.read(83)
    if set(mapping)!=set(range(83)):raise ValueError('source Lua opcode map is not a permutation')
    return ''.join(f'.op {i} {OPCODES[value].lower()}\n' for i,value in enumerate(mapping))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--apk',default=r'C:\Users\zhfzhang\Downloads\梦幻消除战.apk')
    parser.add_argument('--unluac',type=Path,required=True)
    parser.add_argument('--java',default='java')
    parser.add_argument('--output',type=Path,default=Path(r'C:\dev\mhxcz-analysis\construction-lua'))
    parser.add_argument('--workers',type=int,default=6)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(args.apk) as apk,tempfile.TemporaryDirectory(prefix='mhx-lua-') as temporary:
        temporary=Path(temporary);native=temporary/'libxlua.so';native.write_bytes(apk.read('lib/arm64-v8a/libxlua.so'))
        seal=Seal(native);derived=native_parameters(seal,kind=1)
        sealed=apk.read('assets/Lua/lua.bytes')
        if sealed[:4]!=b'FTL1':raise ValueError('unknown source Lua bundle wrapper')
        decoded=AES.new(derived[:32],AES.MODE_CBC,derived[32:]).decrypt(sealed[4:]);pad=decoded[-1]
        if not 1<=pad<=16 or decoded[-pad:]!=bytes([pad])*pad:raise ValueError('source Lua PKCS7 mismatch')
        payload=zlib.decompress(decoded[:-pad]);modules=parse_package(payload)
        opmap=temporary/'opmap.txt';opmap.write_text(opcode_map(native),encoding='utf8')
        manifest={'source':'assets/Lua/lua.bytes','sourceSha256':hashlib.sha256(sealed).hexdigest(),'nativeSha256':hashlib.sha256(native.read_bytes()).hexdigest(),'unluacSha256':hashlib.sha256(args.unluac.read_bytes()).hexdigest(),'format':'Lua 5.4 custom format 0x15; original runtime luaP_opdecode; NativeSeal kind=1 + zlib','bundleModuleCount':len(modules),'modules':[],'errors':[]}
        selected=[(name,data) for name,data in modules if relevant(name)]
        def decompile(entry):
            name,data=entry
            if data[:6]!=b'\x1bLua\x54\x15':raise ValueError('unexpected source Lua bytecode header')
            standard=bytearray(data);standard[5]=0
            source=temporary/name;source.parent.mkdir(parents=True,exist_ok=True);source.write_bytes(standard)
            output=args.output/name;output.parent.mkdir(parents=True,exist_ok=True)
            result=subprocess.run([args.java,'-jar',str(args.unluac),'--opmap',str(opmap),'--rawstring','--output',str(output),str(source)],capture_output=True,timeout=90)
            if result.returncode or result.stderr or not output.exists():raise ValueError(result.stderr.decode('utf8','replace')[:400] or 'unluac did not create output')
            return {'name':name,'bytecodeSha256':hashlib.sha256(data).hexdigest(),'sourceSha256':hashlib.sha256(output.read_bytes()).hexdigest(),'sourceBytes':output.stat().st_size}
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures={executor.submit(decompile,entry):entry[0] for entry in selected}
            for future in concurrent.futures.as_completed(futures):
                try:manifest['modules'].append(future.result())
                except Exception as error:manifest['errors'].append({'name':futures[future],'error':str(error)})
        manifest['modules'].sort(key=lambda item:item['name'])
        (args.output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
        print(json.dumps({'bundleModules':len(modules),'selected':len(selected),'decompiled':len(manifest['modules']),'errors':len(manifest['errors']),'output':str(args.output)}))
        if manifest['errors']:raise SystemExit(1)

if __name__=='__main__':main()
