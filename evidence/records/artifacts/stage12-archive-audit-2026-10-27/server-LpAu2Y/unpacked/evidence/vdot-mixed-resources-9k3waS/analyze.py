"""Trace mixed instruction identities and per-resource co-requests in an existing VCD.
Read-only inputs; no emulator. Missing mapping remains a coverage gap, not no-contention proof.
"""
import argparse,collections,hashlib,importlib.util,json,re,signal,sys,time
from pathlib import Path
WORK=Path('/root/private_data/mj/xiangshan');CAP=WORK/'evidence/vdot-mixed-wave-FNmKGI'
BASE=WORK/'evidence/vdot-window-events-UbYWTP/trace.py';BASE_SHA='50369437ce50c17845e3ff6291582da8c36515f8098421fea856efea139880ce'
TARGETS={0x800001b8:0x02110257,0x800001bc:0x961122d7,0x800001c0:0x0020818b}
SOURCE_HASHES={'src/main/scala/xiangshan/backend/datapath/DataPath.scala':'838eefec28b52827de0f0f0be6dbf33726e9e69518711138054cdf670aacac8f',
 'src/main/scala/xiangshan/backend/datapath/WbArbiter.scala':'da263ea553f27a25cb9fc98c209138dffb700248a6ef5b64104bdc8abb5abbb4',
 'src/main/scala/xiangshan/backend/datapath/RFWBConflictChecker.scala':'7e361eeac818d69b3a910a84fbc499a60776925a0ebe5673c6488c30bef15f8b'}

def require(ok,msg):
    if not ok:raise RuntimeError(msg)
def dump(path,obj):path.write_text(json.dumps(obj,indent=2)+'\n')
def classify(word):
    if word is None:return 'unknown'
    if word&0xfc00707f==0x0b:return 'vdot'
    if word==0x02110257:return 'selected-vadd'
    if word==0x961122d7:return 'selected-vmul'
    return 'other'
def decision(inputs,out_valid,out_ready,chosen):
    requests=[v for v in inputs if v['valid']==1]
    granted=[v['slot'] for v in requests if v['ready']==1]
    blocked=[v['slot'] for v in requests if v['ready']==0]
    return {'request_count':len(requests),'granted_slots':granted,'blocked_slots':blocked,
        'chosen':chosen,'output_valid':out_valid,'output_ready':out_ready,
        'co_requests':len(requests)>=2,'all_input_valid_known':all(v['valid'] in (0,1) for v in inputs),
        'explicit_arbitration':all(v['valid'] in (0,1) for v in inputs) and len(requests)>=2 and len(granted)==1 and len(blocked)==len(requests)-1 and out_valid==1 and out_ready==1
            and (chosen is None or chosen==granted[0])}

