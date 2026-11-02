"""Capture one bounded VCD window using the accepted emu/reference/image.
Inspect only the VCD header and bounded timestamp samples; no cancellation claim.
"""
import argparse,collections,datetime,hashlib,json,os,re,resource,signal,subprocess,time
from pathlib import Path

WORK=Path('/root/private_data/mj/xiangshan')
LOCATOR=WORK/'evidence/vdot-window-locate-v2-l7RZQD/result.json'
BEGIN,END,STOP=6978,9258,10000
WAVE_CAP=4*1024**3
LOG_CAP=128*1024**2
PINNED={
 str(WORK/'vdot-mtval-fix-20261024/XiangShan/build/emu'):'f9653532fd2a4b9f0d0cc08c131f7c258d4b62c46e672c6886d6643aad926850',
 str(WORK/'vdot-dev-20261024/NEMU/build/riscv64-nemu-interpreter-so'):'11b9f6807c36ed860e0c64cc4e58d27216b19335ecde1ce5797ba2d1cd057b74',
 str(WORK/'vdot-dev-20261024/NEMU/.config'):'64282bca051b5dbc5fca742f4fbca2ade937a70f3c4d2ec93c1f4836aca5d9be',
 str(WORK/'evidence/vdot-build-80mKCD/boot-flash.bin'):'fea548655a8b6eecacace83e2f4380a18b8aa83bce964c8aae4cffbe2f5a9724',
 str(WORK/'vdot-dev-20261024/nexus-am/apps/vdot-cancel-csr/build/vdot-cancel-csr-riscv64-xs.bin'):'3e0f4efa7cf32376768f72d52c78beb526bf4f3f12f16dab9f43a433c2e322bc',
}

def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        while chunk:=f.read(1024*1024):h.update(chunk)
    return h.hexdigest()

def build_argv(emu,img,ref,flash,wave):
    assert 0<=BEGIN<=END<STOP and END-BEGIN+1==2281
    return [emu,'-i',img,'--diff='+ref,'-F',flash,'--seed=1','--no-snapshot',
      '--dump-wave-full','--wave-path='+str(wave),'--dump-commit-trace',
      '--log-begin='+str(BEGIN),'--log-end='+str(END),'--max-cycles='+str(STOP),'--stat-cycles=1000']

def classify(path):
    p=path.lower();result=[]
    if 'vdot' in p:result.append('vdot_record' if 'trapinst' in p else 'vdot_fu')
    if 'cyclecnt' in p or p.endswith('.clock') or p.endswith('.timer'):result.append('clock_counter')
    backend='backend' in p or 'ctrlblock' in p
    if backend and ('redirect' in p or 'flush' in p):result.append('redirect_flush')
    if ('rob' in p and ('commit' in p or 'deq' in p or 'exception' in p)) or ('difftest' in p and ('commit' in p or 'archEvent' in path)):result.append('commit_identity')
    if backend and ('rename' in p or 'decode' in p) and any(s in p for s in ('instr','robidx','pdest','pc','valid','ready')):result.append('decode_rename')
    if backend and any(s in p for s in ('exu','scheduler','writeback')) and any(s in p for s in ('robidx','pdest','valid','ready')):result.append('issue_writeback')
    if backend and any(s in p for s in ('mstatus','dirty_vs','set_vstart','trapinst')):result.append('csr_state')
    return result

