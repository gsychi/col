// Discovery only: budgeted exact outcome query, no unknown-as-loss conversion.
// Standalone, fixed grid with legality masks; optional omitted White ports.
#include <algorithm>
#include <array>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <unordered_map>
#include <vector>
using U=std::uint64_t;
struct Key {U a,b; bool operator==(const Key& o) const{return a==o.a&&b==o.b;}};
struct Hash {size_t operator()(Key k)const {U x=k.a+0x9e3779b97f4a7c15ULL*(k.b+1);x^=x>>30;x*=0xbf58476d1ce4e5b9ULL;x^=x>>27;x*=0x94d049bb133111ebULL;return x^(x>>31);}};
struct Limit{};
struct Solver {
 int h,w,n;U full,budget,visits=0;std::vector<U> nb;std::unordered_map<Key,bool,Hash> memo;
 Solver(int h,int w,U budget):h(h),w(w),n(h*w),budget(budget),nb(n){if(n<1||n>63)throw std::runtime_error("Need 1<=h*w<=63");full=(U(1)<<n)-1; for(int r=0;r<h;r++)for(int c=0;c<w;c++){int v=r*w+c;for(auto [rr,cc]:std::vector<std::pair<int,int>>{{r-1,c},{r+1,c},{r,c-1},{r,c+1}})if(rr>=0&&rr<h&&cc>=0&&cc<w)nb[v]|=U(1)<<(rr*w+cc);}}
 U rotate(U a){U b=0;for(;a;a&=a-1)b|=U(1)<<(n-1-__builtin_ctzll(a));return b;}
 bool win(U a,U b){if(++visits>budget)throw Limit{};if(!a)return false;if(!b)return true;Key k{a,b};auto it=memo.find(k);if(it!=memo.end())return it->second;
 if(rotate(a)==b && (!(n&1)||!(a&(U(1)<<(n/2))))) {memo.emplace(k,false);return false;}
 std::vector<std::pair<int,int>> moves;for(U x=a;x;x&=x-1){int v=__builtin_ctzll(x);moves.push_back({-__builtin_popcountll(nb[v]&a),v});}
 // Stable low-index order breaks ties; fewer forbidden own moves first.
 std::sort(moves.begin(),moves.end(),[](auto p,auto q){return p.first!=q.first?p.first>q.first:p.second<q.second;});
 for(auto [score,v]:moves){U bit=U(1)<<v;if(!win(b&~bit,a&~(bit|nb[v]))){memo.emplace(k,true);return true;}}
 memo.emplace(k,false);return false;}
};
int main(int argc,char**argv){try{if(argc!=6)throw std::runtime_error("usage H W BUDGET LEFT_WHITE RIGHT_WHITE");int h=std::stoi(argv[1]),w=std::stoi(argv[2]);U budget=std::stoull(argv[3]),l=std::stoull(argv[4]),r=std::stoull(argv[5]);Solver s(h,w,budget);U a=s.full,b=s.full;for(int i=0;i<h;i++){if(!(l>>i&1))b&=~(U(1)<<(i*w));if(!(r>>i&1))b&=~(U(1)<<(i*w+w-1));}int result=2;try{result=s.win(a,b);}catch(Limit&){} std::cout<<"{\"h\":"<<h<<",\"w\":"<<w<<",\"left\":"<<l<<",\"right\":"<<r<<",\"blue\":"<<a<<",\"white\":"<<b<<",\"result\":"<<result<<",\"visits\":"<<s.visits<<",\"memo\":"<<s.memo.size()<<"}\n";}catch(std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
