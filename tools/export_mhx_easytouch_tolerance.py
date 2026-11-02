"""Retain the original ARM64 EasyTouch constructor and distance-test evidence."""
from pathlib import Path
import hashlib,json,struct,sys
ANALYSIS=Path(r'C:\dev\mhxcz-analysis')
sys.path.insert(0,str(ANALYSIS))
import mhx_native as native

name=b'EasyTouch.dll\0';offset=native.binary.index(name)
name_va=next(offset-s['p_offset']+s['p_vaddr']for s in native.segments if s['p_offset']<=offset<s['p_offset']+s['p_filesz'])
module=next(at for at,value in native.relocs.items()if value==name_va)
pointer_count=native.rd(module+8);pointer_array=native.rd(module+16)
addresses=[native.rd(pointer_array+i*8)for i in range(pointer_count)]
def method(index):
    row=native.methods[index]
    assert native.st(native.types[row[1]][0])=='EasyTouch'
    token=row[5]&0xffffff;address=addresses[token-1]
    end=min([v for v in addresses if address<v<address+0x10000],default=address+1024)
    raw=native.binary[native.off(address):native.off(address)+(end-address)]
    instructions=[{'address':hex(i.address),'operation':i.mnemonic,'operands':i.op_str}for i in native.cs.disasm(raw,address)]
    return{'name':native.st(row[0]),'token':token,'address':hex(address),'byteLength':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'instructions':instructions}
constructor=method(101621);distance_test=method(101647)
assert constructor['name']=='.ctor'and distance_test['name']=='FingerInTolerance'
assert any(i['operation']=='str'and i['operands']=='q0, [x19, #0x30]'for i in constructor['instructions'])
assert any(i['operation']=='ldr'and i['operands']=='s2, [x0, #0x30]'for i in distance_test['instructions'])
constants_va=0x391c460;constants=native.binary[native.off(constants_va):native.off(constants_va)+16]
tolerance=struct.unpack_from('<f',constants)[0];assert tolerance==15
path=Path(__file__).resolve().parents[2]/'经验/outputs/梦幻消除战-资源核查/longtap-easytouch.json'
data=json.loads(path.read_text('utf8'))
data['nativeTolerance']={'binary':{'name':'lib/arm64-v8a/libil2cpp.so','sha256':hashlib.sha256(native.binary).hexdigest()},'metadata':{'name':'runtime-metadata.dat, repaired original header','sha256':hashlib.sha256((ANALYSIS/'metadata-repaired.dat').read_bytes()).hexdigest()},'codeGenModule':hex(module),'methodPointerCount':pointer_count,'constructor':constructor,'distanceTest':distance_test,'constantVector':{'address':hex(constants_va),'bytesHex':constants.hex(),'float32':list(struct.unpack('<4f',constants))},'stationaryTolerancePixels':tolerance,'comparison':'(position-startPosition).sqrMagnitude <= stationaryTolerance * stationaryTolerance','scope':'Original native constructor default; no Lua SetStationaryTolerance string appears in the 2055 decoded modules. Scene MonoBehaviours have stripped typetrees, so a serialized override cannot be ruled out solely from the scene typetrees.'}
path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'stationaryTolerancePixels':tolerance,'evidence':str(path),'constructor':constructor['address'],'distanceTest':distance_test['address']}))
