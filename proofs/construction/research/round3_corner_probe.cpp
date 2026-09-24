// Bounded discovery only. Independent DAG checks are required for proof claims.
#include <cstdint>
#include <iostream>
#include <string>
#include <unordered_map>
#include <vector>
using U = std::uint64_t;
struct Key { U a, b; int q; bool star; bool operator==(Key const& o) const {
  return a==o.a && b==o.b && q==o.q && star==o.star; } };
struct Hash { static U mix(U x) { x^=x>>30; x*=0xbf58476d1ce4e5b9ULL;
  x^=x>>27; x*=0x94d049bb133111ebULL; return x^(x>>31); }
  std::size_t operator()(Key const& k) const {
    return mix(k.a)^mix(k.b+0x9e3779b97f4a7c15ULL)^mix(U(k.q+128)*2+k.star); } };
struct Limit {};
struct Solver {
  int width, size; U visits=0, limit, full; std::vector<U> closed;
  std::unordered_map<Key,bool,Hash> memo;
  Solver(int w,U l):width(w),size(5*w),limit(l),full((1ULL<<size)-1),closed(size) {
    for(int v=0;v<size;v++) { int r=v/w,c=v%w; closed[v]=1ULL<<v;
      if(r)closed[v]|=1ULL<<(v-w); if(r<4)closed[v]|=1ULL<<(v+w);
      if(c)closed[v]|=1ULL<<(v-1); if(c+1<w)closed[v]|=1ULL<<(v+1); }
  }
  bool win(U a,U b,int q=0,bool star=false) {
    if(++visits>limit)throw Limit{};
    if(!(a|b))return q>0||(q==0&&star);
    Key key{a,b,q,star};auto it=memo.find(key);if(it!=memo.end())return it->second;
    for(U bits=a;bits;bits&=bits-1) { int v=__builtin_ctzll(bits); U bit=1ULL<<v;
      if(!win(b&~bit,a&~closed[v],-q,star)){memo.emplace(key,true);return true;} }
    int left=0;bool option=true;
    if(q&1)left=q-1;else if(q%4)left=q-2;else if(q>0)left=q-4;else option=false;
    bool result=(option&&!win(b,a,-left,star))||(star&&!win(b,a,-q,false));
    memo.emplace(key,result);return result;
  }
  void endpoint(U& a,U& b,int c,std::string const& p) {
    for(int r=0;r<5;r++){U bit=1ULL<<(r*width+c);if(p[r]!='o'&&p[r]!='b')a&=~bit;
      if(p[r]!='o'&&p[r]!='w')b&=~bit;}
  }
  void blue(U& a,U& b,int r,int c){int v=r*width+c;U bit=1ULL<<v;
    if(!(a&bit))throw std::runtime_error("illegal Blue move");a&=~closed[v];b&=~bit;}
  void white(U& a,U& b,int r,int c){int v=r*width+c;U bit=1ULL<<v;
    if(!(b&bit))throw std::runtime_error("illegal White move");a&=~bit;b&=~closed[v];}
};
int main(int argc,char**argv) {
  if(argc<3){std::cerr<<"width query [limit] [quarter_offset] [star]\n";return 2;}
  int n=std::stoi(argv[1]);if(n<1||n>12)return 2;
  std::string query=argv[2];U limit=argc>3?std::stoull(argv[3]):3000000;
  int q=argc>4?std::stoi(argv[4]):0;bool star=argc>5&&std::stoi(argv[5]);
  Solver s(n,limit);U a=s.full,b=s.full;
  if(query=="X")s.endpoint(a,b,n-1,"bowob");
  else if(query=="center"||query=="notch"||query=="Dcenter"||query=="Dnotch") {
    if(n<4)return 2;
    if(query[0]=='D'){s.endpoint(a,b,0,"obwbo");s.endpoint(a,b,n-1,"obwbo");}
    int k=n-3;s.blue(a,b,2,k);s.white(a,b,0,k);
    if(query=="notch"||query=="Dnotch") {
      s.white(a,b,2,k+2);
      for(int r=0;r<2;r++)for(int c=k+1;c<n;c++){U bit=1ULL<<(r*n+c);a&=~bit;b&=~bit;}
    }
  } else return 2;
  std::cout<<"width,query,actor,blue_mask,white_mask,quarter_offset,star,result,visits,memo,winning_cell\n";
  for(int actor=0;actor<2;actor++) {
    U aa=actor?b:a,bb=actor?a:b;s.visits=0;int result=2,chosen=-1;
    try {result=s.win(aa,bb,actor?-q:q,star)?1:0;
      if(result==1)for(U bits=aa;bits;bits&=bits-1){int v=__builtin_ctzll(bits);U bit=1ULL<<v;
        if(!s.win(bb&~bit,aa&~s.closed[v],actor?q:-q,star)){chosen=v;break;}}
    }catch(Limit&){}
    std::cout<<n<<","<<query<<","<<actor<<","<<a<<","<<b<<","<<q<<","<<star<<","<<result<<","<<s.visits<<","<<s.memo.size()<<","<<chosen<<std::endl;
  }
}
