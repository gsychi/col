// Bounded finite discovery only. Budget exhaustion is reported as unknown.
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>
using U=uint64_t;
struct Limit{};
struct Solver{
 int w,n;U visits=0,limit;std::vector<U> closed;std::unordered_map<U,bool> memo;
 Solver(int width,U budget):w(width),n(5*width),limit(budget),closed(n){
  if(n>30)throw std::runtime_error("width too large");
  for(int r=0;r<5;r++)for(int c=0;c<w;c++){
   int v=r*w+c;closed[v]=1ULL<<v;
   if(r)closed[v]|=1ULL<<(v-w);if(r<4)closed[v]|=1ULL<<(v+w);
   if(c)closed[v]|=1ULL<<(v-1);if(c<w-1)closed[v]|=1ULL<<(v+1);
  }
 }
 bool win(U a,U b){
  if(++visits>limit)throw Limit{};
  if(!a)return false;if(!b)return true;
  U key=a|(b<<n);auto it=memo.find(key);if(it!=memo.end())return it->second;
  for(U x=a;x;x&=x-1){int v=__builtin_ctzll(x);U bit=1ULL<<v;
   if(!win(b&~bit,a&~closed[v])){memo[key]=true;return true;}}
  memo[key]=false;return false;
 }
};
int main(int argc,char**argv){
 if(argc!=5&&argc!=6)return 2;
 int width=std::stoi(argv[1]);std::string p=argv[2],q=argv[3];
 if(p.size()!=5||q.size()!=5)return 2;
 Solver s(width,std::stoull(argv[4]));U a=(1ULL<<s.n)-1,b=a;
 for(int side=0;side<2;side++)for(int r=0;r<5;r++){
  int c=side?width-1:0;char x=(side?q:p)[r];U bit=1ULL<<(r*width+c);
  if(x!='o'&&x!='b')a&=~bit;if(x!='o'&&x!='w')b&=~bit;
 }
 if(argc==6){
  std::string aux=argv[5];if(aux!="minus_half"&&aux!="plus_half")return 2;
  int v=s.n;if(v+2>30)return 2;s.n+=2;s.closed.resize(s.n);
  s.closed[v]=s.closed[v+1]=(3ULL<<v);
  if(aux=="minus_half"){a|=1ULL<<(v+1);b|=3ULL<<v;}
  else{a|=3ULL<<v;b|=1ULL<<(v+1);}
 }
 try{
  bool blue=s.win(a,b),white=s.win(b,a);
  std::cout<<(blue?(white?"N":"L"):(white?"R":"P"));
 }catch(Limit&){std::cout<<"UNKNOWN";}
 std::cout<<" visits="<<s.visits<<" cache="<<s.memo.size()<<"\n";
}
