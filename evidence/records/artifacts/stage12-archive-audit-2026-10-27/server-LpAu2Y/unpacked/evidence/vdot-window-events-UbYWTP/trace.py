"""Read the existing bounded VCD once; retain pre-edge, identity-qualified events.
No simulator, no rebuild, no automatic cancellation PASS.
"""
import argparse,collections,hashlib,importlib.util,json,re,signal,sys,time
from pathlib import Path

WORK=Path('/root/private_data/mj/xiangshan')
META=WORK/'evidence/vdot-wave-raw-schema-Vebwql'
CAP=WORK/'evidence/vdot-wave-window-Cpa0HX'
HELPER_SHA='bbc9634cc9e3e79f685bb93fc47f788f347458b547e7ba090370aa0daf866c75'
PCS={0x80000204:0x01ff0463,0x80000208:0x0220818b}

def dump(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def require(ok,message):
    if not ok:raise RuntimeError(message)
def load_helper():
    p=META/'discover.py'
    require(hashlib.sha256(p.read_bytes()).hexdigest()==HELPER_SHA,'Previous helper identity mismatch')
    spec=importlib.util.spec_from_file_location('header_helper',p)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def port_connections(body,instance):
    start=re.search(r'\bVDot\s+'+re.escape(instance)+r'\s*\(',body)
    if not start:return {},''
    end=body.find(');',start.end());require(end>=0,'Unterminated VDot instance')
    block=body[start.start():end+2];require(len(block)<128*1024,'Instance block too large')
    # Only direct identifier or literal connections are mapped; expressions stay unresolved.
    return dict(re.findall(r'\.(\w+)\s*\(\s*([^()]*)\s*\)',block)),block

def discover_fu(rows,scopes,out):
    prior=json.loads((META/'rtl-references.json').read_text())
    refs=prior['references'];files={f['path']:f for f in prior['files'] if 'sha256' in f}
    paths={r['path']:r for r in rows};allscopes={s['path'] for s in scopes}
    results=[];read_bytes=0;wiring=[]
    def read(p):
        nonlocal read_bytes
        raw=p.read_bytes();read_bytes+=len(raw)
        require(len(raw)<=8*1024**2 and read_bytes<=64*1024**2,'RTL metadata read budget exceeded')
        if str(p) in files:require(hashlib.sha256(raw).hexdigest()==files[str(p)]['sha256'],'Generated RTL changed: '+str(p))
        wiring.append({'path':str(p),'sha256':hashlib.sha256(raw).hexdigest()})
        return raw.decode(errors='replace')
    rtl=WORK/'vdot-mtval-fix-20261024/XiangShan/build/rtl'
    parents={p:read(p) for p in sorted(rtl.glob('*ExuBlock*.sv')) if p.stat().st_size<=8*1024**2}
    for ref in refs:
        body=read(Path(ref['file']));connections,block=port_connections(body,ref['instance'])
        (out/('wiring-'+ref['parent_module']+'.txt')).write_text(block+'\n')
        instances=[]
        for p,source in parents.items():
            for match in re.finditer(r'\b'+re.escape(ref['parent_module'])+r'\s+(\w+)\s*\(',source):
                instances.append({'file':str(p),'instance':match[1],'line':source[:match.start()].count('\n')+1})
        roots=sorted(s for s in allscopes if '.inner_vfExuBlock.' in s and s.rsplit('.',1)[-1] in {v['instance'] for v in instances})
        for parent in roots:
            mapping={};missing={}
            for port,expr in connections.items():
                expr=expr.strip();direct=parent+'.'+ref['instance']+'.'+port
                flat=parent+'.'+expr
                row=paths.get(direct) or (paths.get(flat) if re.fullmatch(r'[A-Za-z_$][\w$]*',expr) else None)
                if row:mapping[port]=row
                elif re.fullmatch(r"\d+'[bh][0-9a-fA-F]+",expr):mapping[port]={'constant':int(expr.split("'")[1][1:],2 if "'b" in expr else 16)}
                else:missing[port]=expr
            results.append({'parent':parent,'instance':ref['instance'],'parent_declarations':instances,'mapping':mapping,'unresolved':missing})
    dump(out/'fu-mapping.json',{'candidates':results,'read_bytes':read_bytes,'file_identities':wiring,
        'scope_name_matches':[s for s in sorted(allscopes) if s.endswith('.funcUnits_4')][:80],
        'flat_name_examples':[r for r in rows if 'funcUnits_4' in r['path']][:80]})
    return results

def settled(stream,ids):
    """Selected values after all changes at each timestamp; caller uses previous sample."""
    values={};stamp=None;line_count=0
    for raw in stream:
        line_count+=1
        if line_count%1000000==0:print('SCAN_LINES='+str(line_count),flush=True)
        line=raw.strip()
        if not line:continue
        if line[:1]==b'#':
            if stamp is not None:yield stamp,values.copy()
            new=int(line[1:]);require(stamp is None or new>stamp,'Non-increasing VCD time')
            stamp=new
        elif line[:1] in (b'b',b'B'):
            bits,ident=line[1:].split(None,1)
            if ident in ids:values[ident]=None if any(c in bits.lower() for c in (b'x',b'z')) else int(bits,2)
        elif line[:1] in (b'0',b'1',b'x',b'X',b'z',b'Z'):
            ident=line[1:]
            if ident in ids:values[ident]=int(line[:1]) if line[:1] in (b'0',b'1') else None
    if stamp is not None:yield stamp,values.copy()

def val(row,values):
    if row is None:return None
    return row.get('constant') if 'constant' in row else values.get(row['id'].encode())
def tag(get,base):
    f,v=get(base+'_flag'),get(base+'_value')
    return (f,v) if f in (0,1) and v is not None else None
def needs_flush(target,redirect,level):
    return bool((target[0]!=redirect[0]) ^ (target[1]>redirect[1])) or (target==redirect and bool(level&1))

class Trace:
    def __init__(self,rows,fu):
        self.paths={r['path']:r for r in rows};self.selected={};self.missing=[]
        self.events=[];self.targets=[];self.active={};self.allocation_count=0;self.edges=0;self.first=None;self.last=None
        self.offsets=collections.defaultdict(set);self.unmatched=collections.Counter()
        def root(suffix):
            found=sorted({r['scope'] for r in rows if r['scope'].endswith(suffix)})
            require(len(found)==1,'Expected unique scope '+suffix);return found[0]+'.'
        self.rename=root('.inner_ctrlBlock.rename');self.rob=root('.inner_ctrlBlock.rob')
        self.ctrl=root('.inner_ctrlBlock');self.wb=root('.inner_wbDataPath')
        self.bind('clock','TOP.clock',True);self.bind('timer','TOP.SimTop.timer',True)
        counter=[r for r in rows if '.rob.difftest_module_' in r['path'] and r['name']=='io_bits_cycleCnt']
        if len(counter)==1:self.selected['cycleCnt']=counter[0]
        self.lanes=sorted({int(m[1]) for r in rows if (m:=re.fullmatch(re.escape(self.rename)+r'io_out_(\d+)_valid',r['path']))})
        require(bool(self.lanes),'No rename lanes')
        for i in self.lanes:
            for field in ('valid','ready','bits_pc','bits_instr','bits_robIdx_flag','bits_robIdx_value','bits_pdest'):
                self.bind(f'r{i}_{field}',self.rename+f'io_out_{i}_{field}',True)
        self.commit_lanes=sorted({int(m[1]) for r in rows if (m:=re.fullmatch(re.escape(self.rob)+r'io_commits_commitValid_(\d+)',r['path']))})
        require(bool(self.commit_lanes),'No ROB commit lanes')
        for field in ('isCommit','isWalk'):self.bind(field,self.rob+'io_commits_'+field,True)
        for i in self.commit_lanes:
            for field,path in {'valid':f'io_commits_commitValid_{i}','walk':f'io_commits_walkValid_{i}',
              'rob_flag':f'io_commits_robIdx_{i}_flag','rob_value':f'io_commits_robIdx_{i}_value',
              'pc':f'io_commits_info_{i}_debug_pc','instr':f'io_commits_info_{i}_debug_instr',
              'pdest':f'io_commits_info_{i}_debug_pdest','walk_flag':f'walkPtrVec_{i}_flag','walk_value':f'walkPtrVec_{i}_value'}.items():
                self.bind(f'c{i}_{field}',self.rob+path,field not in ('walk','walk_flag','walk_value'))
        self.redirects=[]
        for base in ('io_redirect','s1_s3_redirect','s2_s4_redirect'):
            prefix=self.ctrl+base
            if all(prefix+x in self.paths for x in ('_valid','_bits_robIdx_flag','_bits_robIdx_value','_bits_level')):
                self.redirects.append(base)
                for f in ('valid','bits_robIdx_flag','bits_robIdx_value','bits_level'):self.bind(base+'_'+f,prefix+'_'+f,True)
        require(bool(self.redirects),'No complete redirect endpoint')
        self.wbs=[]
        for r in rows:
            match=re.fullmatch(re.escape(self.wb)+r'(io_fromVfExu_\d+_\d+)_valid',r['path'])
            if match:
                b=match[1];self.wbs.append(b)
                for f in ('valid','ready','bits_robIdx_flag','bits_robIdx_value','bits_pdest','bits_data_0','bits_vecWen','bits_v0Wen'):
                    self.bind(b+'_'+f,self.wb+b+'_'+f,False)
        self.preg_ports=[];self.ctrl_wbs=[]
        for r in rows:
            match=re.fullmatch(re.escape(self.wb)+r'(io_to(?:Vf|V0)Preg_[\d_]+)_wen',r['path'])
            if match:
                b=match[1];self.preg_ports.append(b)
                for f in ('wen','addr','data'):self.bind(b+'_'+f,self.wb+b+'_'+f,False)
            match=re.fullmatch(re.escape(self.wb)+r'(io_toCtrlBlock_writeback_\d+)_valid',r['path'])
            if match:
                b=match[1];self.ctrl_wbs.append(b)
                for f in ('valid','bits_robIdx_flag','bits_robIdx_value','bits_pdest'):self.bind(b+'_'+f,self.wb+b+'_'+f,False)
        self.fu=fu[0] if len(fu)==1 else None
        if self.fu:
            for name,row in self.fu['mapping'].items():
                if name in ('clock','reset') or re.fullmatch(r'io_(in|out)_(valid|ready|bits_ctrl_(robIdx_(flag|value)|pdest)|bits_res_data)',name) or name.startswith('io_flush_'):
                    self.selected['fu_'+name]=row
        self.fu_coverage={stage:[f for f in ('clock','reset',f'io_{stage}_valid',f'io_{stage}_ready',f'io_{stage}_bits_ctrl_robIdx_flag',f'io_{stage}_bits_ctrl_robIdx_value',f'io_{stage}_bits_ctrl_pdest') if 'fu_'+f not in self.selected] for stage in ('in','out')}

    def bind(self,name,path,required):
        if path in self.paths:self.selected[name]=self.paths[path]
        else:
            self.missing.append({'logical':name,'path':path,'required':required})
            require(not required,'Required port missing: '+path)
    def emit(self,kind,t,target=None,**details):
        require(len(self.events)<20000,'Event cap reached')
        e={'kind':kind,'edge_time':t,**details}
        if target is not None:e['target_id']=target['id'];target['events'].append(len(self.events))
        self.events.append(e)
    def match(self,rob,pdest):
        target=self.active.get(rob)
        if target is not None and pdest is not None and target['pdest']==pdest:return target
        if target is not None:self.unmatched['pdest_missing_or_mismatch']+=1
        return None
    def step(self,previous,current,t):
        get=lambda n:val(self.selected.get(n),previous)
        post=lambda n:val(self.selected.get(n),current)
        if post('timer') is not None and post('clock') in (0,1):self.offsets['timer_'+str(post('clock'))].add(t-2*post('timer'))
        if post('cycleCnt') is not None and post('clock') in (0,1):self.offsets['cycleCnt_'+str(post('clock'))].add(t-2*post('cycleCnt'))
        if get('clock')!=0 or post('clock')!=1:return
        self.edges+=1;self.first=t if self.first is None else self.first;self.last=t
        # All event fields below are from the settled sample BEFORE this edge.
        for stage,kind in [('in','fu_input_handshake'),('out','fu_output_handshake')]:
            b='fu_io_'+stage
            if not self.fu_coverage[stage] and get('fu_clock')==0 and post('fu_clock')==1 and get('fu_reset')==0 and get(b+'_valid')==1 and get(b+'_ready')==1:
                target=self.match(tag(get,b+'_bits_ctrl_robIdx'),get(b+'_bits_ctrl_pdest'))
                if target is not None:self.emit(kind,t,target,data=get(b+'_bits_res_data'),timer_before=get('timer'))
        wb_fires=[]
        for b in self.wbs:
            if get(b+'_valid')==1:
                target=self.match(tag(get,b+'_bits_robIdx'),get(b+'_bits_pdest'))
                if target is not None:
                    self.emit('wb_input_fire' if get(b+'_ready')==1 else 'wb_input_valid_ready_unknown_or_low',t,target,
                        port=b,ready=get(b+'_ready'),data=get(b+'_bits_data_0'),vecWen=get(b+'_bits_vecWen'),v0Wen=get(b+'_bits_v0Wen'))
                    if get(b+'_ready')==1:wb_fires.append((target,get(b+'_bits_data_0')))
        for b in self.preg_ports:
            if get(b+'_wen')==1:
                candidates=[v for v in self.active.values() if v['pdest']==get(b+'_addr') and v['pc']==0x80000208]
                for target in candidates:
                    joined=any(v['id']==target['id'] and data is not None and data==get(b+'_data') for v,data in wb_fires)
                    self.emit('preg_write_port',t,target,port=b,addr=get(b+'_addr'),data=get(b+'_data'),
                        association='same_edge_wb_input_identity_and_value' if joined else 'pdest_only_candidate')
        for b in self.ctrl_wbs:
            if get(b+'_valid')==1:
                target=self.match(tag(get,b+'_bits_robIdx'),get(b+'_bits_pdest'))
                if target is not None:self.emit('writeback_to_ctrl',t,target,port=b)
        for i in self.commit_lanes:
            if get('isCommit')==1 and get(f'c{i}_valid')==1:
                rob=tag(get,f'c{i}_rob');target=self.match(rob,get(f'c{i}_pdest'))
                pc,inst=get(f'c{i}_pc'),get(f'c{i}_instr')
                if target is not None and pc==target['pc'] and inst==target['instruction']:
                    self.emit('rob_commit',t,target,lane=i);target['committed']=True;self.active.pop(rob,None)
                elif pc in PCS:self.emit('target_commit_without_matching_rename',t,pc=pc,instruction=inst,rob=rob,pdest=get(f'c{i}_pdest'))
            if get('isWalk')==1 and get(f'c{i}_walk')==1:
                target=self.match(tag(get,f'c{i}_walk'),get(f'c{i}_pdest'))
                if target is not None:self.emit('rob_walk_observation',t,target,lane=i,pc=get(f'c{i}_pc'),note='walk is not automatically cancellation')
        for i in self.lanes:
            if get(f'r{i}_valid')==1 and get(f'r{i}_ready')==1:
                rob=tag(get,f'r{i}_bits_robIdx');pc=get(f'r{i}_bits_pc');inst=get(f'r{i}_bits_instr');pdest=get(f'r{i}_bits_pdest')
                require(rob is not None,'Unknown rename ROB on handshake');self.allocation_count+=1
                old=self.active.pop(rob,None)
                if old is not None:self.emit('rob_tag_reused',t,old)
                if pc in PCS and inst==PCS[pc]:
                    require(pdest is not None,'Unknown target pdest');require(len(self.targets)<512,'Target cap reached')
                    target={'id':len(self.targets),'pc':pc,'instruction':inst,'rob':rob,'pdest':pdest,'rename_edge':t,'events':[],'committed':False}
                    self.targets.append(target);self.active[rob]=target;self.emit('rename_handshake',t,target,lane=i,timer_before=get('timer'))
        for base in self.redirects:
            if get(base+'_valid')==1:
                rob=tag(get,base+'_bits_robIdx');level=get(base+'_bits_level')
                require(rob is not None and level is not None,'Unknown redirect identity')
                source=self.active.get(rob)
                covered=[v['id'] for k,v in self.active.items() if needs_flush(k,rob,level)]
                self.emit('redirect',t,port=base,rob=rob,level=level,source_target_id=source['id'] if source else None,
                    covered_target_ids=covered,note='age coverage only; not proof of execution or cancellation')

def run(out):
    require(out.is_dir() and not (out/'result.json').exists(),'Fresh output directory required')
    started=time.monotonic();result={'status':'running','argv':sys.argv,'cwd':str(Path.cwd()),'python':sys.version,
        'simulator_invoked':False,'cancellation_proven':False,'limits':{'seconds':240,'bytes':457224402,'events':20000}}
    try:
        signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(RuntimeError('240s analysis deadline reached')));signal.alarm(240)
        helper=load_helper();prior=json.loads((CAP/'result.json').read_text());wave=CAP/'cancel-window.vcd';before=wave.stat()
        require(prior['status']=='captured-inventory-ready' and before.st_size==457224402,'Capture identity/size changed')
        print('READING_EXISTING_WINDOW no_simulator=true pre_edge=true',flush=True)
        with wave.open('rb') as stream:
            rows,scopes,header=helper.read_header(stream)
            require(header['bytes']==prior['vcd']['header_bytes'] and header['sha256']==prior['vcd']['header_sha256'],'Header identity changed')
            fu=discover_fu(rows,scopes,out);trace=Trace(rows,fu)
            dump(out/'selected-signals.json',{'signals':trace.selected,'missing':trace.missing,'fu_coverage':trace.fu_coverage})
            print('SELECTED_SIGNALS='+str(len(trace.selected)),flush=True)
            print('FU_MAPPING='+json.dumps({'candidates':len(fu),'parents':[v['parent'] for v in fu],'missing_for_handshake':trace.fu_coverage}),flush=True)
            ids={r['id'].encode() for r in trace.selected.values() if 'id' in r};previous={};timestamps=0
            for stamp,values in settled(stream,ids):
                trace.step(previous,values,stamp);previous=values;timestamps+=1
            require(stream.tell()==before.st_size,'Unexpected incomplete read')
        after=wave.stat();require((after.st_size,after.st_mtime_ns)==(before.st_size,before.st_mtime_ns),'Input changed during analysis')
        require(trace.edges>0 and trace.targets,'No target rename events; inspect selected signal schema')
        with (out/'events.jsonl').open('w') as f:
            for event in trace.events:f.write(json.dumps(event)+'\n')
        dump(out/'targets.json',trace.targets)
        summaries=[]
        for target in trace.targets:
            events=[trace.events[i] for i in target['events']]
            covered=[{'time':e['edge_time'],'port':e['port'],'rob':e['rob'],'level':e['level'],'source':e['source_target_id']}
                for e in trace.events if e['kind']=='redirect' and target['id'] in e['covered_target_ids']]
            summaries.append({'id':target['id'],'pc':hex(target['pc']),'rob':target['rob'],'pdest':target['pdest'],
                'rename':target['rename_edge'],'events':{k:[e['edge_time'] for e in events if e['kind']==k] for k in sorted({e['kind'] for e in events})},
                'redirect_age_matches':covered})
        dump(out/'target-summary.json',summaries)
        result.update(status='events-extracted-review-required',header=header,timestamps=timestamps,root_rising_edges=trace.edges,
            edge_range=[trace.first,trace.last],rename_handshakes_all=trace.allocation_count,target_count=len(trace.targets),
            event_counts=dict(collections.Counter(e['kind'] for e in trace.events)),fu_coverage=trace.fu_coverage,
            clock_offsets={k:sorted(v) for k,v in trace.offsets.items()},identity_rejections=dict(trace.unmatched),
            limitations=['Initial high edge has no pre-edge sample; skipped','Absence outside capture window is unknown',
                'preg_write_port associations marked pdest_only_candidate lack full ROB identity at that port',
                'Redirect age match and ROB walk do not alone prove cancellation','Generated RTL mapping is auxiliary and recorded for review'])
        print('EVENT_COUNTS='+json.dumps(result['event_counts']),flush=True)
        print('CLOCK_OFFSETS='+json.dumps(result['clock_offsets']),flush=True)
        print('IDENTITY_REJECTIONS='+json.dumps(result['identity_rejections']),flush=True)
        for summary in summaries[:32]:print('TARGET='+json.dumps(summary),flush=True)
        print('TARGET_TOTAL='+str(len(summaries)),flush=True)
        print('VDOT_EVENTS_EXTRACTED_REVIEW_REQUIRED',flush=True);return 0
    except Exception as error:
        result.update(status='failed',error=str(error));print('TRACE_ERROR='+str(error),flush=True);return 2
    finally:
        signal.alarm(0);result['elapsed_seconds']=round(time.monotonic()-started,3);dump(out/'result.json',result)
        print('LOG_DIR='+str(out),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args();sys.exit(run(a.output.resolve()))
