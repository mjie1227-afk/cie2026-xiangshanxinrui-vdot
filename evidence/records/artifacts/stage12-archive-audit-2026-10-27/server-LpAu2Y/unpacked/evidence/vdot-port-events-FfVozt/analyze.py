"""One-pass identity and qualified per-port arbitration analysis of saved EfQru1.
Writes fresh evidence only. Physical combinational arbiters use observed parent clock/reset.
"""
import argparse,collections,hashlib,importlib.util,json,signal,sys,time
from pathlib import Path
WORK=Path('/root/private_data/mj/xiangshan');CAP=WORK/'evidence/vdot-port-wave-EfQru1'
MIXED=WORK/'evidence/vdot-mixed-resources-9k3waS/analyze.py'
MIXED_SHA='b48c0872194c8b6e1bd9333b6e86a6c6dc7ce0cf1b1d4449938ddc9d32b19c85'
PCS={0x80000170:0x82112057,0x80000174:0x0020818b,0x80000178:0x52082257}
DOT,IOTA=0x80000174,0x80000178
IMG=str(WORK/'vdot-dev-20261024/nexus-am/apps/vdot-port-contend-v1/build/vdot-port-contend-v1-riscv64-xs.bin')
IMG_SHA='10a092fca6208cbb1387976e57c0894d6762f8128c3a7e7ed190dd62beadb039'
BACKEND_SHA='346c2677150a5a64e8e865b9ec3929dcfbdcfb43697c04b468e1bccc2bd812d7'
def require(ok,msg):
    if not ok:raise RuntimeError(msg)
def dump(p,obj):p.write_text(json.dumps(obj,indent=2)+'\n')
def load(name,p,digest):
    require(hashlib.sha256(p.read_bytes()).hexdigest()==digest,'Helper identity mismatch: '+str(p))
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def sample_eligible(get,post,prefix):
    if get(prefix+'_clock')!=0 or post(prefix+'_clock')!=1:return 'clock_unknown_or_not_rising'
    if get(prefix+'_reset')!=0:return 'reset_asserted' if get(prefix+'_reset')==1 else 'reset_unknown'
    return None

