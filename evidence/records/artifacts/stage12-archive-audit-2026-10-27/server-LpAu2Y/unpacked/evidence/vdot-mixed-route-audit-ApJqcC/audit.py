"""Read existing mixed VCD once to audit resource routes and sampling coverage.
No simulator or source mutation. Single requests are retained, not called contention.
"""
import argparse,collections,hashlib,importlib.util,json,sys,time
from pathlib import Path
PRIOR=Path('/root/private_data/mj/xiangshan/evidence/vdot-mixed-resources-9k3waS')
SHA='b48c0872194c8b6e1bd9333b6e86a6c6dc7ce0cf1b1d4449938ddc9d32b19c85'

def require(ok,message):
    if not ok:raise RuntimeError(message)
def dump(path,obj):path.write_text(json.dumps(obj,indent=2)+'\n')

class Audit:
    def __init__(self,trace,base):
        self.trace,self.base=trace,base
        self.coverage={r['id']:collections.Counter() for r in trace.resources}
        self.routes=[];self.root_edges=0
    def observe(self,previous,current,t):
        tr,base=self.trace,self.base
        get=lambda n:base.val(tr.selected.get(n),previous)
        post=lambda n:base.val(tr.selected.get(n),current)
        if get('clock')!=0 or post('clock')!=1:return
        self.root_edges+=1
        for r in tr.resources:
            rid=r['id'];a=f'a{rid}';c=self.coverage[rid];c['root_edges']+=1
            if get(a+'_clock')!=0 or post(a+'_clock')!=1:
                c['resource_clock_unknown_or_not_rising']+=1;continue
            reset=get(a+'_reset')
            if reset!=0:
                c['reset_asserted' if reset==1 else 'reset_unknown']+=1;continue
            c['eligible_edges']+=1
            vals=[get(f'{a}_i{x["slot"]}_valid') for x in r['inputs']]
            count=sum(v==1 for v in vals)
            known=all(v in (0,1) for v in vals)
            c['all_valid_known' if known else 'valid_unknown']+=1
            if known:c['zero_requests' if count==0 else 'single_request' if count==1 else 'multiple_requests']+=1
            if count>=2:c['at_least_two_known_requests']+=1
            for item,v in zip(r['inputs'],vals):
                slot=item['slot'];b=f'{a}_i{slot}'
                if v not in (0,1):c[f'slot{slot}_valid_unknown']+=1
                if v!=1:continue
                c[f'slot{slot}_requests']+=1
                ready=get(b+'_ready');c[f'slot{slot}_ready_'+('unknown' if ready not in (0,1) else str(ready))]+=1
                iq=item['iq_index']
                if iq is None:continue
                q=f'q{iq}';rob=base.tag(get,q+'_bits_common_robIdx');pdest=get(q+'_bits_common_pdest')
                identity=tr.participant(rob,pdest)
                if identity is None or identity.get('target_id') is None:continue
                valid,vec=get(q+'_valid'),get(q+'_bits_common_vecWen')
                # Missing source controls are retained explicitly, never promoted to confirmed.
                require(len(self.routes)<1024,'Target route sample cap exceeded')
                self.routes.append({'edge_time':t,'resource_id':rid,'slot':slot,'iq_index':iq,
                    'identity':identity,'source_valid':valid,'source_vec_wen':vec,
                    'identity_controls_confirmed':valid==1 and vec==1,
                    'ready':ready,'all_input_valid_known':known,'known_request_count':count,
                    'output_valid':get(a+'_io_out_valid'),'output_ready':get(a+'_io_out_ready'),
                    'output_ready_basis':r['out_ready_basis'],'chosen':get(a+'_io_chosen')})
    def finish(self):
        result=[]
        for r in self.trace.resources:
            c=self.coverage[r['id']]
            complete=(c['root_edges']>0 and c['eligible_edges']==c['root_edges'] and c['valid_unknown']==0)
            result.append({'resource_id':r['id'],'phase':r['phase'],'scope':r['scope'],
                'input_slots':[x['slot'] for x in r['inputs']],'counts':dict(c),
                'complete_nonreset_valid_coverage':complete,
                'no_co_request_in_sampled_resource_window':complete and c['multiple_requests']==0})
        return result

