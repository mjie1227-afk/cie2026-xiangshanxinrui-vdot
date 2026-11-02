"""Supplement UbYWTP with EXU/Dispatcher input identity and WB diagnostics.
Reuse the pinned extractor; read the existing VCD once, never invoke emu.
"""
import argparse,hashlib,importlib.util,json,re,sys
from pathlib import Path
WORK=Path('/root/private_data/mj/xiangshan')
PREVIOUS=WORK/'evidence/vdot-window-events-UbYWTP'
BASE_SHA='50369437ce50c17845e3ff6291582da8c36515f8098421fea856efea139880ce'
EXU_SHA='3456bd48a6618f86584de80a769b01f5142b612712e4b8b19d186ad86182d448'

def constant_ready(text):
    found={}
    for name,base,number in re.findall(r"\bassign\s+(io_fromVfExu_[\d_]+_ready)\s*=\s*1'([bh])([01])\s*;",text):
        found[name]=int(number,2 if base=='b' else 16)
    return found

def source_proof():
    project=WORK/'vdot-mtval-fix-20261024/XiangShan'
    path=project/'src/main/scala/xiangshan/backend/exu/ExeUnit.scala';raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=EXU_SHA:raise RuntimeError('ExeUnit source differs from reviewed identity; stop before inferring input tags')
    text=raw.decode();anchors=['in1ToN.io.in.bits := io.in.bits','sink.bits.ctrl.robIdx      := source.bits.robIdx',
        'sink.bits.ctrl.pdest       := source.bits.pdest','out.bits := io.in.bits']
    if not all(a in text for a in anchors):raise RuntimeError('Reviewed combinational identity route absent')
    proof={'source':str(path),'sha256':EXU_SHA,'route':'EXU input -> combinational Dispatcher selected output -> FU input',
        'anchors':anchors,'ready_constants':{},'generated_files':[]}
    total=0
    for path in sorted((project/'build/rtl').glob('WbDataPath*.sv')):
        if path.stat().st_size>8*1024**2:raise RuntimeError('WbDataPath generated file exceeds metadata cap')
        raw=path.read_bytes();total+=len(raw)
        if total>32*1024**2:raise RuntimeError('WbDataPath metadata total exceeds cap')
        text=raw.decode(errors='replace')
        proof['generated_files'].append({'path':str(path),'sha256':hashlib.sha256(raw).hexdigest()})
        for name,value in constant_ready(text).items():
            old=proof['ready_constants'].get(name)
            if old is not None and old['constant']!=value:raise RuntimeError('Conflicting generated ready constants')
            proof['ready_constants'][name]={'constant':value,'provenance':str(path),'basis':'direct generated assign; not sampled VCD'}
    return proof

def make_trace(base,proof,instances):
    class SupplementTrace(base.Trace):
        def __init__(self,rows,fu):
            super().__init__(rows,fu);self.current_edge=None;self.current_pre={};self.rejections=[];self.recovered=[]
            if self.fu:
                parent=self.fu['parent']
                for field in ('robIdx_flag','robIdx_value','pdest'):
                    logical='fu_io_in_bits_ctrl_'+field
                    if logical in self.selected:continue
                    # Source hash proves the Dispatcher is combinational; validity/ready remain from the actual FU.
                    choices=[parent+'.in1ToN.io_out_4_bits_'+field,parent+'.io_in_bits_'+field]
                    row=next((self.paths[p] for p in choices if p in self.paths),None)
                    if row:
                        self.selected[logical]=row;self.recovered.append({'logical':logical,'path':row['path'],'basis':proof['route'],'source_sha256':proof['sha256']})
                for suffix in ('valid','ready'):
                    self.bind('fu_parent_'+suffix,parent+'.io_in_'+suffix,False)
                self.bind('fu_parent_clock',parent+'.clock',False)
            for b in self.wbs:
                name=b+'_ready'
                if name not in self.selected and name in proof['ready_constants']:
                    self.selected[name]=proof['ready_constants'][name];self.recovered.append({'logical':name,**self.selected[name]})
            self.fu_coverage={stage:[f for f in ('clock','reset',f'io_{stage}_valid',f'io_{stage}_ready',
              f'io_{stage}_bits_ctrl_robIdx_flag',f'io_{stage}_bits_ctrl_robIdx_value',f'io_{stage}_bits_ctrl_pdest') if 'fu_'+f not in self.selected] for stage in ('in','out')}
            instances.append(self)

        def match(self,rob,pdest):
            target=self.active.get(rob)
            if target is not None and (pdest is None or target['pdest']!=pdest):
                get=lambda n:base.val(self.selected.get(n),self.current_pre)
                sources=[]
                for b in self.wbs+self.ctrl_wbs:
                    if get(b+'_valid')==1 and base.tag(get,b+'_bits_robIdx')==rob and get(b+'_bits_pdest')==pdest:
                        sources.append({'port':b,'pdest':pdest,'ready':get(b+'_ready')})
                for i in self.commit_lanes:
                    if get('isCommit')==1 and get(f'c{i}_valid')==1 and base.tag(get,f'c{i}_rob')==rob:
                        sources.append({'commit_lane':i,'pc':get(f'c{i}_pc'),'instruction':get(f'c{i}_instr'),'pdest':get(f'c{i}_pdest')})
                if len(self.rejections)>=512:raise RuntimeError('Identity diagnostic cap exceeded')
                self.rejections.append({'edge_time':self.current_edge,'target_id':target['id'],'rob':rob,
                    'expected_pdest':target['pdest'],'observed_pdest':pdest,'sources':sources})
            return super().match(rob,pdest)

        def step(self,previous,current,t):
            self.current_edge=t;self.current_pre=previous
            before=len(self.events);super().step(previous,current,t)
            get=lambda n:base.val(self.selected.get(n),previous)
            for e in self.events[before:]:
                if e['kind']=='fu_input_handshake':
                    e.update(identity_source='EXU/Dispatcher combinational route',parent_valid=get('fu_parent_valid'),parent_ready=get('fu_parent_ready'))
                    # A parent unknown is preserved; a contradictory known value rejects the run.
                    if get('fu_parent_valid')==0 or get('fu_parent_ready')==0:raise RuntimeError('FU input fire contradicts parent EXU acceptance')
    return SupplementTrace

