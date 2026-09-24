// Exact normal-play Col scans. Nothing is inferred from a timed-out root.
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <string>
#include <stdexcept>
#include <unordered_map>
#include <vector>
using U=uint64_t;
struct H{size_t operator()(U x)const{x^=x>>30;x*=0xbf58476d1ce4e5b9ULL;x^=x>>27;x*=0x94d049bb133111ebULL;return x^(x>>31);}};
struct Limit{};
struct S{
 int h,w,n;U full,limit,visits=0; std::vector<U>nb;std::unordered_map<U,int8_t,H>memo;
 S(int hh,int ww,U lim):h(hh),w(ww),n(hh*ww),full((1ULL<<n)-1),limit(lim),nb(n){if(n>=32)throw std::runtime_error("max31cells");for(int v=0;v<n;v++){int r=v/w,c=v%w;if(r)nb[v]|=1ULL<<(v-w);if(r+1<h)nb[v]|=1ULL<<(v+w);if(c)nb[v]|=1ULL<<(v-1);if(c+1<w)nb[v]|=1ULL<<(v+1);}}
 int win(U a,U b){if(++visits>limit)throw Limit{};if(!a)return -1;if(!b)return __builtin_ctzll(a);U key=a|(b<<n);auto it=memo.find(key);if(it!=memo.end())return it->second;
 for(U x=a;x;x&=x-1){int v=__builtin_ctzll(x);U bit=1ULL<<v;if(win(b&~bit,a&~(bit|nb[v]))<0){memo.emplace(key,v);return v;}}
 memo.emplace(key,-1);return -1;}
};
int main(int argc,char**argv){
 try{if(argc<5)throw std::runtime_error("usage H W per_root_node_budget perimeter|ports|full|query");int h=std::stoi(argv[1]),w=std::stoi(argv[2]);U budget=std::stoull(argv[3]);std::string mode=argv[4];S s(h,w,budget);
 std::cout<<"h,w,a,b,result,winning_move,visits,memo,seconds\n";
 auto solve=[&](U a,U b){if(s.memo.size()>4000000)s.memo.clear();s.visits=0;auto t=std::chrono::steady_clock::now();int result=2,v=-2;try{v=s.win(a,b);result=v>=0?1:0;}catch(Limit&){};double dt=std::chrono::duration<double>(std::chrono::steady_clock::now()-t).count();std::cout<<h<<','<<w<<','<<a<<','<<b<<','<<result<<','<<v<<','<<s.visits<<','<<s.memo.size()<<','<<dt<<std::endl;};
 if(mode=="query"){U a,b;while(std::cin>>a>>b)solve(a,b);return 0;}
 std::vector<int> border;U inside=0;
 for(int v=0;v<h*w;v++){int r=v/w,c=v%w;bool selectable=(mode=="full") || (mode=="ports"?(c==0||c+1==w):(r==0||r+1==h||c==0||c+1==w));if(selectable)border.push_back(v);else inside|=1ULL<<v;}
 if(border.size()>24)throw std::runtime_error("too many roots");
 for(U sel=0;sel<(1ULL<<border.size());sel++){U b=inside;for(size_t j=0;j<border.size();j++)if(sel>>j&1)b|=1ULL<<border[j];solve(s.full,b);}
 }catch(std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
}
