"""Capture the accepted VDot/VIOTA candidate window; inventory for script and GTKWave review."""
import argparse,datetime,hashlib,importlib.util,json,os,re,resource,shutil,signal,subprocess,sys,time
from pathlib import Path
WORK=Path('/root/private_data/mj/xiangshan')
SAVED=WORK/'evidence/vdot-port-candidate-eDAWKv'
LOCATOR=SAVED/'result.json'
RUNNER=WORK/'evidence/vdot-port-candidate-package-ICvzS7/package/run.py'
RUNNER_SHA='4716598ff39017725b7d9860da902fda9a4e0ff9465bbf7c34a06134c75a667d'
CAPTURE_HELPER=WORK/'evidence/vdot-wave-window-Cpa0HX/capture.py'
CAPTURE_SHA='2bb3099782d9bca14b17174994b5153086e10fbb4d5fef236b3d70d3f074f00c'
PARSER=WORK/'evidence/vdot-mixed-reparse-nIu7DA/mixed_parser.py'
PARSER_SHA='dabb0c77b8ab6a5f0dc05abd2602ec77d0ee99869dc1eb837570a9c21c646704'
IMG=str(WORK/'vdot-dev-20261024/nexus-am/apps/vdot-port-contend-v1/build/vdot-port-contend-v1-riscv64-xs.bin')
# Image identity comes from the accepted server build record, not the local build.
BEGIN,END,STOP=5978,8258,9000
TARGETS={0x80000170:0x82112057,0x80000174:0x0020818b,0x80000178:0x52082257}
WAVE_CAP=4*1024**3;LOG_CAP=128*1024**2

def require(ok,msg):
    if not ok:raise RuntimeError(msg)
def dump(p,obj):p.write_text(json.dumps(obj,indent=2)+'\n')
def load(name,path,sha):
    require(hashlib.sha256(path.read_bytes()).hexdigest()==sha,'Helper identity mismatch: '+str(path))
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def validate_locator(prior,pinned,identities,arch,before,after):
    require(prior['status']=='candidate-architecture-and-window-ready','Candidate run not accepted')
    require([(s['name'],s['exit']) for s in prior['stages']]==[('build',0),('architecture',0),('prefix',0)],'Stage exits differ')
    require(prior['window']['begin']==BEGIN and prior['window']['end']==END,'Window differs')
    require([(int(e['pc'],16),int(e['word'],16)) for e in prior['first_cluster']]==list(TARGETS.items()),'Target cluster differs')
    require(prior['application']==IMG,'Candidate application path differs')
    require(all(arch[k] for k in ('reference','difftest','good_trap','arch_marker')) and not arch['errors'] and not arch['usage'] and not arch['limit'],'Architecture checks incomplete')
    require(before==after==pinned,'Baseline identity record differs')
    require(set(identities)==set(pinned)|{IMG},'Unexpected runtime identity set')
    require(all(identities[k]==v for k,v in pinned.items()),'Runtime baseline differs')
    require(bool(re.fullmatch('[0-9a-f]{64}',identities[IMG])),'Missing saved application hash')

def gtk_inventory(out):
    selected=[]
    for line in (out/'signal-candidates.tsv').read_text().splitlines()[1:]:
        tags,width,ident,path=line.split('\t',3)
        if 'gtk_overview' in tags.split(','):selected.append({'path':path,'width':int(width),'id':ident})
    require(selected,'No GTKWave overview signals found')
    dump(out/'gtkwave-overview-signals.json',selected)
    (out/'gtkwave-overview-signals.txt').write_text('\n'.join(x['path'] for x in selected)+'\n')
    return len(selected)

def overview_signal(path):
    if path in ('TOP.clock','TOP.SimTop.timer'):return True
    if path.endswith(('.backend.inner_wbDataPath.clock','.backend.inner_wbDataPath.reset')):return True
    if re.search(r'\.inner_dataPath\.io_fromVfIQ_0_[01]_(valid|ready|bits_common_(robIdx_(flag|value)|pdest|vecWen))$',path):return True
    if re.search(r'\.inner_vfExuBlock\.exus(?:_1)?\.io_(in|out)_(valid|ready|bits_(robIdx_(flag|value)|pdest))$',path):return True
    if re.search(r'\.(vfWbBusyArbiter|vfWbArbiter)\.arbiters_0\.(io_in_[01]_(valid|ready)|io_out_(valid|ready)|io_chosen|clock|reset)$',path):return True
    return False

