#!/usr/bin/env python3
"""Finite discovery only, using the separately built optimized raw solver."""
import argparse
import json
from pathlib import Path
import subprocess
from wf_white_first_check import endpoint_masks,white_move

ROOT=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--solver',default='/tmp/col-round2-raw/target/release/raw_research')
    args=parser.parse_args()
    def run(w,a,b):
        call=[args.solver,'5',str(w),str(a),str(b),'0','10000000','10']
        return json.loads(subprocess.check_output(call,text=True))
    validation=run(3,32447,30167)
    if validation['actor_wins'] is not False:raise ValueError('Known DD3 certificate disagrees')
    a,b=endpoint_masks(4,'obwbo','wobob');a,b=white_move(4,a,b,2,2)
    second=run(4,a,b)
    if second['actor_wins'] is not False:raise ValueError('Known phase R4 certificate disagrees')
    results=[]
    for p,rows in [(3,(1,3)),(4,(2,))]:
        for t in rows:
            for name,endpoint in [('R','wobob'),('X','bowob')]:
                a,b=endpoint_masks(6,'obwbo',endpoint);a,b=white_move(6,a,b,t,p)
                result=run(6,a,b)
                row={'family':name,'width':6,'p':p,'t':t,
                     'reachable_in_conditional_assembly':name!='X' or 6<=2*p-2,
                     'raw_result':result,'status':'experimental_not_independently_certified'}
                results.append(row);print(row,flush=True)
    output={'validation':[validation,second],'queries':results}
    (ROOT/'round2_wf_raw_phase_probe.json').write_text(json.dumps(output,indent=2)+'\n')

if __name__=='__main__':main()
