import sys
H,W=5,9
def cl(v):
    r,c=divmod(v,W); m=1<<v
    for rr,cc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
        if 0<=rr<H and 0<=cc<W: m|=1<<(rr*W+cc)
    return m
def play(stones):
    A=B=(1<<(H*W))-1
    for i,v in enumerate(stones):
        if i%2==0: A&=~cl(v); B&=~(1<<v)
        else: A&=~(1<<v); B&=~cl(v)
    return A,B
if __name__=='__main__':
    s=[int(x) for x in sys.argv[1:]]
    print(*play(s))
