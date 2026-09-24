// Bounded discovery of actual opening/reply states; no proof claims from Unknown.
#define main round3_corner_discovery_main
#include "round3_corner_probe.cpp"
#undef main

int main(int argc, char** argv) {
  if(argc<5){std::cerr<<"width Blue-cell White-cell limit [next-Blue-cell]\n";return 2;}
  int n=std::stoi(argv[1]);if(n<1||n>12)return 2;
  int blue=std::stoi(argv[2]), white=std::stoi(argv[3]);
  U limit=std::stoull(argv[4]);Solver s(n,limit);U a=s.full,b=s.full;
  s.blue(a,b,blue/n,blue%n);s.white(a,b,white/n,white%n);
  if(argc>5){int next=std::stoi(argv[5]);s.blue(a,b,next/n,next%n);}
  std::cout<<"width,blue,white,a,b,actor,result,visits,memo,witness\n";
  for(int actor=0;actor<2;actor++) {
    U aa=actor?b:a,bb=actor?a:b;s.visits=0;int result=2,chosen=-1;
    try {result=s.win(aa,bb)?1:0;
      if(result==1)for(U bits=aa;bits;bits&=bits-1){int v=__builtin_ctzll(bits);U bit=1ULL<<v;
        if(!s.win(bb&~bit,aa&~s.closed[v])){chosen=v;break;}}
    }catch(Limit&){}
    std::cout<<n<<","<<blue<<","<<white<<","<<a<<","<<b<<","<<actor<<","<<result<<","<<s.visits<<","<<s.memo.size()<<","<<chosen<<std::endl;
  }
}