def make_trace(base,rows,scopes):
    class MixedTrace(base.Trace):
        def __init__(self):
            super().__init__(rows,[]);self.live={};self.arbitration=[];self.exus=[];self.iqs=[];self.resources=[];self.mapping_notes=[]
            self.mapping_conflict_count=0;self.mapping_conflict_samples=[]
            scope_names={s['path'] for s in scopes};by_scope=collections.defaultdict(list)
            for row in rows:by_scope[row['scope']].append(row)
            def add(key,path):self.bind(key,path,False);return self.selected.get(key)
            for parent in sorted(s for s in scope_names if re.search(r'\.inner_vfExuBlock\.exus(?:_\d+)?$',s)):
                idx=len(self.exus);self.exus.append(parent)
                for f in ('clock','reset','io_in_valid','io_in_ready','io_in_bits_robIdx_flag','io_in_bits_robIdx_value','io_in_bits_pdest',
                    'io_out_valid','io_out_ready','io_out_bits_robIdx_flag','io_out_bits_robIdx_value','io_out_bits_pdest','io_out_bits_data_0'):
                    add(f'x{idx}_{f}',parent+'.'+f)
            dp=sorted(s for s in scope_names if s.endswith('.inner_dataPath'))
            self.dp=dp[0] if len(dp)==1 else None
            iq_groups={kind:{} for kind in ('Int','Fp','Vf','Mem')}
            if self.dp:
                for r in rows:
                    match=re.fullmatch(re.escape(self.dp)+r'\.io_from(Int|Fp|Vf|Mem)IQ_(\d+)_(\d+)_valid',r['path'])
                    if not match:continue
                    kind,i,j=match[1],int(match[2]),int(match[3]);port=f'io_from{kind}IQ_{i}_{j}';idx=len(self.iqs)
                    item={'index':idx,'kind':kind,'group':i,'lane':j,'path':self.dp+'.'+port};self.iqs.append(item)
                    iq_groups[kind].setdefault(i,[]).append(item)
                    for f in ('valid','ready','bits_common_robIdx_flag','bits_common_robIdx_value','bits_common_pdest','bits_common_vecWen'):
                        add(f'q{idx}_{f}',item['path']+'_'+f)
            # Source-defined concatenation order. Do not infer missing groups or lanes.
            ordered={};outer=0;complete=True
            for kind,groups in iq_groups.items():
                if groups and sorted(groups)!=list(range(max(groups)+1)):complete=False
                for group in sorted(groups):
                    lanes=groups[group]
                    if sorted(x['lane'] for x in lanes)!=list(range(max(x['lane'] for x in lanes)+1)):complete=False
                    for item in lanes:ordered[(outer,item['lane'])]=item
                    outer+=1
            pre_roots=sorted(s for s in scope_names if s.endswith('.vfWbBusyArbiter'))
            wb_roots=sorted(s for s in scope_names if s.endswith('.inner_wbDataPath.vfWbArbiter'))
            for phase,roots in [('pre_issue',pre_roots),('physical_writeback',wb_roots)]:
                for parent in roots:
                    outer_ports=[]
                    if phase=='pre_issue':
                        for r in rows:
                            match=re.fullmatch(re.escape(parent)+r'\.io_in_(\d+)_(\d+)_valid',r['path'])
                            if match:
                                key=(int(match[1]),int(match[2]));ready=self.paths.get(parent+f'.io_in_{key[0]}_{key[1]}_ready')
                                if ready:outer_ports.append((key,r,ready))
                        outer_keys={k for k,_,_ in outer_ports}
                        groups_complete=complete and outer_keys==set(ordered)
                    else:groups_complete=False
                    descendants=sorted(s for s in scope_names if s.startswith(parent+'.'))
                    for child in descendants:
                        indices=sorted({int(m[1]) for r in by_scope[child] if (m:=re.fullmatch(r'io_in_(\d+)_valid',r['name']))})
                        if not indices or child+'.io_out_valid' not in self.paths:continue
                        rid=len(self.resources);resource={'id':rid,'phase':phase,'scope':child,'inputs':[],'out_ready_basis':'VCD'}
                        for f in ('clock','reset','io_out_valid','io_out_ready','io_chosen','io_out_bits_robIdx_flag','io_out_bits_robIdx_value','io_out_bits_pdest','io_out_bits_data'):
                            add(f'a{rid}_{f}',child+'.'+f)
                        if f'a{rid}_io_out_ready' not in self.selected:
                            self.selected[f'a{rid}_io_out_ready']={'constant':1,'basis':'locked source: per-port arbOut.ready := true.B'}
                            resource['out_ready_basis']='source constant, not sampled VCD'
                        for slot in indices:
                            fields={}
                            for f in ('valid','ready','bits_robIdx_flag','bits_robIdx_value','bits_pdest','bits_data'):
                                row=add(f'a{rid}_i{slot}_{f}',child+f'.io_in_{slot}_'+f)
                                if row:fields[f]=row
                            mapped=None
                            if phase=='pre_issue' and groups_complete and 'valid' in fields and 'ready' in fields:
                                aliases=[k for k,v,r in outer_ports if v['id']==fields['valid']['id'] and r['id']==fields['ready']['id']]
                                if len(aliases)==1:mapped=ordered[aliases[0]]['index']
                            resource['inputs'].append({'slot':slot,'iq_index':mapped,'identity_fields':all(k in fields for k in ('bits_robIdx_flag','bits_robIdx_value','bits_pdest'))})
                        self.resources.append(resource)
                    self.mapping_notes.append({'phase':phase,'parent':parent,'iq_concat_mapping_complete':groups_complete})
            self.schema={'exus':self.exus,'iq_ports':self.iqs,'resources':self.resources,'mapping_notes':self.mapping_notes,
                'busy_table_scopes':[s for s in sorted(scope_names) if 'vfWbBusyTable' in s][:64],
                'coverage_limit':'Only discovered per-port arbiter scopes; missing scope/mapping is not proof of no contention'}
        def participant(self,rob,pdest):
            instruction=self.live.get(rob)
            if instruction is None or pdest is None or instruction['pdest']!=pdest:return None
            target=self.active.get(rob)
            return dict(instruction,target_id=target['id'] if target and target['pdest']==pdest else None)
        def step(self,previous,current,t):
            get=lambda n:base.val(self.selected.get(n),previous)
            post=lambda n:base.val(self.selected.get(n),current)
            if get('clock')==0 and post('clock')==1:
                # These observations precede retirement and ROB tag reuse at this edge.
                for idx,parent in enumerate(self.exus):
                    if get(f'x{idx}_clock')!=0 or post(f'x{idx}_clock')!=1 or get(f'x{idx}_reset')!=0:continue
                    for direction in ('in','out'):
                        b=f'x{idx}_io_{direction}'
                        if get(b+'_valid')!=1:continue
                        target=self.match(base.tag(get,b+'_bits_robIdx'),get(b+'_bits_pdest'))
                        if target is not None:self.emit('exu_'+direction+('_fire' if get(b+'_ready')==1 else '_valid_not_accepted_or_unknown'),t,target,
                            scope=parent,ready=get(b+'_ready'),data=get(b+'_bits_data_0'))
                for q in self.iqs:
                    b=f'q{q["index"]}'
                    if get(b+'_valid')==1:
                        target=self.match(base.tag(get,b+'_bits_common_robIdx'),get(b+'_bits_common_pdest'))
                        if target is not None:self.emit('iq_offer',t,target,port=q['path'],ready=get(b+'_ready'))
                for resource in self.resources:
                    rid=resource['id'];a=f'a{rid}';inputs=[]
                    if get(a+'_reset') not in (None,0):continue
                    for item in resource['inputs']:
                        b=f'{a}_i{item["slot"]}';rob=base.tag(get,b+'_bits_robIdx');pdest=get(b+'_bits_pdest')
                        iq=item['iq_index'];source_valid=None;source_vec_wen=None
                        if iq is not None:
                            rob=base.tag(get,f'q{iq}_bits_common_robIdx');pdest=get(f'q{iq}_bits_common_pdest')
                            source_valid=get(f'q{iq}_valid');source_vec_wen=get(f'q{iq}_bits_common_vecWen')
                        p=self.participant(rob,pdest)
                        if iq is not None and (source_valid!=1 or source_vec_wen==0):
                            p=None
                            if get(b+'_valid')==1:
                                self.mapping_conflict_count+=1
                                if len(self.mapping_conflict_samples)<20:self.mapping_conflict_samples.append({'edge_time':t,'resource_id':rid,'slot':item['slot'],'iq_index':iq,'source_valid':source_valid,'source_vec_wen':source_vec_wen})
                        inputs.append({'slot':item['slot'],'valid':get(b+'_valid'),'ready':get(b+'_ready'),
                            'rob':rob,'pdest':pdest,'identity':p,'data':get(b+'_bits_data'),
                            'source_iq_valid':source_valid,'source_vec_wen':source_vec_wen})
                    d=decision(inputs,get(a+'_io_out_valid'),get(a+'_io_out_ready'),get(a+'_io_chosen'))
                    if d['co_requests']:
                        require(len(self.arbitration)<5000,'Resource event cap exceeded')
                        known=[v['identity'] for v in inputs if v['valid']==1 and v['identity'] is not None]
                        self.arbitration.append({'edge_time':t,'resource_id':rid,'scope':resource['scope'],'phase':resource['phase'],
                            'decision':d,'inputs':[v for v in inputs if v['valid']==1],'output_ready_basis':resource['out_ready_basis'],
                            'output_identity':{'rob':base.tag(get,a+'_io_out_bits_robIdx'),'pdest':get(a+'_io_out_bits_pdest'),'data':get(a+'_io_out_bits_data')},
                            'selected_targets':[v['target_id'] for v in known if v['target_id'] is not None],
                            'contains_vdot':any(classify(v['instruction'])=='vdot' for v in known),
                            'active_redirects':[{'port':b,'rob':base.tag(get,b+'_bits_robIdx'),'level':get(b+'_bits_level')}
                                for b in self.redirects if get(b+'_valid')==1]})
            super().step(previous,current,t)
            if get('clock')==0 and post('clock')==1:
                if get('isCommit')==1:
                    for i in self.commit_lanes:
                        if get(f'c{i}_valid')==1:self.live.pop(base.tag(get,f'c{i}_rob'),None)
                for i in self.lanes:
                    if get(f'r{i}_valid')==get(f'r{i}_ready')==1:
                        rob=base.tag(get,f'r{i}_bits_robIdx')
                        if rob is not None:self.live[rob]={'rob':rob,'pdest':get(f'r{i}_bits_pdest'),'pc':get(f'r{i}_bits_pc'),
                            'instruction':get(f'r{i}_bits_instr'),'rename_edge':t}
    return MixedTrace()

