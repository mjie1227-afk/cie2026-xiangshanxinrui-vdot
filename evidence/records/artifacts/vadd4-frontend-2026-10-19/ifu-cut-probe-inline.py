import pathlib,json
p=pathlib.Path('/home/lenovo1227/xiangshan-learning/waves/vadd4-kj2e3y6k/vadd4.vcd')
scope='TOP.SimTop.l_soc.core_with_l2.core.frontend.inner_ifu'
names={'f2_valid','f2_fire','f2_cut_data_10','f2_cut_data_11','f2_cut_ptr_10','f2_cut_ptr_11','f2_ftq_req_startAddr','f2_ftq_req_ftqIdx_flag','f2_ftq_req_ftqIdx_value'}
stack=[];sig={};vals={};time=0
with p.open() as f:
 for line in f:
  t=line.split()
  if not t:continue
  if t[0]=='$scope':stack.append(t[2])
  elif t[0]=='$upscope':stack.pop()
  elif t[0]=='$var' and '.'.join(stack)==scope and t[4] in names:sig[t[4]]=t[3]
  elif t[0]=='$enddefinitions':break
 ids=set(sig.values())
 for line in f:
  if line[0]=='#':
   if time==5083:break
   time=int(line[1:])
   if time>5083:break
  elif line[0]=='b':
   b,i=line[1:].split()
   if i in ids:vals[i]=int(b,2) if set(b)<={'0','1'} else None
  elif line[0] in '01xz':
   i=line[1:].strip()
   if i in ids:vals[i]=int(line[0]) if line[0] in '01' else None
print(json.dumps({'scope':scope,'time_ps':time,'signals_hex':{n:hex(vals[i]) if vals.get(i) is not None else None for n,i in sig.items()},'missing':sorted(names-set(sig))},ensure_ascii=True))