def inspect_log(lines,reference,classify):
    r={'reference':False,'difftest':False,'cycle_limit':False,'usage':False,'error_count':0,'errors':[],'target_commits':[]}
    for n,raw in enumerate(lines,1):
        line=re.sub(r'\x1b\[[0-9;]*m','',raw)
        r['reference']|=('The reference model is '+reference) in line
        r['difftest']|='Difftest enabled.' in line;r['cycle_limit']|='EXCEEDING CYCLE/INSTR LIMIT' in line
        r['usage']|=bool(re.search(r'^\s*Usage:',line,re.I))
        kind=classify(line)
        if kind not in (None,'perf-counter'):
            r['error_count']+=1
            if len(r['errors'])<20:r['errors'].append({'line':n,'kind':kind,'text':line.strip()[:300]})
        m=re.search(r'\bcommit\s+pc\s+(?:0x)?([0-9a-f]+)\s+inst\s+(?:0x)?([0-9a-f]{8})\b',line,re.I)
        if m and int(m[1],16) in TARGETS:
            pc,word=int(m[1],16),int(m[2],16)
            require(len(r['target_commits'])<128,'Unexpected target repetition cap')
            r['target_commits'].append({'line':n,'pc':hex(pc),'instruction':hex(word)})
            if word!=TARGETS[pc]:r['error_count']+=1;r['errors'].append({'line':n,'kind':'target-word-mismatch'})
    first=[(int(v['pc'],16),int(v['instruction'],16)) for v in r['target_commits'][:3]]
    r['target_cluster_seen']=first==list(TARGETS.items())
    r['runtime_ok']=r['reference'] and r['difftest'] and r['cycle_limit'] and not r['usage'] and not r['error_count'] and r['target_cluster_seen']
    return r