def inspect_vcd(path,out):
    scopes=[];variables=0;groups=collections.Counter();samples={};candidates=0;header_bytes=0;enddefs=False
    header_hash=hashlib.sha256();timescale=[];in_scale=False;first_time=None
    with open(path,'rb') as f,(out/'signal-candidates.tsv').open('w') as listing:
        listing.write('groups\twidth\tid\tpath\n')
        while raw:=f.readline(1024*1024):
            if len(raw)==1024*1024 and not raw.endswith(b'\n'):raise RuntimeError('Unexpected binary/overlong VCD header line')
            header_bytes+=len(raw)
            if header_bytes>64*1024**2:raise RuntimeError('VCD header exceeds 64MiB inspection cap')
            header_hash.update(raw);line=raw.decode('utf-8',errors='replace').strip();parts=line.split()
            if line.startswith('$timescale'):in_scale=True
            if in_scale:
                timescale.append(line)
                if '$end' in line:in_scale=False
            if not parts:continue
            if parts[0]=='$scope':scopes.append(parts[2])
            elif parts[0]=='$upscope':
                if not scopes:raise RuntimeError('Unbalanced VCD scope')
                scopes.pop()
            elif parts[0]=='$var':
                if len(parts)<6:raise RuntimeError('Malformed VCD variable')
                variables+=1;width=int(parts[2]);code=parts[3];name='.'.join(scopes+[parts[4]])
                tags=classify(name)
                if tags:
                    candidates+=1;listing.write(','.join(tags)+f'\t{width}\t{code}\t{name}\n')
                    for tag in tags:
                        groups[tag]+=1
                        if len(samples.setdefault(tag,[]))<5:samples[tag].append({'path':name,'width':width,'id':code})
            elif parts[0]=='$enddefinitions':enddefs=True;break
        if not enddefs or variables==0:raise RuntimeError('Missing/empty VCD header (wrong format or interrupted capture)')
        # Do not scan the entire waveform. Verilator normally emits #time before
        # its initial value dump; retain a small search allowance for variations.
        consumed=0
        while raw:=f.readline(1024*1024):
            consumed+=len(raw)
            if consumed>8*1024**2:raise RuntimeError('No first VCD timestamp in bounded initial sample')
            if re.fullmatch(rb'#[0-9]+\s*',raw.strip()):first_time=int(raw.strip()[1:]);break
        size=os.fstat(f.fileno()).st_size;offset=max(header_bytes,size-8*1024**2);f.seek(offset)
        if offset>header_bytes:f.readline() # discard possible partial line
        tail=f.read(8*1024**2)
    stamps=re.findall(rb'^#([0-9]+)\s*$',tail,re.M)
    last_time=int(stamps[-1]) if stamps else None
    if first_time is None or last_time is None or last_time<=first_time:raise RuntimeError('Insufficient VCD time span')
    return {'wave_bytes':size,'header_bytes':header_bytes,'header_sha256':header_hash.hexdigest(),
      'declared_variables':variables,'candidate_declarations':candidates,'groups':dict(groups),'samples':samples,
      'timescale_declaration':' '.join(timescale),'first_vcd_timestamp':first_time,'last_vcd_timestamp':last_time,
      'full_wave_sha256':'not computed; only header and bounded timestamp samples inspected',
      'clock_mapping':'not yet calibrated; do not equate these timestamps to GTimer/cycleCnt',
      'waveform_event_analysis_performed':False}

def inspect_log(path):
    result={'reference':False,'difftest':False,'cycle_limit':False,'usage':False,'bad':[],'target_commits':[]}
    ref=next(p for p in PINNED if p.endswith('-so'))
    with open(path,errors='replace') as f:
        for num,line in enumerate(f,1):
            line=re.sub(r'\x1b\[[0-9;]*m','',line)
            if 'The reference model is '+ref in line:result['reference']=True
            if 'Difftest enabled.' in line:result['difftest']=True
            if 'EXCEEDING CYCLE/INSTR LIMIT' in line:result['cycle_limit']=True
            if re.search(r'^\s*Usage:',line):result['usage']=True
            if re.search(r'HIT BAD TRAP|ABORT|different at pc|FAIL|invalid option|unrecognized option|Assertion.*failed',line):result['bad'].append({'line':num,'text':line.strip()[:320]})
            m=re.search(r'\bcommit\s+pc\s+(?:0x)?([0-9a-f]+)\s+inst\s+(?:0x)?([0-9a-f]{8})\b',line,re.I)
            if m and int(m[1],16) in (0x80000204,0x80000208):result['target_commits'].append({'line':num,'pc':hex(int(m[1],16)),'instruction':hex(int(m[2],16))})
    result['runtime_ok']=result['reference'] and result['difftest'] and result['cycle_limit'] and not result['bad']
    return result