def main(out):
    out.mkdir(exist_ok=True)
    if (out/'supplement.json').exists():raise RuntimeError('Fresh output directory required')
    p=PREVIOUS/'trace.py'
    if hashlib.sha256(p.read_bytes()).hexdigest()!=BASE_SHA:raise RuntimeError('Previous extractor identity mismatch')
    spec=importlib.util.spec_from_file_location('pinned_event_base',p);base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
    proof=source_proof();base.dump(out/'source-route-proof.json',proof)
    instances=[];base.Trace=make_trace(base,proof,instances)
    rc=base.run(out)
    if not instances:return rc
    trace=instances[0];base.dump(out/'identity-rejections.json',trace.rejections)
    selected={key:row for key,row in trace.selected.items() if key in ('clock','timer','cycleCnt','isCommit','isWalk')
        or key.startswith(('fu_','io_toVfPreg','io_fromVfExu','io_toCtrlBlock','io_redirect','s1_s3_redirect','s2_s4_redirect'))
        or re.match(r'[rc]\d+_',key)}
    base.dump(out/'screenshot-signals.json',selected)
    selected_paths=list(dict.fromkeys(v['path'] for v in selected.values() if 'path' in v))
    (out/'screenshot-signals.txt').write_text('\n'.join(selected_paths)+'\n')
    focus=[]
    for target in trace.targets:
        if target['id'] in (1,17,18,19):
            focus.append({'identity':{k:target[k] for k in ('id','pc','instruction','rob','pdest','rename_edge')},
                'events':[trace.events[i] for i in target['events']],
                'redirects':[e for e in trace.events if e['kind']=='redirect' and target['id'] in e['covered_target_ids']]})
    result={'status':'supplement-extracted-review-required' if rc==0 else 'failed','base_exit':rc,'recovered':trace.recovered,
        'fu_coverage':trace.fu_coverage,'rejections':trace.rejections,'focus':focus,'cancellation_pass':False,
        'note':'Review completed candidate separately from target17; absence of output is not proof of pre-issue cancellation'}
    base.dump(out/'supplement.json',result)
    print('RECOVERED_PORTS='+json.dumps(trace.recovered),flush=True)
    for row in trace.rejections:print('IDENTITY_REJECTION='+json.dumps(row),flush=True)
    for row in focus:print('FOCUS_DETAIL='+json.dumps(row),flush=True)
    if rc==0:print('VDOT_SUPPLEMENT_EXTRACTED_REVIEW_REQUIRED',flush=True)
    return rc

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('output',type=Path);args=parser.parse_args()
    try:rc=main(args.output.resolve())
    except Exception as error:
        print('SUPPLEMENT_ERROR='+str(error),flush=True);rc=2
        (args.output/'supplement-error.txt').write_text(str(error)+'\n')
    sys.exit(rc)
