// Discovery/export only. round4_bridge_check.py independently verifies the DAG.
#define main round3_corner_discovery_main
#include "round3_corner_probe.cpp"
#undef main
#include <fstream>

int main(int argc, char** argv) {
  if(argc!=3){std::cerr<<"odd-width output-json\n";return 2;}
  int n=std::stoi(argv[1]);if(n<3||n>11||n%2==0)return 2;
  Solver s(n,1000000000);U a=s.full,b=s.full;
  s.blue(a,b,2,n/2);s.white(a,b,0,0);
  if(s.win(a,b)){std::cerr<<"Not a loss\n";return 1;}
  std::vector<Key> states{{a,b,0,false}};
  std::unordered_map<Key,int,Hash> indices;indices.emplace(states[0],0);
  std::ofstream out(argv[2]);
  out<<"{\"height\":5,\"width\":"<<n<<",\"root\":["<<a<<","<<b<<"],\"nodes\":[";
  U edges=0;
  for(std::size_t i=0;i<states.size();i++) {
    Key state=states[i];if(i)out<<",";
    out<<"["<<state.a<<","<<state.b<<",[";bool comma=false;
    for(U bits=state.a;bits;bits&=bits-1) {
      int v=__builtin_ctzll(bits);U bit=1ULL<<v;
      U mid_a=state.b&~bit,mid_b=state.a&~s.closed[v];int reply=-1;Key child{};
      for(U options=mid_a;options;options&=options-1) {
        int u=__builtin_ctzll(options);U ubit=1ULL<<u;
        child={mid_b&~ubit,mid_a&~s.closed[u],0,false};
        if(!s.win(child.a,child.b)){reply=u;break;}
      }
      if(reply<0){std::cerr<<"No reply\n";return 1;}
      if(!indices.count(child)){indices.emplace(child,states.size());states.push_back(child);}
      if(comma)out<<",";comma=true;
      out<<"["<<v<<","<<reply<<"]";edges++;
    }
    out<<"]]";
  }
  out<<"],\"edges\":"<<edges<<"}\n";
  std::cout<<"nodes="<<states.size()<<" edges="<<edges<<" visits="<<s.visits<<std::endl;
}
