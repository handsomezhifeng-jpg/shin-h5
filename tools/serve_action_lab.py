"""Loopback-only action review page and explicit user-review persistence."""
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
import argparse,json,time,re
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1];LAB=ROOT/'action-lab';REVIEW=ROOT/'outputs/action-lab/reviews.json'
class LocalServer(ThreadingHTTPServer):
 allow_reuse_address=False

class Handler(SimpleHTTPRequestHandler):
 def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(LAB),**kwargs)
 def log_message(self,*args):pass
 def send_head(self):
  if not urlparse(self.path).path.lower().endswith('.mp4'):return super().send_head()
  path=Path(self.translate_path(self.path))
  if not path.is_file():self.send_error(404);return None
  size=path.stat().st_size;start=0;end=size-1;requested=self.headers.get('Range');partial=False
  if requested:
   match=re.fullmatch(r'bytes=(\d*)-(\d*)',requested.strip())
   if not match:self.send_error(416);return None
   left,right=match.groups()
   if left:start=int(left);end=min(size-1,int(right)) if right else size-1
   elif right:start=max(0,size-int(right))
   if start>=size or end<start:self.send_response(416);self.send_header('Content-Range',f'bytes */{size}');self.end_headers();return None
   partial=True
  stream=path.open('rb');stream.seek(start);self._range_remaining=end-start+1;self.send_response(206 if partial else 200);self.send_header('Content-Type','video/mp4');self.send_header('Accept-Ranges','bytes');self.send_header('Content-Length',str(self._range_remaining));self.send_header('Last-Modified',self.date_time_string(path.stat().st_mtime))
  if partial:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
  self.end_headers();return stream
 def copyfile(self,source,outputfile):
  remaining=getattr(self,'_range_remaining',None)
  if remaining is None:return super().copyfile(source,outputfile)
  while remaining:
   chunk=source.read(min(65536,remaining))
   if not chunk:break
   outputfile.write(chunk);remaining-=len(chunk)
 def end_headers(self):
  self.send_header('Cache-Control','no-cache');self.send_header('X-Content-Type-Options','nosniff');super().end_headers()
 def respond(self,value,code=200):
  raw=json.dumps(value,ensure_ascii=False).encode('utf8');self.send_response(code);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
 def do_GET(self):
  if urlparse(self.path).path=='/api/reviews':
   value=json.loads(REVIEW.read_text(encoding='utf8')) if REVIEW.exists() else {'version':1,'reviews':{}}
   self.respond(value);return
  super().do_GET()
 def do_POST(self):
  if self.path!='/api/reviews':self.respond({'error':'Unknown endpoint'},404);return
  origin=self.headers.get('Origin');expected=f'http://127.0.0.1:{self.server.server_port}'
  if origin and origin!=expected:self.respond({'error':'Local page only'},403);return
  if not self.headers.get('Content-Type','').startswith('application/json'):self.respond({'error':'JSON required'},415);return
  length=int(self.headers.get('Content-Length','0'))
  if length<1 or length>65536:self.respond({'error':'Invalid review size'},413);return
  try:
   supplied=json.loads(self.rfile.read(length));ident=str(supplied['clipId']);manifest=json.loads((LAB/'manifest.json').read_text(encoding='utf8'));clips={c['id']:c for c in manifest['clips']}
   if ident not in clips:raise ValueError('Unknown action')
   status=supplied['status']
   if status not in ['pending','approved','rework']:raise ValueError('Invalid decision')
   if status=='approved' and clips[ident]['generationStatus']!='ready':raise ValueError('Action is not ready for review')
   trim=supplied.get('trim') or {};start=max(0,int(trim.get('start',0)));end=max(start,int(trim.get('end',0)))
   review={'status':status,'note':str(supplied.get('note',''))[:8000],'trim':{'start':start,'end':end},'updatedAt':time.time(),'source':'explicit-user-review'}
   data=json.loads(REVIEW.read_text(encoding='utf8')) if REVIEW.exists() else {'version':1,'reviews':{}};data['reviews'][ident]=review;REVIEW.parent.mkdir(parents=True,exist_ok=True);tmp=REVIEW.with_suffix('.json.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8');tmp.replace(REVIEW);self.respond({'saved':True,'review':review})
  except (ValueError,KeyError,TypeError,json.JSONDecodeError) as e:self.respond({'error':str(e)},400)

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=3689);args=parser.parse_args();server=LocalServer(('127.0.0.1',args.port),Handler);print(f'Action review ready: http://127.0.0.1:{args.port}/',flush=True);server.serve_forever()
