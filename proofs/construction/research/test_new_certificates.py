#!/usr/bin/env python3
import copy,gzip,json
from number_certificates import ROOT,verify
p=ROOT/'new_certificates'/'cap_minus_quarter_blue.json.gz'
d=json.loads(gzip.decompress(p.read_bytes()))
mutations=[
 ('illegal reply',lambda x:x['nodes'][0][4][0].__setitem__(1,-99)),
 ('missing first-player branch',lambda x:x['nodes'][0][4].pop()),
 ('non-dyadic number',lambda x:x['root'].__setitem__(3,3)),
 ('missing successor checkpoint',lambda x:x['nodes'].pop()),
]
for name,mutate in mutations:
 x=copy.deepcopy(d);mutate(x)
 try:verify(x)
 except (ValueError,KeyError,AssertionError):print('PASS: rejected',name)
 else:raise AssertionError('Accepted corrupt certificate: '+name)
