from pathlib import Path
import json,csv,glob,time
from functools import lru_cache
LIB={}
def add(h,w,a,b,source):
 for trans in (False,True):
  hh,ww=(w,h) if trans else (h,w)
  for fv in (False,True):
   for fh in (False,True):
    aa=bb=0
    for r in range(h):
     for c in range(w):
      rr,cc=(c,r) if trans else (r,c)
      if fv:rr=hh-1-rr
      if fh:cc=ww-1-cc
      if a>>(r*w+c)&1:aa|=1<<(rr*ww+cc)
      if b>>(r*w+c)&1:bb|=1<<(rr*ww+cc)
    LIB[(hh,ww,aa,bb)]=source
for f in glob.glob(f'{Path(__file__).resolve().parent}/full*.csv'):
 rows=list(csv.DictReader(open(f)));h=int(rows[0]['h']);w=int(rows[0]['w'])
 good={int(x['b']) for x in rows if x['result']=='0'}
 for b in good:
  if all((b&~(1<<j)) not in good for j in range(h*w) if b>>j&1):add(h,w,(1<<(h*w))-1,b,f)
m=json.load(open(f'{Path(__file__).resolve().parent.parent / "original_proof"}/manifest.json'))
for t in m['certificates']:add(t['height'],t['width'],*t['root'],t['file'])
LIB[(1,1,0,0)]='empty'

class Engine:
 def __init__(self,H,W):
  self.h=H;self.w=W;self.N=H*W;self.full=(1<<self.N)-1
  self.nb=[]
  for v in range(self.N):
   r,c=divmod(v,W);self.nb.append(sum(1<<(rr*W+cc) for rr,cc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)) if 0<=rr<H and 0<=cc<W))
  self.options=[]
  for r in range(H):
   for c in range(W):
    cand=[]
    for h,w,a,b in LIB:
     if r+h>H or c+w>W:continue
     occ=aa=bb=0
     for rr in range(h):
      for cc in range(w):
       bit=1<<((r+rr)*W+c+cc);loc=rr*w+cc;occ|=bit
       if a>>loc&1:aa|=bit
       if b>>loc&1:bb|=bit
     nbb=0
     for v in range(self.N):
      if bb>>v&1:nbb|=self.nb[v]
     cand.append((occ,aa,bb,nbb,(r,c,h,w,a,b)))
    cand.sort(key=lambda x:(-x[0].bit_count(),x[2].bit_count()))
    self.options.append(cand)
 def after(self,v,u):
  return self.full&~((1<<v)|(1<<u)|self.nb[v]),self.full&~((1<<v)|(1<<u)|self.nb[u])
 def plan(self,a,b,cap=100000):
  opt=[[x for x in ls if a&x[0]&~x[1]==0 and x[2]&~b==0] for ls in self.options]
  seen=set();vis=0
  def rec(o,wh,path):
   nonlocal vis
   vis+=1
   if vis>cap:raise TimeoutError()
   if o==self.full:return path
   key=(o,wh)
   if key in seen:return
   v=((self.full^o)&-(self.full^o)).bit_length()-1
   for oo,aa,bb,nbb,desc in opt[v]:
    if oo&o or nbb&wh:continue
    res=rec(o|oo,wh|bb,path+[desc])
    if res is not None:return res
   seen.add(key)
  try:res=rec(0,0,[]);status='certified' if res else 'not_found'
  except TimeoutError:res=None;status='unfinished'
  return status,res,vis

if __name__=='__main__':
 results=[]
 for H,W in [(5,5),(5,7),(5,9),(7,7),(7,9)]:
  eng=Engine(H,W);ans=[];failed=[];unfinished=[];t=time.perf_counter()
  for r in range((H+1)//2):
   for c in range((W+1)//2):
    v=r*W+c;found=None;unk=False
    us=sorted((u for u in range(H*W) if u!=v),key=lambda u:abs(u%W-c)+abs(u//W-r))
    for u in us:
     a,b=eng.after(v,u);status,p,vis=eng.plan(a,b,cap=20000)
     if status=='unfinished':unk=True
     if p is not None:found={'opening':v,'response':u,'plan':p};break
    if found:ans.append(found)
    else:failed.append(v)
    if unk:unfinished.append(v)
  result={'h':H,'w':W,'answered':len(ans),'total':len(ans)+len(failed),'failed':failed,'budget_hits':unfinished,'answers':ans,'seconds':time.perf_counter()-t}
  results.append(result);json.dump(results,open(f'{Path(__file__).resolve().parent}/adaptive_2d_results.json','w'),indent=2)
  print(H,W,len(ans),'/',len(ans)+len(failed),'failed',failed,'cap',unfinished,'time',result['seconds'],flush=True)