class PortAudit:
    def __init__(self,tr,base,mixed):
        self.tr,self.base,self.mixed=tr,base,mixed
        self.coverage={r['id']:collections.Counter() for r in tr.resources}
        self.requests=[];self.root_edges=0;self.conflicts=0
        # Actual RF-write arbitration has no state. Its sampling domain is the containing datapath.
        backend=tr.wb.rsplit('.inner_wbDataPath.',1)[0]
        for field in ('clock','reset'):
            # BackendInlinedImp instantiates WbDataPath and Og2ForVector directly in
            # the same clock/reset scope. Do not use the outer Backend reset: ResetGen
            # may distinguish it from the inlined domain. Only bind an observed path.
            choices=[tr.wb+field,backend+'.inner_'+field,backend+'.inner_og2ForVector.'+field]
            found=next((p for p in choices if p in tr.paths),None)
            tr.bind('wbparent_'+field,found or choices[0],False)
        for r in tr.resources:
            r['sampling_prefix']='wbparent' if r['phase']=='physical_writeback' else 'a'+str(r['id'])
            r['sampling_basis']='observed inlined-backend domain; source-verified combinational leaf; exact paths in sampling-domains.json' if r['phase']=='physical_writeback' else 'observed leaf clock/reset'
        self.domains={'wb_parent_path':tr.wb.rstrip('.'),
            'root_clock':tr.selected.get('clock'),'wb_clock':tr.selected.get('wbparent_clock'),
            'wb_reset':tr.selected.get('wbparent_reset')}
    def observe(self,previous,current,t):
        tr,base=self.tr,self.base
        get=lambda n:base.val(tr.selected.get(n),previous)
        post=lambda n:base.val(tr.selected.get(n),current)
        if get('clock')!=0 or post('clock')!=1:return
        self.root_edges+=1
        for r in tr.resources:
            rid=r['id'];a=f'a{rid}';c=self.coverage[rid];c['root_edges']+=1
            failure=sample_eligible(get,post,r['sampling_prefix'])
            if failure:c[failure]+=1;continue
            c['eligible_edges']+=1;inputs=[]
            for item in r['inputs']:
                slot=item['slot'];b=f'{a}_i{slot}';valid=get(b+'_valid');ready=get(b+'_ready')
                rob=base.tag(get,b+'_bits_robIdx');pdest=get(b+'_bits_pdest');q=item['iq_index']
                source_valid=source_vec=None
                if q is not None:
                    rob=base.tag(get,f'q{q}_bits_common_robIdx');pdest=get(f'q{q}_bits_common_pdest')
                    source_valid=get(f'q{q}_valid');source_vec=get(f'q{q}_bits_common_vecWen')
                identity=tr.participant(rob,pdest)
                if q is not None and (source_valid!=1 or source_vec!=1):
                    identity=None
                    if valid==1 and (source_valid==0 or source_vec==0):self.conflicts+=1
                inputs.append({'slot':slot,'valid':valid,'ready':ready,'rob':rob,'pdest':pdest,
                    'identity':identity,'iq_index':q,'source_valid':source_valid,'source_vec_wen':source_vec})
                if valid not in (0,1):c[f'slot{slot}_valid_unknown']+=1
                if valid==1:
                    c[f'slot{slot}_requests']+=1
                    c[f'slot{slot}_ready_'+(str(ready) if ready in (0,1) else 'unknown')]+=1
            d=self.mixed.decision(inputs,get(a+'_io_out_valid'),get(a+'_io_out_ready'),get(a+'_io_chosen'))
            known=d['all_input_valid_known'];n=d['request_count']
            c['all_valid_known' if known else 'valid_unknown']+=1
            if known:c['zero_requests' if n==0 else 'single_request' if n==1 else 'multiple_requests']+=1
            if d['co_requests']:c['co_requests']+=1
            if d['explicit_arbitration']:c['explicit_arbitration']+=1
            selected=[x['identity']['target_id'] for x in inputs if x['valid']==1 and x['identity'] is not None and x['identity'].get('target_id') is not None]
            if d['co_requests'] or selected:
                require(len(self.requests)<5000,'Request record cap exceeded')
                self.requests.append({'edge_time':t,'resource_id':rid,'phase':r['phase'],'scope':r['scope'],
                    'sampling_basis':r['sampling_basis'],'decision':d,'inputs':inputs,'selected_targets':selected,
                    'out_ready_basis':r['out_ready_basis'],
                    'active_redirects':[{'port':p,'rob':base.tag(get,p+'_bits_robIdx'),'level':get(p+'_bits_level')}
                        for p in tr.redirects if get(p+'_valid')==1]})
    def finish(self):
        out=[]
        for r in self.tr.resources:
            c=self.coverage[r['id']];complete=bool(c['root_edges']) and c['eligible_edges']==c['root_edges'] and not c['valid_unknown']
            out.append({'resource_id':r['id'],'phase':r['phase'],'scope':r['scope'],'sampling_basis':r['sampling_basis'],
                'counts':dict(c),'complete_valid_coverage':complete,
                'no_co_request_in_sampled_resource_window':complete and not c['multiple_requests']})
        return out

