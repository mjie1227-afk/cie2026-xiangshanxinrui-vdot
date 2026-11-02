"""Check retirement-qualified VS-dirty requests in the existing VCD window.
This does not claim final mstatus/vsstatus state or all CSR effects verified.
"""
import argparse,hashlib,importlib.util,json,re,signal,sys,time
from pathlib import Path
WORK=Path('/root/private_data/mj/xiangshan')
CAP=WORK/'evidence/vdot-wave-window-Cpa0HX'
PREV=WORK/'evidence/vdot-window-supplement-fgpWCe'
BASE=WORK/'evidence/vdot-window-events-UbYWTP/trace.py'
BASE_SHA='50369437ce50c17845e3ff6291582da8c36515f8098421fea856efea139880ce'
SOURCES={
 'src/main/scala/xiangshan/backend/rob/Rob.scala':'9caf717a9be85ddaa9e73b3f2eb88a0e2933896302ba97acb31eb66cc5edf6d5',
 'src/main/scala/xiangshan/backend/fu/wrapper/CSR.scala':'2f6a27f9f4aef987369b010c92799f5aecac3bf0a659b06186969f630ef83711',
 'src/main/scala/xiangshan/backend/Backend.scala':'346c2677150a5a64e8e865b9ec3929dcfbdcfb43697c04b468e1bccc2bd812d7',
 'utility/src/main/scala/utility/ClockGatedReg.scala':'c79223ebb92249e67ca3c6b04571b0194167a374263c151aaa1699af311d47a5'}

def require(ok,msg):
    if not ok:raise RuntimeError(msg)
def dump(path,obj):path.write_text(json.dumps(obj,indent=2)+'\n')
def expected_dirty(is_commit,lanes):
    require(is_commit in (0,1),'Unknown isCommit')
    if not is_commit:return 0
    values=[]
    for lane in lanes:
        require(lane['valid'] in (0,1),'Unknown commitValid')
        if lane['valid']:
            require(lane['dirtyVs'] in (0,1),'Unknown committed dirtyVs');values.append(lane['dirtyVs'])
    return int(any(values))
def tag_matches(lane,target,t):
    reused=target.get('reuse_edge')
    return target['rename_edge']<=t and (reused is None or t<reused) and all(lane[k]==target[k] for k in ('rob','pdest','pc','instruction'))

class CSRCheck:
    def __init__(self,rows,targets,base):
        self.base=base;self.targets=targets;self.paths={r['path']:r for r in rows};self.selected={};self.edges=0
        self.rows=[];self.mismatches=[];self.target_commits=[];self.reset_edges=0
        roots=sorted({r['scope'] for r in rows if r['scope'].endswith('.inner_ctrlBlock.rob')})
        require(len(roots)==1,'Unique ROB scope required');self.rob=roots[0]+'.'
        def bind(key,path):
            require(path in self.paths,'Missing required signal: '+path);self.selected[key]=self.paths[path]
        self.bind=bind
        bind('root_clock','TOP.clock');bind('rob_clock',self.rob+'clock');bind('reset',self.rob+'reset')
        bind('isCommit',self.rob+'io_commits_isCommit');bind('rob_vsDirty',self.rob+'io_csr_dirty_vs')
        csr=[r for r in rows if r['name']=='io_fromRob_commit_vsDirty' and '.csrMod.' in r['path']]
        require(len(csr)==1,'Unique CSR receive vsDirty port required');self.selected['csr_vsDirty']=csr[0]
        self.lanes=sorted({int(m[1]) for r in rows if (m:=re.fullmatch(re.escape(self.rob)+r'io_commits_commitValid_(\d+)',r['path']))})
        require(bool(self.lanes),'No ROB commit lanes')
        for i in self.lanes:
            for field,suffix in {'valid':f'io_commits_commitValid_{i}','dirtyVs':f'io_commits_info_{i}_dirtyVs',
                'flag':f'io_commits_robIdx_{i}_flag','value':f'io_commits_robIdx_{i}_value',
                'pc':f'io_commits_info_{i}_debug_pc','instruction':f'io_commits_info_{i}_debug_instr',
                'pdest':f'io_commits_info_{i}_debug_pdest'}.items():bind(f'c{i}_{field}',self.rob+suffix)
        self.expected_normal={v['id'] for v in targets if v.get('previous_commit') and v['pc']==0x80000208}
    def step(self,pre,post,t):
        get=lambda key,values:self.base.val(self.selected[key],values)
        if get('rob_clock',pre)!=0 or get('rob_clock',post)!=1:return
        require(get('reset',pre) in (0,1),'Unknown ROB reset')
        if get('reset',pre):self.reset_edges+=1;return
        self.edges+=1;lanes=[]
        for i in self.lanes:
            lane={f:get(f'c{i}_{f}',pre) for f in ('valid','dirtyVs','pc','instruction','pdest')}
            lane.update(lane=i,rob=[get(f'c{i}_flag',pre),get(f'c{i}_value',pre)])
            lanes.append(lane)
        commit=get('isCommit',pre);expected=expected_dirty(commit,lanes)
        rob_post=get('rob_vsDirty',post);csr_post=get('csr_vsDirty',post)
        require(rob_post in (0,1) and csr_post in (0,1),'Unknown dirty request output')
        # GatedValidRegNext(Bool) is RegNext: edge samples retirement inputs, then output updates.
        active=[v for v in lanes if commit==1 and v['valid']==1]
        row={'edge_time':t,'isCommit_before':commit,'active_lanes':active,'expected_vsDirty_after':expected,
            'rob_vsDirty_before':get('rob_vsDirty',pre),'rob_vsDirty_after':rob_post,
            'csr_vsDirty_before':get('csr_vsDirty',pre),'csr_vsDirty_after':csr_post}
        if rob_post!=expected or csr_post!=rob_post:self.mismatches.append(row)
        require(len(self.mismatches)<=20,'Too many timing mismatches; stop and inspect mapping')
        hits=[]
        for lane in active:
            for target in self.targets:
                if tag_matches(lane,target,t):
                    hits.append(target['id']);self.target_commits.append({'target_id':target['id'],'edge_time':t,'dirtyVs':lane['dirtyVs'],
                        'rob_request_after':rob_post,'csr_request_after':csr_post,'rob':lane['rob'],'pdest':lane['pdest']})
        row['target_ids']=hits
        if expected or rob_post or csr_post or hits or 16888<=t<=16974:self.rows.append(row)
        require(len(self.rows)<=5000,'CSR observation cap exceeded')
    def result(self):
        normal=[v for v in self.target_commits if v['target_id'] in self.expected_normal]
        seen={v['target_id'] for v in normal};canceled=[v for v in self.target_commits if v['target_id']==19]
        ok=self.edges>0 and not self.mismatches and seen==self.expected_normal and len(normal)==len(seen) and bool(normal)
        ok=ok and all(v['dirtyVs']==v['rob_request_after']==v['csr_request_after']==1 for v in normal) and not canceled
        return {'checks_passed':ok,'checked_edges':self.edges,'reset_edges_skipped':self.reset_edges,
            'mismatch_count':len(self.mismatches),'normal_expected_ids':sorted(self.expected_normal),
            'normal_observed_ids':sorted(seen),'candidate19_commits':len(canceled),'target_commits':self.target_commits,
            'scope':'retirement -> ROB registered dirty_vs -> CSR request input only',
            'final_vs_state_verified':False,'all_csr_side_effects_verified':False}

