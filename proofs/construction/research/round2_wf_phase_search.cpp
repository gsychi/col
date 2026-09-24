// Discovery only: exact finite minimax with a visit limit; not a certificate.
#include <cstdint>
#include <iostream>
#include <string>
#include <unordered_map>
#include <vector>
using U=uint64_t;
struct Hash{size_t operator()(U x)const{x^=x>>30;x*=0xbf58476d1ce4e5b9ULL;x^=x>>27;x*=0x94d049bb133111ebULL;return x^(x>>31);}};
struct Limit{};
struct Solver{
 int w,n; U full,visits=0,limit;std::vector<U>nb;std::unordered_map<U,bool,Hash>memo;
 Solver(int width,U lim):w(width),n(5*width),full((1ULL<<n)-1),limit(lim),nb(n){
  for(int v=0;v<n;v++){int r=v/w,c=v%w;if(r)nb[v]|=1ULL<<(v-w);if(r<4)nb[v]|=1ULL<<(v+w);if(c)nb[v]|=1ULL<<(v-1);if(c+1<w)nb[v]|=1ULL<<(v+1);}
 }
 bool win(U a,U b,int q){
  if(++visits>limit)throw Limit{};
  U key=(a|(b<<n))<<4 | U(q+8);
  auto it=memo.find(key);if(it!=memo.end())return it->second;
  for(U x=a;x;x&=x-1){int v=__builtin_ctzll(x);U bit=1ULL<<v;if(!win(b&~bit,a&~(bit|nb[v]),-q)){memo.emplace(key,true);return true;}}
  int left=0;bool option=true;
  if(q&1)left=q-1;else if(q%4)left=q-2;else if(q>0)left=q-4;else option=false;
  bool result=option&&!win(b,a,-left);memo.emplace(key,result);return result;
 }
 void masks(const std::string&p,U&a,U&b){a=b=full;std::string d="obwbo";
  for(int end=0;end<2;end++)for(int r=0;r<5;r++){char x=end?p[r]:d[r];U bit=1ULL<<(r*w+(end?w-1:0));if(x!='o'&&x!='b')a&=~bit;if(x!='o'&&x!='w')b&=~bit;}
 }
};
int main(int argc,char**argv){
 int w=std::stoi(argv[1]),column=std::stoi(argv[2]);U limit=argc>3?std::stoull(argv[3]):20000000;
 bool all=argc>4&&std::string(argv[4])=="all";
 Solver s(w,limit);std::cout<<"width,row,column,state,quarter_offset,result,visits,memo\n";
 std::vector<std::pair<std::string,std::string>>patterns={{"D","obwbo"},{"U","wbobo"},{"V","bwbob"},{"R","wobob"},{"X","bowob"},{"J","owobo"}};
 for(int row: {1,2,3})for(auto const&entry:patterns){
  if(!all&&((column%2==0&&row!=2)||(column%2!=0&&row==2)))continue;
  if(!all&&((w%2==0&&entry.first!="R"&&entry.first!="X"&&entry.first!="V")||(w%2!=0&&entry.first!="D"&&entry.first!="U"&&entry.first!="J")))continue;
  U a,b;s.masks(entry.second,a,b);int v=row*w+column;U bit=1ULL<<v;if(!(b&bit))continue;a&=~bit;b&=~(bit|s.nb[v]);
  std::vector<int> offsets=all?std::vector<int>{0,1,-4}:std::vector<int>{entry.first=="V"?-4:0};
  for(int q:offsets){
   if(s.memo.size()>5000000)s.memo.clear();s.visits=0;int result=2;
   try{result=s.win(a,b,q)?1:0;}catch(Limit&){}
   std::cout<<w<<","<<row<<","<<column<<","<<entry.first<<","<<q<<","<<result<<","<<s.visits<<","<<s.memo.size()<<std::endl;
  }
 }
}
