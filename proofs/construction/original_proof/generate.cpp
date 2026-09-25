// Plain exhaustive minimax. The Python verifier does not trust this program.
// Build: c++ -O2 -std=c++17 generate.cpp -o generate
// Usage: ./generate HEIGHT WIDTH BLUE_MASK WHITE_MASK output.json
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>
using Mask = std::uint64_t;

struct Hash {
    std::size_t operator()(Mask x) const noexcept {
        x ^= x >> 30; x *= 0xbf58476d1ce4e5b9ULL;
        x ^= x >> 27; x *= 0x94d049bb133111ebULL;
        return static_cast<std::size_t>(x ^ (x >> 31));
    }
};
class Solver {
public:
    int h, w, n;
    Mask full, visits = 0;
    std::vector<Mask> neighbors;
    std::unordered_map<Mask, int, Hash> memo;
    Solver(int height, int width) : h(height), w(width), n(height*width) {
        if (h < 1 || w < 1 || n >= 32) throw std::invalid_argument("Need 1 <= h*w < 32");
        full=(Mask{1}<<n)-1;
        neighbors.resize(n);
        for (int v=0; v<n; ++v) {
            int r=v/w, c=v%w;
            if(r>0) neighbors[v] |= Mask{1}<<(v-w);
            if(r+1<h) neighbors[v] |= Mask{1}<<(v+w);
            if(c>0) neighbors[v] |= Mask{1}<<(v-1);
            if(c+1<w) neighbors[v] |= Mask{1}<<(v+1);
        }
    }
    static int first(Mask x) {
        if (!x) throw std::logic_error("first(0)");
        int v=0; while ((x&1)==0) { x >>= 1; ++v; } return v;
    }
    Mask key(Mask a, Mask b) const { return a | (b<<n); }
    // -1 means the player to move loses; otherwise return a winning move.
    int win(Mask current, Mask other) {
        ++visits;
        if(!current) return -1;
        if(!other) return first(current);
        Mask k=key(current,other);
        auto it=memo.find(k); if(it!=memo.end()) return it->second;
        for(Mask z=current; z; z &= z-1) {
            int v=first(z); Mask bit=Mask{1}<<v;
            if(win(other&~bit,current&~(bit|neighbors[v]))<0) {
                memo.emplace(k,v); return v;
            }
        }
        memo.emplace(k,-1); return -1;
    }
    void emit(Mask blue, Mask white, const std::string& output) {
        if ((blue&~full) || (white&~full)) throw std::invalid_argument("Mask outside tile");
        if(win(blue,white)>=0) throw std::runtime_error("Requested tile is not Blue-first losing");
        std::vector<Mask> states{key(blue,white)};
        std::unordered_set<Mask,Hash> seen{states.front()};
        std::vector<std::vector<int>> responses;
        std::uint64_t edge_count=0;
        for(std::size_t i=0;i<states.size();++i) {
            Mask a=states[i]&full, b=states[i]>>n;
            std::vector<int> rs;
            for(Mask z=a;z;z&=z-1) {
                int v=first(z); Mask bit=Mask{1}<<v;
                Mask a1=a&~(bit|neighbors[v]), b1=b&~bit;
                int r=win(b1,a1);
                if(r<0) throw std::logic_error("No response at purported losing node");
                rs.push_back(r); ++edge_count;
                Mask rb=Mask{1}<<r;
                Mask child=key(a1&~rb,b1&~(rb|neighbors[r]));
                if(seen.insert(child).second) states.push_back(child);
            }
            responses.push_back(std::move(rs));
        }
        std::ofstream out(output);
        if(!out) throw std::runtime_error("Cannot open output file");
        out<<"{\"height\":"<<h<<",\"width\":"<<w<<",\"root\":["<<blue<<","<<white<<"],\"nodes\":[";
        for(std::size_t i=0;i<states.size();++i) {
            if(i)out<<",";
            out<<"["<<(states[i]&full)<<","<<(states[i]>>n)<<",[";
            for(std::size_t j=0;j<responses[i].size();++j) {
                if(j)out<<","; out<<responses[i][j];
            }
            out<<"]]";
        }
        out<<"]}\n";
        if(!out) throw std::runtime_error("Writing certificate failed");
        std::cout<<"checkpoints="<<states.size()<<" edges="<<edge_count
                 <<" minimax_calls="<<visits<<" memo_entries="<<memo.size()<<"\n";
    }
};
int main(int argc,char**argv) {
    try {
        if(argc!=6) throw std::invalid_argument("Usage: generate HEIGHT WIDTH BLUE_MASK WHITE_MASK OUTPUT.json");
        Solver s(std::stoi(argv[1]),std::stoi(argv[2]));
        s.emit(std::stoull(argv[3]),std::stoull(argv[4]),argv[5]);
        return 0;
    } catch(const std::exception& e) {
        std::cerr<<e.what()<<"\n"; return 1;
    }
}