def target_routes(trace):
    result=[]
    for target in trace.targets:
        events=[trace.events[i] for i in target['events']]
        offers=[]
        for e in events:
            if e['kind']!='iq_offer':continue
            matches=[q for q in trace.iqs if q['path']==e['port']]
            qi=matches[0]['index'] if len(matches)==1 else None
            resources=[{'resource_id':r['id'],'slot':i['slot'],'scope':r['scope']}
                for r in trace.resources if r['phase']=='pre_issue' for i in r['inputs']
                if qi is not None and i['iq_index']==qi]
            offers.append({'edge_time':e['edge_time'],'port':e['port'],'ready':e.get('ready'),
                'iq_index':qi,'mapped_resources':resources})
        result.append({k:target[k] for k in ('id','pc','instruction','rob','pdest','rename_edge')} |
            {'iq_offers':offers,'exu_events':[e for e in events if e['kind'].startswith('exu_')],
             'commit_times':[e['edge_time'] for e in events if e['kind']=='rob_commit']})
    return result

def run(out):
    require(out.is_dir() and not(out/'audit-result.json').exists(),'Fresh output directory required')
    start=time.monotonic();summary={'status':'running','simulator_invoked':False,'contention_accepted':False,
        'cwd':str(Path.cwd()),'argv':sys.argv,'python':sys.version,'prior':str(PRIOR)}
    try:
        source=PRIOR/'analyze.py'
        require(hashlib.sha256(source.read_bytes()).hexdigest()==SHA,'Prior analyzer identity changed')
        old=json.loads((PRIOR/'result.json').read_text())
        require(old['status']=='mixed-resource-observations-review-required' and old['co_request_events']==0
            and old['mapping_conflicts']==0 and old['root_rising_edges']==2280,'Prior result differs; stop for review')
        expected=json.loads((PRIOR/'target-summary.json').read_text())
        dump(out/'prior-input-identities.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (source,PRIOR/'result.json',PRIOR/'target-summary.json')})
        spec=importlib.util.spec_from_file_location('pinned_mixed',source)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        original=module.make_trace;audits=[]
        def factory(base,rows,scopes):
            trace=original(base,rows,scopes);audit=Audit(trace,base);audits.append(audit)
            original_step=trace.step
            def step(previous,current,t):
                audit.observe(previous,current,t);original_step(previous,current,t)
            trace.step=step;return trace
        module.make_trace=factory
        print('AUDITING_ROUTES existing_wave=true simulator=false wall_limit=240s',flush=True)
        require(module.run(out)==0,'Inherited VCD analysis failed; see result.json')
        require(len(audits)==1,'Unexpected trace count')
        audit=audits[0];trace=audit.trace
        require(json.loads((out/'target-summary.json').read_text())==expected,'Target lifecycles differ from accepted input')
        require(trace.mapping_conflict_count==0 and audit.root_edges==old['root_rising_edges'],'Mapping or edge count differs')
        require(len(trace.resources)==old['resource_count'] and len(trace.arbitration)==old['co_request_events'],'Resource analysis differs')
        coverage=audit.finish();routes=target_routes(trace)
        dump(out/'resource-coverage.json',coverage);dump(out/'target-routes.json',routes)
        dump(out/'target-request-samples.json',audit.routes)
        summary.update(status='mixed-route-coverage-review-required',root_edges=audit.root_edges,
            resources=len(coverage),fully_observed_resources=sum(r['complete_nonreset_valid_coverage'] for r in coverage),
            target_request_samples=len(audit.routes),confirmed_target_request_samples=sum(x['identity_controls_confirmed'] for x in audit.routes),
            physical_writeback_identity_attribution='not added; use raw per-resource request coverage only',
            limitations=['Earlier busy-table gating is outside these arbiter inputs',
                'EXU overlap is not same-resource contention; source-constant output ready is labelled',
                'Prior live identity retains redirected tags until reuse; review redirects before accepting competition'])
        for row in routes:print('TARGET_ROUTE='+json.dumps(row),flush=True)
        for row in coverage:print('RESOURCE_COVERAGE='+json.dumps(row),flush=True)
        for row in audit.routes[:24]:print('TARGET_REQUEST='+json.dumps(row),flush=True)
        print('ROUTE_AUDIT='+json.dumps(summary),flush=True)
        print('VDOT_MIXED_ROUTE_AUDIT_READY',flush=True);return 0
    except Exception as e:
        summary.update(status='failed',error=str(e));print('ROUTE_AUDIT_ERROR='+str(e),flush=True);return 2
    finally:
        summary['elapsed_seconds']=round(time.monotonic()-start,3)
        dump(out/'audit-result.json',summary);print('LOG_DIR='+str(out),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('output',type=Path)
    sys.exit(run(parser.parse_args().output.resolve()))