def run(out):
    require(out.is_dir() and not(out/'result.json').exists(),'Fresh output directory required')
    result={'status':'running','scope':'mixed identity and per-resource request analysis','simulator_invoked':False,'contention_accepted':False,
        'cwd':str(Path.cwd()),'argv':sys.argv,'python':sys.version};start=time.monotonic()
    try:
        signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(RuntimeError('240s analysis deadline')));signal.alarm(240)
        require(hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_SHA,'Pinned event helper changed')
        spec=importlib.util.spec_from_file_location('event_base',BASE);base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base);base.PCS=TARGETS
        project=WORK/'vdot-mtval-fix-20261024/XiangShan'
        for p,sha in SOURCE_HASHES.items():require(hashlib.sha256((project/p).read_bytes()).hexdigest()==sha,'Resource source identity differs: '+p)
        dump(out/'source-identities.json',SOURCE_HASHES)
        prior=json.loads((CAP/'result.json').read_text());require(prior['status']=='mixed-captured-inventory-ready' and prior['emu_exit']==0,'Capture not accepted')
        wave=CAP/'mixed-window.vcd';before=wave.stat();require(before.st_size==prior['vcd']['wave_bytes']==477548918,'Wave size differs')
        helper=base.load_helper();print('READING_MIXED_RESOURCES existing_wave=true pre_edge=true',flush=True)
        with wave.open('rb') as f:
            rows,scopes,header=helper.read_header(f)
            require(header['sha256']==prior['vcd']['header_sha256'] and header['bytes']==prior['vcd']['header_bytes'],'Wave header differs')
            trace=make_trace(base,rows,scopes);dump(out/'resource-schema.json',trace.schema);dump(out/'selected-signals.json',trace.selected)
            print('RESOURCE_SCHEMA='+json.dumps({'exus':trace.exus,'iq_ports':len(trace.iqs),'resources':trace.resources,'mapping_notes':trace.mapping_notes}),flush=True)
            ids={r['id'].encode() for r in trace.selected.values() if 'id' in r};pre={}
            for t,post in base.settled(f,ids):trace.step(pre,post,t);pre=post
        after=wave.stat();require((before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns),'Input changed while reading')
        require(trace.targets and trace.edges,'No target identity observations')
        dump(out/'targets.json',trace.targets);dump(out/'events.json',trace.events);dump(out/'resource-events.json',trace.arbitration)
        dump(out/'mapping-conflicts.json',{'count':trace.mapping_conflict_count,'samples':trace.mapping_conflict_samples})
        focus=[e for e in trace.arbitration if e['selected_targets'] or e['contains_vdot']]
        summaries=[]
        for target in trace.targets:
            events=[trace.events[i] for i in target['events']]
            summaries.append({'id':target['id'],'pc':hex(target['pc']),'word':hex(target['instruction']),'rob':target['rob'],'pdest':target['pdest'],
                'events':{k:[e['edge_time'] for e in events if e['kind']==k] for k in sorted({e['kind'] for e in events})}})
        dump(out/'target-summary.json',summaries)
        result.update(status='mixed-resource-observations-review-required',header=header,root_rising_edges=trace.edges)
        result.update(target_count=len(trace.targets),event_counts=dict(collections.Counter(e['kind'] for e in trace.events)),
            resource_count=len(trace.resources),co_request_events=len(trace.arbitration),vdot_or_selected_events=len(focus),
            explicit_arbitration_events=sum(e['decision']['explicit_arbitration'] for e in focus),
            clock_offsets={k:sorted(v) for k,v in trace.offsets.items()},identity_rejections=dict(trace.unmatched),mapping_conflicts=trace.mapping_conflict_count,
            limitations=['Missing resource fields or identity maps remain gaps','IQ ready alone does not identify blocking resource',
                'All-live identities after redirect are retained until reuse; review redirect overlap before accepting a contention claim',
                'No co-request in discovered arbiters does not prove absence of earlier busy-table conflicts'])
        print('MIXED_SUMMARY='+json.dumps({k:v for k,v in result.items() if k not in ('header','argv','python')}),flush=True)
        for row in summaries[:16]:print('TARGET='+json.dumps(row),flush=True)
        for row in focus[:12]:print('RESOURCE_EVENT='+json.dumps(row),flush=True)
        print('VDOT_MIXED_RESOURCE_OBSERVATIONS_READY',flush=True);return 0
    except Exception as error:
        result.update(status='failed',error=str(error));print('MIXED_ANALYSIS_ERROR='+str(error),flush=True);return 2
    finally:
        signal.alarm(0);result['elapsed_seconds']=round(time.monotonic()-start,3);dump(out/'result.json',result);print('LOG_DIR='+str(out),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args();sys.exit(run(a.output.resolve()))
