"""Targeted raw discovery for RX_odd <= 1/2; never an independent proof."""
from pathlib import Path
import json
import subprocess

RAW='/tmp/col-round2-raw/target/release/raw_research'


def masks(width):
    ambient=width+2;a=b=0
    for r in range(5):
        for c in range(width):a|=1<<(r*ambient+c);b|=1<<(r*ambient+c)
    for c,p in [(0,'wobob'),(width-1,'bowob')]:
        for r,s in enumerate(p):
            if s not in 'ob':a&=~(1<<(r*ambient+c))
            if s not in 'ow':b&=~(1<<(r*ambient+c))
    # The dead column 'width' separates a wo path at rows0,1 in the last
    # column, representing -1/2 exactly.
    a|=1<<(ambient+width+1)
    b|=(1<<(width+1))|(1<<(ambient+width+1))
    return ambient,a,b


if __name__=='__main__':
    output=[]
    for width in (3,5):
        ambient,a,b=masks(width)
        for turn in (0,1):
            text=subprocess.check_output([RAW,'5',str(ambient),str(a),str(b),str(turn),'2000000'],text=True)
            result=json.loads(text);result['label']=f'RX_{width}-1/2'
            result['status']='Unknown' if result['states']>=result['budget'] else 'Completed'
            output.append(result);print(json.dumps(result),flush=True)
    Path(__file__).with_suffix('.json').write_text(json.dumps(output,indent=2)+'\n')
