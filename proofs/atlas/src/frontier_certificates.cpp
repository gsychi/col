#define main base_main
#include "base_generator.cpp"
#undef main
#include <filesystem>
int main(int argc,char**argv){
 try {if(argc!=4) throw std::invalid_argument("usage H W OUTDIR; masks on stdin");int h=std::stoi(argv[1]),w=std::stoi(argv[2]);std::string dir=argv[3];std::filesystem::create_directories(dir);std::ofstream manifest(dir+"/manifest.json");manifest<<"{\"height\":"<<h<<",\"width\":"<<w<<",\"records\":[";bool first=true;Mask b;
 Solver s(h,w);
 while(std::cin>>b){if(s.memo.size()>4000000)s.memo.clear();int v=s.win(s.full,b);std::string name="W"+std::to_string(b)+".json";bool safe=v<0;
 std::cout<<"mask="<<b<<" safe="<<safe<<" ";
 if(safe)s.emit(s.full,b,dir+"/"+name);
 else {Mask bit=Mask{1}<<v;s.emit(b&~bit,s.full&~(bit|s.neighbors[v]),dir+"/"+name);}
 if(!first)manifest<<',';first=false;manifest<<"{\"white\":"<<b<<",\"blue_first_loses\":"<<(safe?"true":"false")<<",\"blue_winning_move\":"<<v<<",\"file\":\""<<name<<"\"}";
 }
 manifest<<"]}\n";
 }catch(std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
}