def review_pairs(tr,requests):
    pairs=[]
    for r in requests:
        active=[x['identity'] for x in r['inputs'] if x['valid']==1 and x['identity'] is not None]
        members={pc:[p for p in active if p['pc']==pc and p.get('target_id') is not None] for pc in (DOT,IOTA)}
        if not all(members.values()):continue
        ids=sorted({p['target_id'] for v in members.values() for p in v});chains=[]
        for tid in ids:
            target=tr.targets[tid];events=[tr.events[i] for i in target['events']]
            relevant={k:[e['edge_time'] for e in events if e['kind']==k] for k in ('iq_offer','exu_in_fire','exu_out_fire','writeback_to_ctrl','rob_commit')}
            redirects=[e for e in tr.events if e['kind']=='redirect' and tid in e.get('covered_target_ids',[]) and target['rename_edge']<=e['edge_time']<=max(relevant['rob_commit'] or [r['edge_time']])]
            later_chain=all(any(t>=r['edge_time'] for t in relevant[k]) for k in ('exu_in_fire','exu_out_fire','writeback_to_ctrl','rob_commit'))
            chains.append({'target_id':tid,'pc':hex(target['pc']),'word':hex(target['instruction']),
                'rob':target['rob'],'pdest':target['pdest'],'rename_edge':target['rename_edge'],
                'events':relevant,'later_chain_present':later_chain,'redirects_covering_identity':redirects})
        pairs.append({'edge_time':r['edge_time'],'resource_id':r['resource_id'],'phase':r['phase'],
            'explicit_arbitration':r['decision']['explicit_arbitration'],'decision':r['decision'],'chains':chains,
            'mechanical_chain_complete':r['decision']['explicit_arbitration'] and len(chains)==2
                and all(c['later_chain_present'] and not c['redirects_covering_identity'] for c in chains),
            'note':'review pre-edge resource grants and IQ readiness separately; no automatic acceptance'})
    return pairs

