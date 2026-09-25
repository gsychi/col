// Exact comparisons with a canonical dyadic number in units of 1/64.
#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <numeric>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>
using U=uint64_t;struct Hash{size_t operator()(U x)const{x^=x>>30;x*=0xbf58476d1ce4e5b9ULL;x^=x>>27;x*=0x94d049bb133111ebULL;return x^(x>>31);}};struct Limit{};
struct Node{U a,b;int q;};
struct Solver{
 int h,w,n;U full,visits=0,limit;std::vector<U>nb;std::unordered_map<U,int8_t,Hash> memo;
 Solver(int h,int w,U lim):h(h),w(w),n(h*w),full((1ULL<<n)-1),limit(lim),nb(n){if(n>26)throw std::runtime_error("numeric key limited to26 cells");for(int v=0;v<n;v++){int r=v/w,c=v%w;if(r)nb[v]|=1ULL<<(v-w);if(r+1<h)nb[v]|=1ULL<<(v+w);if(c)nb[v]|=1ULL<<(v-1);if(c+1<w)nb[v]|=1ULL<<(v+1);}}
 U key(Node s){if(s.q < -1024 || s.q>=1024)throw std::runtime_error("numeric range");return s.a|(s.b<<n)|(U(s.q+1024)<<(2*n));}
 Node unkey(U k){return{k&full,(k>>n)&full,int(k>>(2*n))-1024};}
 bool hasnum(int q){return q%64!=0 || q>0;}
 int left(int q){int x=std::abs(q);return q-(q%64? (x&-x):64);}
 Node child(Node s,int v){if(v==-1)return{s.b,s.a,-left(s.q)};U bit=1ULL<<v;return{s.b&~bit,s.a&~(bit|nb[v]),-s.q};}
 std::vector<int> moves(Node s){std::vector<int>m;for(U x=s.a;x;x&=x-1)m.push_back(__builtin_ctzll(x));if(hasnum(s.q))m.push_back(-1);return m;}
 int win(Node s){if(++visits>limit)throw Limit{};U k=key(s);auto it=memo.find(k);if(it!=memo.end())return it->second;for(U x=s.a;x;x&=x-1){int v=__builtin_ctzll(x);if(win(child(s,v))==-2){memo.emplace(k,v);return v;}}if(hasnum(s.q)&&win(child(s,-1))==-2){memo.emplace(k,-1);return -1;}memo.emplace(k,-2);return -2;}
 void emit(Node root,const std::string&path){if(win(root)!=-2)throw std::runtime_error("not loss");std::vector<U>states{key(root)};std::unordered_set<U,Hash>seen{states.front()};std::vector<std::vector<std::pair<int,int>>>rs;U edges=0;
 for(size_t i=0;i<states.size();i++){Node s=unkey(states[i]);std::vector<std::pair<int,int>>vrs;for(int m:moves(s)){Node mid=child(s,m);int r=win(mid);if(r==-2)throw std::runtime_error("bad response");Node dest=child(mid,r);U k=key(dest);if(seen.insert(k).second)states.push_back(k);vrs.push_back({m,r});edges++;}rs.push_back(vrs);}
 auto record=[](std::ostream&o,Node s){int g=std::gcd(std::abs(s.q),64);o<<s.a<<','<<s.b<<','<<s.q/g<<','<<64/g;};
 std::ofstream o(path);o<<"{\"height\":"<<h<<",\"width\":"<<w<<",\"root\":[";record(o,root);o<<"],\"nodes\":[";for(size_t i=0;i<states.size();i++){if(i)o<<',';o<<'[';record(o,unkey(states[i]));o<<",[";for(size_t j=0;j<rs[i].size();j++){if(j)o<<',';o<<'['<<rs[i][j].first<<','<<rs[i][j].second<<']';}o<<"]]";}o<<"],\"edges\":"<<edges<<"}\n";
 std::cerr<<"certificate "<<path<<" checkpoints="<<states.size()<<" edges="<<edges<<'\n';}
};
int main(int argc,char**argv){try{if(argc<4)throw std::runtime_error("usage H W BUDGET [a b q_scaled OUTPUT]");Solver s(std::stoi(argv[1]),std::stoi(argv[2]),std::stoull(argv[3]));if(argc==8){s.emit({std::stoull(argv[4]),std::stoull(argv[5]),std::stoi(argv[6])},argv[7]);return 0;}std::cout<<"a,b,q_scaled,result,winning_move,visits,memo\n";U a,b;int q;while(std::cin>>a>>b>>q){if(s.memo.size()>3000000)s.memo.clear();s.visits=0;int v=-3,result=2;try{v=s.win({a,b,q});result=v==-2?0:1;}catch(Limit&){}std::cout<<a<<','<<b<<','<<q<<','<<result<<','<<v<<','<<s.visits<<','<<s.memo.size()<<std::endl;}}catch(std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