def run(out):
    require(out.is_dir() and not (out/'result.json').exists(),'Fresh output directory required')
    result={'status':'running','argv':sys.argv,'python':sys.version,'cwd':str(Path.cwd()),'simulator_invoked':False}
    started=time.monotonic()
    try:
        signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(RuntimeError('240s analysis deadline')));signal.alarm(240)
        require(hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_SHA,'Pinned VCD parser changed')
        spec=importlib.util.spec_from_file_location('event_base',BASE);base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
        project=WORK/'vdot-mtval-fix-20261024/XiangShan';identities={}
        for name,expected in SOURCES.items():
            actual=hashlib.sha256((project/name).read_bytes()).hexdigest();require(actual==expected,'Source identity changed: '+name);identities[name]=actual
        dump(out/'source-identities.json',identities)
        prior=json.loads((PREV/'supplement.json').read_text());require(prior['status']=='supplement-extracted-review-required' and prior['base_exit']==0,'Supplement input not accepted')
        targets=json.loads((PREV/'targets.json').read_text());events=[json.loads(line) for line in (PREV/'events.jsonl').read_text().splitlines() if line]
        for v in targets:
            own=[events[i] for i in v['events']];v['reuse_edge']=next((e['edge_time'] for e in own if e['kind']=='rob_tag_reused'),None)
            v['previous_commit']=any(e['kind']=='rob_commit' for e in own)
        target=next(v for v in targets if v['id']==19)
        require(target['rob']==[1,27] and target['pdest']==61 and target['rename_edge']==16892 and target['reuse_edge']==16970,'Candidate identity differs')
        wave=CAP/'cancel-window.vcd';before=wave.stat();require(before.st_size==457224402,'VCD size changed')
        capture=json.loads((CAP/'result.json').read_text());helper=base.load_helper()
        print('CHECKING_CSR_COMMIT_REQUEST existing_wave=true no_simulator=true',flush=True)
        with wave.open('rb') as f:
            rows,scopes,header=helper.read_header(f)
            require(header['sha256']==capture['vcd']['header_sha256'] and header['bytes']==capture['vcd']['header_bytes'],'VCD header changed')
            check=CSRCheck(rows,targets,base);dump(out/'selected-signals.json',check.selected)
            print('CSR_PORTS='+json.dumps({k:v['path'] for k,v in check.selected.items() if k in ('rob_vsDirty','csr_vsDirty','rob_clock')}),flush=True)
            ids={v['id'].encode() for v in check.selected.values()};pre={}
            for t,post in base.settled(f,ids):check.step(pre,post,t);pre=post
        after=wave.stat();require((before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns),'Input changed during read')
        data=check.result();result.update(data,status='csr-request-check-pass' if data['checks_passed'] else 'csr-request-check-failed',header=header)
        dump(out/'csr-observations.json',check.rows);dump(out/'mismatches.json',check.mismatches)
        (out/'screenshot-csr-signals.txt').write_text('\n'.join(dict.fromkeys(v['path'] for v in check.selected.values()))+'\n')
        print('CSR_CHECK='+json.dumps(data),flush=True)
        focus_times={16902,16904,16906,16908,16910,16950,16952,16954,16956,16958,16960,16968,16970}
        for row in check.rows:
            if row['edge_time'] in focus_times or row['target_ids']:print('CSR_FOCUS='+json.dumps(row),flush=True)
        print('VDOT_CSR_COMMIT_REQUEST_PASS' if data['checks_passed'] else 'VDOT_CSR_COMMIT_REQUEST_FAIL',flush=True)
        return 0 if data['checks_passed'] else 2
    except Exception as error:
        result.update(status='failed',error=str(error));print('CSR_ERROR='+str(error),flush=True);return 2
    finally:
        signal.alarm(0);result['elapsed_seconds']=round(time.monotonic()-started,3);dump(out/'result.json',result);print('LOG_DIR='+str(out),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args();sys.exit(run(a.output.resolve()))
