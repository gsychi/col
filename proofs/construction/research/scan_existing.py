from pathlib import Path
import sys,json,time
sys.path.insert(0,f'{Path(__file__).resolve().parent.parent / "original_proof"}')
from tiling_search import TilingSearch
s=TilingSearch()
# Add reflected copies of every verified root, with source metadata.
base=list(s.library); uniq={x[:5] for x in base}
for w,a,b,l,r,f in base:
 for fh in (False,True):
  for fv in (False,True):
   def tr(x):
    y=0
    for v in range(3*w):
     if x>>v&1:
      rr,cc=divmod(v,w);rr=2-rr if fv else rr;cc=w-1-cc if fh else cc
      y|=1<<(rr*w+cc)
    return y
   aa,bb=tr(a),tr(b)
   ll=sum(1<<r for r in range(3) if bb>>(r*w)&1)
   rr=sum(1<<r for r in range(3) if bb>>(r*w+w-1)&1)
   item=(w,aa,bb,ll,rr)
   if item not in uniq:s.library.append((*item,f+f':H{int(fh)}V{int(fv)}'));uniq.add(item)
def after(n,v,u):
 full=(1<<(3*n))-1
 def nb(v):
  r,c=divmod(v,n);z=0
  for rr,cc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
   if 0<=rr<3 and 0<=cc<n:z|=1<<(rr*n+cc)
  return z
 return full&~((1<<v)|(1<<u)|nb(v)),full&~((1<<v)|(1<<u)|nb(u))
results=[]
for n in [3,5,7,9,11,13,15,17,19,21,23,27,31,35,39]:
 t=time.perf_counter();solved=[];failed=[]
 for r in (0,1):
  for c in range((n+1)//2):
   v=r*n+c;ans=None
   # nearby replies first but try all
   us=sorted((u for u in range(3*n) if u!=v),key=lambda u:(abs(u%n-c),u))
   for u in us:
    a,b=after(n,v,u);p=s.plan(a,b,n)
    if p is not None:ans={'open':[r,c],'reply':list(divmod(u,n)),'plan':p};break
   if ans:solved.append(ans)
   else:failed.append([r,c])
 res={'n':n,'solved':len(solved),'total':n+1,'failed':failed,'answers':solved,'seconds':time.perf_counter()-t}
 results.append(res);print(n,'solved',len(solved),'/',n+1,'failed',failed,'sec',res['seconds'],flush=True)
 json.dump(results,open(f'{Path(__file__).resolve().parent}/existing_library_scan.json','w'),indent=2)