def run(out):
    require(out.is_dir() and not (out/'result.json').exists(),'Fresh output directory required')
    result={'status':'preflight','cwd':str(WORK),'argv_runner':sys.argv,'python':sys.version,
        'start':datetime.datetime.now().astimezone().isoformat(),'scope':'bounded shared-port candidate capture; no contention acceptance',
        'window':{'begin':BEGIN,'end':END,'inclusive_cycles':2281,'stop_cycle':STOP},'seed':1,
        'wall_limit_seconds':600,'wave_file_cap_bytes':WAVE_CAP,'log_cap_bytes':LOG_CAP,
        'contention_proven':False,'new_build':False}
    proc=None
    def stop_child():
        if proc is not None and proc.poll() is None:
            try:os.killpg(proc.pid,signal.SIGTERM)
            except ProcessLookupError:pass
            try:proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                try:os.killpg(proc.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                proc.wait()
    try:
        helper=load('capture_base',CAPTURE_HELPER,CAPTURE_SHA);parser=load('failure_parser',PARSER,PARSER_SHA)
        require(helper.digest(RUNNER)==RUNNER_SHA,'Accepted candidate runner changed')
        pinned={p:h for p,h in helper.PINNED.items() if '/apps/' not in p}
        prior=json.loads(LOCATOR.read_text());identities=json.loads((SAVED/'runtime-identities.json').read_text())
        arch=json.loads((SAVED/'architecture-check.json').read_text())
        before=json.loads((SAVED/'identity-before.json').read_text());after=json.loads((SAVED/'identity-after.json').read_text())
        validate_locator(prior,pinned,identities,arch,before,after);pinned=identities
        dump(out/'accepted-input-record-hashes.json',{p:helper.digest(SAVED/p) for p in
            ('result.json','runtime-identities.json','architecture-check.json','identity-before.json','identity-after.json')})
        dump(out/'locator-result.json',prior);result['locator_sha256']=helper.digest(LOCATOR)
        result['identity_before']={p:helper.digest(p) for p in pinned};require(result['identity_before']==pinned,'Artifact identity drift')
        processes=subprocess.check_output(['ps','-eo','pid,comm'],text=True);(out/'processes-before.txt').write_text(processes)
        require(not any(v.split()[-1] in {'emu','java','mill','make','verilator_bin'} for v in processes.splitlines()[1:] if v.split()),'Existing build or simulation; stop')
        result['free_bytes_before']=shutil.disk_usage(out).free;require(result['free_bytes_before']>=8*1024**3,'Need 8GiB free; preserve old evidence and stop')
        emu=next(p for p in pinned if p.endswith('/build/emu'));ref=next(p for p in pinned if p.endswith('-so'))
        flash=next(p for p in pinned if p.endswith('boot-flash.bin'))
        helper.BEGIN,helper.END,helper.STOP=BEGIN,END,STOP
        wave=out/'port-window.vcd';log=out/'capture.log';(out/'build').mkdir()
        argv=helper.build_argv(emu,IMG,ref,flash,wave);env=dict(os.environ,NOOP_HOME=str(out),NEMU_HOME=str(Path(ref).parents[1]))
        result.update(argv=argv,environment={'NOOP_HOME':str(out),'NEMU_HOME':env['NEMU_HOME']},status='running')
        dump(out/'argv.json',argv);dump(out/'result.json',result)
        print('CAPTURING_PORT begin=5978 end=8258 stop=9000 both_edges=true wall_limit=600s',flush=True)
        def constrain():resource.setrlimit(resource.RLIMIT_FSIZE,(WAVE_CAP,WAVE_CAP))
        start=time.monotonic();reason=None
        with log.open('wb') as stream:
            proc=subprocess.Popen(argv,cwd=WORK,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,preexec_fn=constrain)
            while proc.poll() is None:
                if time.monotonic()-start>600:reason='wall-time limit'
                elif log.stat().st_size>LOG_CAP:reason='text-log size limit'
                elif wave.exists() and wave.stat().st_size>=WAVE_CAP:reason='wave size limit'
                if reason:stop_child();break
                time.sleep(0.25)
        result.update(emu_exit=proc.returncode,stop_reason=reason,elapsed_seconds=round(time.monotonic()-start,3))
        with log.open(errors='replace') as f:result['runtime']=inspect_log(f,ref,parser.classify_failure)
        result['identity_after']={p:helper.digest(p) for p in pinned};require(result['identity_after']==pinned,'Identity drift after capture')
        print('CAPTURE_EMU_EXIT='+str(proc.returncode),flush=True)
        require(reason is None and proc.returncode==0 and result['runtime']['runtime_ok'],'Capture rejected; retain log/partial wave, no automatic retry')
        require(wave.is_file() and 0<wave.stat().st_size<WAVE_CAP,'Wave missing, empty or capped')
        original_classify=helper.classify
        def groups(path):
            tags=original_classify(path)
            if overview_signal(path):tags.append('gtk_overview')
            if '.inner_vfExuBlock.' in path:tags.append('vector_execute')
            if '.inner_wbDataPath.' in path:tags.append('writeback_arbitration')
            if 'vfWbBusy' in path:tags.append('issue_wb_busy')
            return tags
        helper.classify=groups
        result['vcd']=helper.inspect_vcd(wave,out);result['status']='port-captured-inventory-ready'
        result['gtk_overview_signal_count']=gtk_inventory(out)
        print('GTK_OVERVIEW_SIGNALS='+str(result['gtk_overview_signal_count']),flush=True)
        print('CAPTURE_IDENTITIES='+json.dumps(pinned),flush=True)
        print('WAVE_BYTES='+str(result['vcd']['wave_bytes']),flush=True)
        print('VCD_TIMES='+json.dumps({k:result['vcd'][k] for k in ('timescale_declaration','first_vcd_timestamp','last_vcd_timestamp')}),flush=True)
        print('SIGNAL_GROUP_COUNTS='+json.dumps(result['vcd']['groups']),flush=True)
        print('TARGET_COMMIT_ROWS='+json.dumps(result['runtime']['target_commits'][:12]),flush=True)
        print('VDOT_PORT_BOUNDED_WAVE_CAPTURED',flush=True);return 0
    except Exception as error:
        stop_child();result.update(status='failed',error=str(error));print('PORT_CAPTURE_ERROR='+str(error),flush=True);return 2
    finally:
        stop_child();result['end']=datetime.datetime.now().astimezone().isoformat();dump(out/'result.json',result);print('LOG_DIR='+str(out),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args();sys.exit(run(a.output.resolve()))