def run(out):
    import shutil
    os.chdir(WORK);assert out.is_dir() and not (out/'result.json').exists(),'Fresh output directory required'
    report={'scope':'bounded waveform capture and header inventory only','status':'preflight',
      'start':datetime.datetime.now().astimezone().isoformat(),'cwd':str(WORK),'locator':str(LOCATOR),
      'window':{'begin':BEGIN,'end':END,'inclusive_cycles':2281,'stop_cycle':STOP},
      'wall_limit_seconds':600,'wave_file_cap_bytes':WAVE_CAP,'text_log_cap_bytes':LOG_CAP,
      'microarchitectural_cancellation_proven':False}
    def save():(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    save();proc=None
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
        prior=json.loads(LOCATOR.read_text());assert prior['status']=='window-ready' and prior['emu_exit']==0
        a=prior['analysis'];assert a['window_ready'] and a['selected_branch']['pc']=='0x80000204'
        assert a['suggested_wave_window']['begin']==BEGIN and a['suggested_wave_window']['end']==END
        assert prior['identity_before']==PINNED and prior['identity_after']==PINNED
        report['locator_sha256']=digest(LOCATOR);(out/'locator-result.json').write_text(json.dumps(prior,indent=2)+'\n')
        report['identity_before']={p:digest(p) for p in PINNED};assert report['identity_before']==PINNED,'Artifact identity drift'
        processes=subprocess.check_output(['ps','-eo','pid,comm'],text=True);(out/'processes-before.txt').write_text(processes)
        assert not any(x.split()[-1] in {'emu','java','mill','make','verilator_bin'} for x in processes.splitlines()[1:] if x.split()),'Existing build or simulation'
        report['free_bytes_before']=shutil.disk_usage(out).free
        assert report['free_bytes_before']>=8*1024**3,'Need 8GiB free; retain old evidence and stop'
        emu=next(p for p in PINNED if p.endswith('/build/emu'));ref=next(p for p in PINNED if p.endswith('-so'))
        img=next(p for p in PINNED if '/apps/' in p);flash=next(p for p in PINNED if p.endswith('boot-flash.bin'))
        wave=out/'cancel-window.vcd';log=out/'capture.log';(out/'build').mkdir()
        argv=build_argv(emu,img,ref,flash,wave);env=dict(os.environ,NOOP_HOME=str(out),NEMU_HOME=str(Path(ref).parents[1]))
        report.update(argv=argv,environment={'NOOP_HOME':str(out),'NEMU_HOME':env['NEMU_HOME']},status='running');save()
        print('CAPTURING begin=6978 end=9258 stop=10000 both_edges=true wall_limit=600s',flush=True)
        def constrain():resource.setrlimit(resource.RLIMIT_FSIZE,(WAVE_CAP,WAVE_CAP))
        start=time.monotonic();stop_reason=None
        with log.open('wb') as stream:
            proc=subprocess.Popen(argv,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,preexec_fn=constrain)
            while proc.poll() is None:
                if time.monotonic()-start>600:stop_reason='wall-time limit'
                elif log.stat().st_size>LOG_CAP:stop_reason='text-log size limit'
                elif wave.exists() and wave.stat().st_size>=WAVE_CAP:stop_reason='wave size limit'
                if stop_reason:
                    stop_child()
                    break
                time.sleep(0.25)
        rc=proc.returncode;report.update(emu_exit=rc,stop_reason=stop_reason,elapsed_seconds=round(time.monotonic()-start,3))
        report['runtime']=inspect_log(log)
        report['identity_after']={p:digest(p) for p in PINNED}
        assert report['identity_after']==PINNED,'Artifact identity drift after capture'
        print('CAPTURE_EMU_EXIT='+str(rc),flush=True)
        if stop_reason or rc!=0 or not report['runtime']['runtime_ok']:
            raise RuntimeError('Capture runtime rejected; retain log and partial wave, no automatic rerun')
        assert wave.is_file() and 0<wave.stat().st_size<WAVE_CAP,'Wave missing, empty or at size cap'
        report['vcd']=inspect_vcd(wave,out);report['status']='captured-inventory-ready'
        print('WAVE_BYTES='+str(report['vcd']['wave_bytes']),flush=True)
        print('VCD_TIMES='+json.dumps({k:report['vcd'][k] for k in ('timescale_declaration','first_vcd_timestamp','last_vcd_timestamp')}),flush=True)
        print('SIGNAL_GROUP_COUNTS='+json.dumps(report['vcd']['groups']),flush=True)
        print('VDOT_SIGNAL_SAMPLES='+json.dumps(report['vcd']['samples'].get('vdot_fu',[])),flush=True)
        print('CLOCK_SIGNAL_SAMPLES='+json.dumps(report['vcd']['samples'].get('clock_counter',[])),flush=True)
        print('TARGET_COMMIT_ROWS='+json.dumps(report['runtime']['target_commits'][:24]),flush=True)
        print('VDOT_BOUNDED_WAVE_CAPTURED',flush=True)
        return 0
    except BaseException as err:
        stop_child()
        report.update(status='failed',error=str(err));print('CAPTURE_ERROR='+str(err),flush=True);return 2
    finally:
        report['end']=datetime.datetime.now().astimezone().isoformat();save();print('LOG_DIR='+str(out),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('output',type=Path);args=parser.parse_args();raise SystemExit(run(args.output.resolve()))
