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
 int h,w,n; U full,limit,visits=0;std::vector<U>nb;std::unordered_map<U,int8_t,H>memo;
 S(int a,int b,U lim):h(a),w(b),n(a*b),full((1ULL<<n)-1),limit(lim),nb(n){if(n>=32)throw std::runtime_error("too big");for(int v=0;v<n;v++){int r=v/w,c=v%w;if(r)nb[v]|=1ULL<<(v-w);if(r<h-1)nb[v]|=1ULL<<(v+w);if(c)nb[v]|=1ULL<<(v-1);if(c<w-1)nb[v]|=1ULL<<(v+1);}}
 bool win(U a,U b){if(++visits>limit)throw Limit{};if(!a)return false;if(!b)return true;U key=a|(b<<n);auto it=memo.find(key);if(it!=memo.end())return it->second;
 // Exact half-turn pairing, includes the fixed-center exclusion.
 U ra=0;for(U x=a;x;x&=x-1)ra|=1ULL<<(n-1-__builtin_ctzll(x));
 if(ra==b && (!(n&1)|| !(a>>(n/2)&1))){memo.emplace(key,0);return false;}
 for(U x=a;x;x&=x-1){int v=__builtin_ctzll(x);U bit=1ULL<<v;if(!win(b&~bit,a&~(bit|nb[v]))){memo.emplace(key,1);return true;}}
 memo.emplace(key,0);return false;}
};
int main(int argc,char**argv){int h=std::stoi(argv[1]),w=std::stoi(argv[2]);U budget=std::stoull(argv[3]);S s(h,w,budget);int q=1<<h;std::string mode=argc>4?argv[4]:"empty";std::cout<<"h,w,mode,left,right,a,b,result,visits,memo,seconds\n";
 for(int l=0;l<q;l++)for(int r=0;r<q;r++){
 U a=s.full,b=s.full; if(mode=="middle-w") a&=~(1ULL<<((h/2)*w));
 for(int i=0;i<h;i++){if(!(l>>i&1))b&=~(1ULL<<(i*w));if(!(r>>i&1))b&=~(1ULL<<(i*w+w-1));}
 // prevent runaway memory; this only discards memoized solved facts.
 if(s.memo.size()>3000000)s.memo.clear();s.visits=0;auto t=std::chrono::steady_clock::now();int out=2;try{out=s.win(a,b)?1:0;}catch(Limit&){}
 auto sec=std::chrono::duration<double>(std::chrono::steady_clock::now()-t).count();
 std::cout<<h<<","<<w<<","<<mode<<","<<l<<","<<r<<","<<a<<","<<b<<","<<out<<","<<s.visits<<","<<s.memo.size()<<","<<sec<<std::endl;
 }
}
