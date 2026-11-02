# Offline execution of the APK-supplied xlua_seal_apply. No Android device, network, or stored key is used.
from pathlib import Path
import struct,io,zipfile,gzip
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_INVALID,UC_PROT_ALL,UcError
from unicorn.arm64_const import *
BASE=0x10000000;HEAP=0x50000000;STACK=0x70000000;STUB=0x40000000;END=0x401ff000;TLS=0x71000000
class Seal:
 def __init__(self,path):
  self.raw=Path(path).read_bytes();self.elf=ELFFile(io.BytesIO(self.raw));u=self.uc=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
  u.mem_map(BASE,0x1000000);u.mem_map(HEAP,0x4000000);u.mem_map(STACK,0x400000);u.mem_map(STUB,0x200000);u.mem_map(TLS,0x10000)
  for s in self.elf.iter_segments():
   if s['p_type']=='PT_LOAD':u.mem_write(BASE+s['p_vaddr'],s.data())
  self.cursor=HEAP;self.sizes={};self.stubnames={};self.symbols={};i=0
  symtab=self.elf.get_section_by_name('.dynsym')
  for s in symtab.iter_symbols():
   name=s.name
   if not name:continue
   if s['st_shndx']=='SHN_UNDEF':
    a=STUB+i*16;i+=1;self.symbols[name]=a;self.stubnames[a]=name;u.mem_write(a,bytes.fromhex('c0035fd6'))
   else:self.symbols[name]=BASE+s['st_value']
  for sec in self.elf.iter_sections():
   if sec['sh_type']!='SHT_RELA':continue
   ss=self.elf.get_section(sec['sh_link'])
   for r in sec.iter_relocations():
    ty=r['r_info_type'];add=r['r_addend'];val=None
    if ty==1027:val=BASE+add
    elif ty in (257,1025,1026):val=self.symbols.get(ss.get_symbol(r['r_info_sym']).name,0)+add
    if val is not None:u.mem_write(BASE+r['r_offset'],struct.pack('<Q',val))
  u.reg_write(UC_ARM64_REG_TPIDR_EL0,TLS)
  u.hook_add(UC_HOOK_CODE,self.hook,begin=STUB,end=STUB+0x1fffff)
  u.hook_add(UC_HOOK_MEM_INVALID,self.bad)
  self.calls=[]
 def alloc(self,size):
  size=max(16,int(size));a=self.cursor;self.cursor=(a+size+15)&~15
  if self.cursor>HEAP+0x4000000:raise MemoryError('native seal heap exceeded')
  self.sizes[a]=size;return a
 def readstr(self,a):
  out=bytearray()
  while len(out)<0x100000:
   c=self.uc.mem_read(a+len(out),1)[0]
   if c==0:return bytes(out)
   out.append(c)
  raise ValueError('unbounded native string')
 def bad(self,u,access,address,size,value,data):raise RuntimeError('unmapped memory '+hex(address)+' at '+hex(u.reg_read(UC_ARM64_REG_PC)))
 def hook(self,u,address,size,data):
  if address==END:u.emu_stop();return
  name=self.stubnames.get(address)
  if name is None:raise RuntimeError('unknown stub '+hex(address))
  self.calls.append(name);a=[u.reg_read(r) for r in [UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_X3]];result=0
  if name in ('malloc','calloc'):
   count=a[0]*(a[1] if name=='calloc' else 1);result=self.alloc(count)
   if name=='calloc':u.mem_write(result,bytes(count))
  elif name=='free':pass
  elif name=='realloc':
   result=self.alloc(a[1]);old=self.sizes.get(a[0],0)
   if a[0] and old:u.mem_write(result,bytes(u.mem_read(a[0],min(old,a[1]))))
  elif name in ('memcpy','__memcpy_chk','memmove'):u.mem_write(a[0],bytes(u.mem_read(a[1],a[2])));result=a[0]
  elif name=='memset':u.mem_write(a[0],bytes([a[1]&255])*a[2]);result=a[0]
  elif name=='memcmp':
   b=bytes(u.mem_read(a[0],a[2]));c=bytes(u.mem_read(a[1],a[2]));result=0 if b==c else (1 if b>c else -1)
  elif name in ('strlen','__strlen_chk'):result=len(self.readstr(a[0]))
  elif name in ('strcmp','strncmp'):
   b=self.readstr(a[0]);c=self.readstr(a[1]);b=b[:a[2]] if name=='strncmp' else b;c=c[:a[2]] if name=='strncmp' else c;result=0 if b==c else (1 if b>c else -1)
  elif name in ('__cxa_atexit','__cxa_finalize'):pass
  elif name=='__errno':result=TLS+0x100
  else:raise RuntimeError('unsupported native import '+name)
  u.reg_write(UC_ARM64_REG_X0,result&0xffffffffffffffff);u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR))
 def unseal(self,payload,kind=3,encrypt=0):
  self.cursor=HEAP;self.sizes={};self.calls=[];src=self.alloc(len(payload));self.uc.mem_write(src,payload);op=self.alloc(16);ol=self.alloc(16);self.uc.mem_write(op,bytes(16));self.uc.mem_write(ol,bytes(16))
  self.uc.reg_write(UC_ARM64_REG_SP,STACK+0x3ff000);self.uc.reg_write(UC_ARM64_REG_LR,END)
  for reg,val in zip([UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_X3,UC_ARM64_REG_X4,UC_ARM64_REG_X5],[kind,encrypt,src,len(payload),op,ol]):self.uc.reg_write(reg,val)
  self.uc.emu_start(self.symbols['xlua_seal_apply'],END+4,timeout=10000000,count=200000000)
  status=self.uc.reg_read(UC_ARM64_REG_X0)&0xffffffff;ptr=struct.unpack('<Q',self.uc.mem_read(op,8))[0];length=struct.unpack('<I',self.uc.mem_read(ol,4))[0]
  if status!=0:raise RuntimeError('native status '+str(status))
  if length>0x2000000 or not HEAP<=ptr<HEAP+0x4000000:raise ValueError('invalid native result')
  return bytes(self.uc.mem_read(ptr,length))