def run(out):
    require(out.is_dir() and not(out/'result.json').exists(),'Fresh directory required')
    result={'status':'running','simulator_invoked':False,'contention_accepted':False,
        'cwd':str(Path.cwd()),'argv':sys.argv,'python':sys.version};start=time.monotonic()
    try:
        signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(RuntimeError('240s analysis deadline')));signal.alarm(240)
        mixed=load('mixed',MIXED,MIXED_SHA);base=load('event_base',mixed.BASE,mixed.BASE_SHA);base.PCS=PCS
        mixed.SOURCE_HASHES['src/main/scala/xiangshan/backend/Backend.scala']=BACKEND_SHA
        for path,sha in mixed.SOURCE_HASHES.items():require(hashlib.sha256((WORK/'vdot-mtval-fix-20261024/XiangShan'/path).read_bytes()).hexdigest()==sha,'Resource source identity differs: '+path)
        dump(out/'source-identities.json',mixed.SOURCE_HASHES)
        prior=json.loads((CAP/'result.json').read_text());wave=CAP/'port-window.vcd';before=wave.stat()
        require(prior['status']=='port-captured-inventory-ready' and prior['emu_exit']==0 and prior['runtime']['runtime_ok'],'Capture not accepted')
        require(prior['identity_before']==prior['identity_after'] and prior['identity_before'][IMG]==IMG_SHA,'Capture image identity differs')
        require(before.st_size==prior['vcd']['wave_bytes']==481830060,'Wave size changed')
        dump(out/'capture-identities.json',prior['identity_before']);dump(out/'capture-record-hash.json',{'sha256':hashlib.sha256((CAP/'result.json').read_bytes()).hexdigest()})
        helper=base.load_helper();print('READING_PORT_EVENTS existing_wave=true pre_edge=true simulator=false',flush=True)
        with wave.open('rb') as f:
            rows,scopes,header=helper.read_header(f)
            require(header['sha256']==prior['vcd']['header_sha256'] and header['bytes']==prior['vcd']['header_bytes'],'Wave header differs')
            tr=mixed.make_trace(base,rows,scopes);audit=PortAudit(tr,base,mixed)
            dump(out/'resource-schema.json',tr.schema);dump(out/'sampling-domains.json',audit.domains)
            dump(out/'selected-signals.json',tr.selected)
            ids={r['id'].encode() for r in tr.selected.values() if 'id' in r};pre={}
            for t,post in base.settled(f,ids):audit.observe(pre,post,t);tr.step(pre,post,t);pre=post
        after=wave.stat();require((before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns),'Wave changed during analysis')
        require(tr.targets and audit.root_edges,'No identities or sampled edges')
        coverage=audit.finish();pairs=review_pairs(tr,audit.requests)
        dump(out/'targets.json',tr.targets);dump(out/'events.json',tr.events);dump(out/'request-events.json',audit.requests)
        dump(out/'resource-coverage.json',coverage);dump(out/'pair-review.json',pairs)
        summaries=[]
        for target in tr.targets:
            events=[tr.events[i] for i in target['events']]
            summaries.append({k:target[k] for k in ('id','pc','instruction','rob','pdest','rename_edge')}|
                {'events':[e for e in events if e['kind'] in ('rename_handshake','iq_offer','exu_in_fire','exu_out_fire','writeback_to_ctrl','rob_commit','rob_tag_reused')]})
        dump(out/'target-summary.json',summaries)
        # Context is generated from observations; a viewing recommendation is not a contention verdict.
        edges=[p['edge_time'] for p in pairs] or [e['edge_time'] for e in tr.events if e['kind']=='exu_in_fire' and tr.targets[e['target_id']]['pc'] in (DOT,IOTA)]
        window=None
        if edges:
            center=min(edges);window={'begin_ps':max(prior['vcd']['first_vcd_timestamp'],center-32),
                'end_ps':min(prior['vcd']['last_vcd_timestamp'],center+100),
                'basis':'first mapped pair request' if pairs else 'first target EXU input; no pair request found'}
        dump(out/'gtk-focus.json',{'window':window,'pair_count':len(pairs),'acceptance':False,
            'signal_list':str(CAP/'gtkwave-overview-signals.txt'),'identities':'target-summary.json'})
        result.update(status='port-events-review-required',root_edges=audit.root_edges,
            target_count=len(tr.targets),resource_count=len(coverage),fully_sampled_resources=sum(c['complete_valid_coverage'] for c in coverage),
            qualified_co_request_events=sum(c['counts'].get('co_requests',0) for c in coverage),
            mapped_dot_iota_pairs=len(pairs),mechanical_complete_pairs=sum(p['mechanical_chain_complete'] for p in pairs),
            mapping_conflicts={'qualified_audit':audit.conflicts,'inherited_mapping_check':tr.mapping_conflict_count},identity_rejections=dict(tr.unmatched),
            clock_offsets={k:sorted(v) for k,v in tr.offsets.items()},gtk_window=window,
            limitations=['Physical WB input identities may be absent; raw multi-request is not automatically the target pair',
                'Earlier busy-table/read-port gating is not fully covered; IQ ready alone does not isolate blocking resource',
                'No GUI opened; review actual pre-edge handshake and allocation epochs before accepting competition'])
        print('SAMPLING_DOMAINS='+json.dumps(audit.domains),flush=True)
        for row in coverage:print('RESOURCE_COVERAGE='+json.dumps(row),flush=True)
        for row in summaries[:12]:print('TARGET='+json.dumps(row),flush=True)
        focus=[r for r in audit.requests if r['selected_targets'] or r['decision']['co_requests']]
        for row in focus[:16]:print('REQUEST='+json.dumps(row),flush=True)
        for row in pairs[:8]:print('PAIR_REVIEW='+json.dumps(row),flush=True)
        print('PORT_SUMMARY='+json.dumps(result),flush=True)
        print('VDOT_PORT_EVENTS_READY',flush=True);return 0
    except Exception as error:
        result.update(status='failed',error=str(error));print('PORT_ANALYSIS_ERROR='+str(error),flush=True);return 2
    finally:
        signal.alarm(0);result['elapsed_seconds']=round(time.monotonic()-start,3);dump(out/'result.json',result);print('LOG_DIR='+str(out),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);sys.exit(run(p.parse_args().output.resolve()))
