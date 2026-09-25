from pathlib import Path
import csv,glob,json,time,sys
library={}
for f in glob.glob(f'{Path(__file__).resolve().parent}/full*.csv'):
 rows=list(csv.DictReader(open(f)));h=int(rows[0]['h']);w=int(rows[0]['w'])
 good={int(r['b']) for r in rows if r['result']=='0'}
 minimal=sorted(b for b in good if all((b&~(1<<j)) not in good for j in range(h*w) if b>>j&1))
 for b in minimal:
  library[(h,w,b)]=f
  # transpose
  bt=sum(1<<(c*h+r) for r in range(h) for c in range(w) if b>>(r*w+c)&1)
  library[(w,h,bt)]=f

def tile(H,W,cap=500000):
 full=(1<<(H*W))-1
 nb=[]
 for v in range(H*W):
  r,c=divmod(v,W);nb.append(sum(1<<(rr*W+cc) for rr,cc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)) if 0<=rr<H and 0<=cc<W))
 opts=[]
 for r in range(H):
  for c in range(W):
   candidates=[]
   for h,w,b in library:
    if r+h>H or c+w>W:continue
    occ=sum(1<<((r+rr)*W+c+cc) for rr in range(h) for cc in range(w))
    wh=sum(1<<((r+rr)*W+c+cc) for rr in range(h) for cc in range(w) if b>>(rr*w+cc)&1)
    nwh=0
    for v in range(H*W):
     if wh>>v&1:nwh|=nb[v]
    candidates.append((occ,wh,nwh,(r,c,h,w,b)))
   candidates.sort(key=lambda x:-x[0].bit_count())
   opts.append(candidates)
 seen=set();vis=0
 def rec(o,b,path):
  nonlocal vis
  vis+=1
  if vis>cap:raise TimeoutError()
  if o==full:return path
  k=(o,b)
  if k in seen:return
  v=((full^o)&-(full^o)).bit_length()-1
  for occ,wh,nwh,desc in opts[v]:
   if occ&o or nwh&b:continue
   res=rec(o|occ,b|wh,path+[desc])
   if res is not None:return res
  seen.add(k)
 st=time.perf_counter()
 try:p=rec(0,0,[]);status='certified' if p else 'no_tiling_in_library'
 except TimeoutError:p=None;status='budget_exhausted'
 return {'height':H,'width':W,'status':status,'nodes':vis,'seconds':time.perf_counter()-st,'plan':p}
if __name__=='__main__':
 results=[]
 for h,w in [(3,3),(3,5),(3,7),(3,9),(3,11),(5,5),(5,7),(5,9),(5,11),(7,7),(7,9),(7,11),(9,9)]:
  r=tile(h,w);results.append(r);print(json.dumps(r),flush=True)
  json.dump(results,open(f'{Path(__file__).resolve().parent}/static_2d_results.json','w'),indent=2)
