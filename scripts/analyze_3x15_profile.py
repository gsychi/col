"""Analyze sampled two-component states. Tree keys are exact colored graph isomorphisms.

All subtree costs are inclusive: never add them to estimate total search work.
"""
import ast
from collections import Counter
import csv
from functools import lru_cache
import json
from pathlib import Path
import sys

@lru_cache(maxsize=None)
def tree_key(text):
    codes=ast.literal_eval(text)
    points=[(x>>8,(x>>2)&63,x&3) for x in codes]
    adj=[[] for _ in points]
    for i,(r,c,t) in enumerate(points):
        for j in range(i):
            rr,cc,tt=points[j]
            if abs(r-rr)+abs(c-cc)==1 and ((~t)&(~tt)&3):
                adj[i].append(j);adj[j].append(i)
    edges=sum(map(len,adj))//2
    if edges!=len(points)-1:
        return None
    # The production component extractor guarantees connectivity.
    def rooted(i,parent):
        return str(points[i][2])+"("+"".join(sorted(rooted(j,i) for j in adj[i] if j!=parent))+")"
    remaining=set(range(len(points)))
    degree=list(map(len,adj))
    while len(remaining)>2:
        leaves=[i for i in remaining if degree[i]<=1]
        if not leaves:
            raise ValueError("disconnected/non-tree signature")
        remaining.difference_update(leaves)
        for i in leaves:
            for j in adj[i]:degree[j]-=1
    return min(rooted(i,-1) for i in remaining)

def summarize(rows):
    cores={r["core"] for r in rows}
    pairs={(r["core"],r["pair"]) for r in rows}
    charged={(r["core"],r["charge"] if r["charge"]!="oversized" else r["pair"]) for r in rows}
    tree_rows=[r for r in rows if tree_key(r["core"]) is not None]
    graph_charged={(tree_key(r["core"]) or r["core"],r["charge"] if r["charge"]!="oversized" else r["pair"]) for r in rows}
    return {"observations":len(rows),"unique_geometric_pairs":len(pairs),"unique_geometric_cores":len(cores),
        "unique_core_charge_keys":len(charged),"unique_tree_or_geometry_charge_keys":len(graph_charged),
        "tree_observations":len(tree_rows),"unique_tree_geometry_cores":len({r["core"] for r in tree_rows}),
        "unique_tree_graph_cores":len({tree_key(r["core"]) for r in tree_rows}),
        "small_size_histogram":dict(Counter(r["small_size"] for r in rows)),
        "charge_histogram":dict(Counter(r["charge"] for r in rows)),
        "balanced_column_separator_size":dict(Counter(r["separator"] for r in rows))}

if __name__=="__main__":
    source=Path(sys.argv[1])
    with source.open() as f:rows=list(csv.DictReader(f,delimiter="\t"))
    result={"source":str(source),"sampling":"Every 64th completed recursive return plus every completed subtree with >=100 counted states. Costs overlap. Raw pre-reduction states.",
        "sampled":summarize([r for r in rows if r["sampled"]=="true"]),
        "cost_100":summarize([r for r in rows if int(r["cost"])>=100]),
        "cost_1000":summarize([r for r in rows if int(r["cost"])>=1000])}
    target=source.with_suffix(".summary.json")
    target.write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
