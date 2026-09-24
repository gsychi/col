#!/usr/bin/env python3
"""Selected finite discovery values, separate from independently checked claims."""
from pathlib import Path
import json
from round2_wf_caps import numerical_solver
from round4_wf_caps_probe import cap,restrict
from wf_white_first_check import endpoint_masks,white_move
from round2_wf_check import blue_move
ROOT=Path(__file__).resolve().parent
out=[]
# Adjacent inner-row cap on F_X(n,n-2,2), c=n-3.
a,b=restrict(3,*cap(3,'X',1,2,1),'owobo')
value,star=numerical_solver(3)(a,b)
out.append(dict(label='adjacent_X_J_cap',width=3,A=a,B=b,value=str(value),star=star))
# Move that cut one column left and retain an all-Blue interface.
a,b=endpoint_masks(4,'ooooo','bowob')
a,b=white_move(4,a,b,2,2);a,b=blue_move(4,a,b,1,1)
a,b=restrict(4,a,b,'bobob')
value,star=numerical_solver(4)(a,b)
out.append(dict(label='allblue_T_cap',width=4,A=a,B=b,value=str(value),star=star))
(ROOT/'round4_wf_scalar_probe.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
