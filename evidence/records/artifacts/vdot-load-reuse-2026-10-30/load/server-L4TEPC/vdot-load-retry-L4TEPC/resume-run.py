"""Build a fresh segmented-dot application; equal-output register/materialized schedules.
No core/reference rebuild, waveform, or automatic speedup acceptance.
"""
import hashlib,json,os,re,resource,shutil,signal,statistics,struct,subprocess,sys,time
from pathlib import Path
from failure_parser import classify_failure
WORK=Path('/root/private_data/mj/xiangshan');APP=None
XS=WORK/'vdot-mtval-fix-20261024/XiangShan';AM=WORK/'vdot-dev-20261024/nexus-am';NM=WORK/'vdot-dev-20261024/NEMU'
EMU=XS/'build/emu';REF=NM/'build/riscv64-nemu-interpreter-so';FLASH=WORK/'evidence/vdot-build-80mKCD/boot-flash.bin'
PIN={str(EMU):'f9653532fd2a4b9f0d0cc08c131f7c258d4b62c46e672c6886d6643aad926850',
 str(REF):'11b9f6807c36ed860e0c64cc4e58d27216b19335ecde1ce5797ba2d1cd057b74',
 str(NM/'.config'):'64282bca051b5dbc5fca742f4fbca2ade937a70f3c4d2ec93c1f4836aca5d9be',
 str(FLASH):'fea548655a8b6eecacace83e2f4380a18b8aa83bce964c8aae4cffbe2f5a9724'}
def require(ok,msg):
    if not ok:raise RuntimeError(msg)
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024**2),b''):h.update(b)
    return h.hexdigest()
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def inspect(lines,reference,targets,marker):
    r={'reference':False,'difftest':False,'good_trap':False,'limit':False,'usage':False,'errors':[],
       'arch_marker':False,'commits':0,'targets':[]};last=None;pending=[]
    for n,raw in enumerate(lines,1):
        line=re.sub(r'\x1b\[[0-9;]*m','',raw)
        r['reference']|=('The reference model is '+reference) in line
        r['difftest']|='Difftest enabled.' in line;r['good_trap']|='HIT GOOD TRAP' in line
        r['limit']|='EXCEEDING CYCLE/INSTR LIMIT' in line;r['usage']|=bool(re.match(r'^\s*Usage:',line,re.I))
        r['arch_marker']|=marker in line
        kind=classify_failure(line)
        if kind not in (None,'perf-counter') and len(r['errors'])<20:r['errors'].append({'line':n,'kind':kind,'text':line.strip()[:300]})
        tick=re.search(r'\[PERF\s*\]\s*\[time=\s*(\d+)\]',line)
        if tick and int(tick[1])!=last:
            value=int(tick[1])
            require(last is None or value>=last,'Nonmonotonic PERF time')
            for event in pending:event['next_perf_time']=value
            pending=[];last=value
        m=re.search(r'\bcommit\s+pc\s+(?:0x)?([0-9a-f]+)\s+inst\s+(?:0x)?([0-9a-f]{8})\b',line,re.I)
        if m:
            r['commits']+=1;pc,word=int(m[1],16),int(m[2],16)
            if pc in targets:
                require(word==targets[pc]['word'],'Target word differs from image')
                require(len(r['targets'])<64,'Unexpected target repetition')
                event={'line':n,'pc':hex(pc),'word':hex(word),'name':targets[pc]['name'],
                    'previous_perf_time':last,'next_perf_time':None}
                r['targets'].append(event);pending.append(event)
    r['help_only']=r['usage'] and not r['difftest'] and r['commits']==0
    return r

def inspect_samples(lines,matrix):
    pattern=re.compile(r'OPT_SAMPLE warm=(\d+) round=(\d+) position=(\d+) variant=(\d+) cycles=(\d+) instret=(\d+) consumer=(\d+)')
    rows=[];count=len(matrix['variants'])
    for line in lines:
        m=pattern.search(line)
        if m:rows.append(dict(zip(('warm','round','position','variant','cycles','instret','consumer'),map(int,m.groups()))))
    require(len(rows)==matrix['calls'],'Wrong number of complete samples')
    for i,row in enumerate(rows):
        rnd,pos=divmod(i,count);k=(pos+rnd)%count
        require((row['round'],row['position'],row['warm'],row['variant'])==(rnd,pos,int(rnd<matrix['warm_rounds']),k),'Sample order/rotation mismatch')
        v=matrix['variants'][k]
        require(0<row['cycles']<=0x7fffffff and row['instret']==v['expected_instret'] and row['consumer']==v['consumer'],'Counter/consumer mismatch')
    stats=[]
    for k,v in enumerate(matrix['variants']):
        vals=[r['cycles'] for r in rows if not r['warm'] and r['variant']==k]
        require(len(vals)==matrix['rounds'],'Missing formal sample')
        stats.append(dict(variant=v['name'],kind=v['kind'],mode=v['mode'],group=v['group'],dot_operations=v['iterations'],outputs=v['outputs'],dynamic_vector_loads=v['dynamic_vector_loads'],final_output_bytes=v['final_output_bytes'],samples=len(vals),raw_cycle_min=min(vals),raw_cycle_median=statistics.median(vals),raw_cycle_max=max(vals),instret=v['expected_instret'],formal_cycles=vals))
    return rows,stats


def check_kernel(image,symbols,v):
    fn='opt_'+v['name'];start,end=symbols[fn+'_payload_begin'],symbols[fn+'_payload_end']
    cb,ce=symbols[fn+'_counter_begin'],symbols[fn+'_counter_end'];base=0x80000000
    word=lambda pc:struct.unpack_from('<I',image,pc-base)[0]
    lo,hi=symbols[fn],symbols[fn+'_code_end']
    require(0<=lo-base<cb-base<ce-base<hi-base<=len(image),'Function outside image')
    require(hashlib.sha256(image[lo-base:hi-base]).hexdigest()==v['code_sha256'],'Compiled kernel differs from locally checked function: '+v['name'])
    require(start==cb+16 and ce==end+28 and end-start==4*v['payload_static_instructions'],'Counter/payload boundary differs')
    require(word(cb-8)==0x0330000f and word(cb-4)==word(ce)==0x34029073,'Pre-fence or outer barrier missing')
    require([word(cb+i) for i in (0,4,8,12)]==[0xb0002373,0x34029073,0xb02023f3,0x34029073],'Start boundary differs')
    off=v['last_output_offset']
    require([word(p) for p in range(end,ce,4)]==[0x0330000f,(off<<20)|0x0005ae03,0x7ffe7e13,0x340e1073,0xb0202ef3,0x34029073,0xb0002f73],'End fence/readback boundary differs')
    return dict(name=v['name'],code_sha256=v['code_sha256'],payload_begin=hex(start),payload_end=hex(end),
      group=v['group'],mode=v['mode'],expected_instret=v['expected_instret'],static_instructions=v['payload_static_instructions'])

def comparisons(stats,matrix):
    idx={(s['kind'],s['mode']):s['raw_cycle_median'] for s in stats if s['outputs']};ratios=[]
    pairs=[('tu','ta'),('ta','ta_rr')] if matrix['experiment']=='load' else [('independent','reuse')]
    for kind in ('native','rvv_mf2'):
        for before,after in pairs:
            ratios.append(dict(comparison='same_implementation',kind=kind,before=before,after=after,before_cycles=idx[kind,before],after_cycles=idx[kind,after],ratio=idx[kind,before]/idx[kind,after]))
    for mode in dict.fromkeys(s['mode'] for s in stats if s['outputs']):
        ratios.append(dict(comparison='same_schedule_rvv_over_native',mode=mode,native_cycles=idx['native',mode],baseline_cycles=idx['rvv_mf2',mode],ratio=idx['rvv_mf2',mode]/idx['native',mode]))
    return dict(status='review_required',items=ratios,scope='same task within experiment; raw windows; no resource attribution')


def run(package,out):
    global APP
    summary={'status':'preflight','scope':'prewarmed software-only input-load/data-reuse comparison','performance_measured':False,
        'cwd':str(WORK),'argv':sys.argv,'python':sys.version,'seed':1,'stages':[]};env=dict(os.environ,AM_HOME=str(AM),NEMU_HOME=str(NM),NOOP_HOME=str(out),PYTHONDONTWRITEBYTECODE='1')
    (out/'build').mkdir();dump(out/'environment.json',{k:env[k] for k in ('AM_HOME','NEMU_HOME','NOOP_HOME')})
    def stage(name,argv,seconds):
        dump(out/(name+'.argv.json'),argv);print('RUNNING='+name+' wall_limit='+str(seconds),flush=True)
        def cap():resource.setrlimit(resource.RLIMIT_FSIZE,(128*1024**2,128*1024**2))
        start=time.monotonic()
        with (out/(name+'.log')).open('wb') as f:
            proc=subprocess.Popen(argv,cwd=WORK,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,preexec_fn=cap)
            try:
                while True:
                    remaining=seconds-(time.monotonic()-start)
                    if remaining<=0:raise subprocess.TimeoutExpired(argv,seconds)
                    try:rc=proc.wait(timeout=min(60,remaining));break
                    except subprocess.TimeoutExpired:
                        elapsed=int(time.monotonic()-start)
                        print('PROGRESS stage='+name+' elapsed_s='+str(elapsed)+' log_bytes='+str((out/(name+'.log')).stat().st_size),flush=True)
            except BaseException as error:
                os.killpg(proc.pid,signal.SIGTERM)
                try:proc.wait(timeout=5)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
                summary['stages'].append({'name':name,'exit':proc.returncode,'error':str(error),
                    'wall_seconds':round(time.monotonic()-start,3)})
                dump(out/'result.json',summary)
                print(name.upper()+'_EXIT='+str(proc.returncode)+' STOP='+type(error).__name__,flush=True)
                raise
        summary['stages'].append({'name':name,'exit':rc,'wall_seconds':round(time.monotonic()-start,3)})
        dump(out/'result.json',summary);print(name.upper()+'_EXIT='+str(rc),flush=True)
        require(rc==0,name+' failed; inspect '+str(out/(name+'.log')))
    checked=False
    try:
        matrix=json.loads((package/'matrix.json').read_text());APP=matrix['app'];require(APP in ('vdot-load-v1','vdot-tile-v1'),'Unexpected application');shutil.copyfile(package/'matrix.json',out/'matrix.json')
        accepted=WORK/'evidence/vdot-segment-Pw1wQ8'
        previous=json.loads((accepted/'result.json').read_text())
        require(previous['status']=='vdot-segment-raw-results-review-required' and previous['calls']==52 and previous['samples']==39,
                'Prior segmented-dot run incomplete')
        require([(r['name'],r['exit']) for r in previous['stages']]==[('build',0),('architecture',0)],'Prior segmented-dot stages failed')
        previous_img=str(AM/'apps/vdot-segment-v1/build/vdot-segment-v1-riscv64-xs.bin')
        previous_ids=json.loads((accepted/'runtime-identities.json').read_text())
        require(previous_ids==PIN|{previous_img:'bd034d3d3bebae84c68d26d5b2d52c6420f26ea89c41178621a217321c0aac8b'},'Prior segmented-dot identities differ')
        require(sha(previous_img)==previous_ids[previous_img],'Preserve prior segmented-dot image')
        dump(out/'accepted-segment.json',previous)
        for rel,digest in matrix['source_sha256'].items():require(sha(XS/rel)==digest,'Counter ordering source changed: '+rel)
        require({p:sha(p) for p in PIN}==PIN,'Pinned core/reference identity differs');checked=True
        dump(out/'identity-before.json',PIN)
        procs=subprocess.check_output(['ps','-eo','pid,comm'],text=True);(out/'processes-before.txt').write_text(procs)
        require(not any(x.split()[-1] in {'emu','make','java','mill','verilator_bin'} for x in procs.splitlines()[1:]),'Existing build or simulation; stop')
        with (out/'repositories.txt').open('w') as log:
            for repo in (XS,NM,AM):
                log.write('REPO='+str(repo)+'\n');log.flush()
                for args in (['rev-parse','--show-toplevel','HEAD'],['branch','--show-current'],['status','--short'],['diff','--stat','--','apps/'+APP],['diff','--cached','--stat','--','apps/'+APP]):
                    rc=subprocess.call(['git','-C',str(repo),*args],stdout=log,stderr=log,env=dict(env,GIT_OPTIONAL_LOCKS='0'))
                    log.write('EXIT='+str(rc)+'\n');log.flush()
                    if rc and repo!=AM:raise RuntimeError('Repository identity unavailable: '+str(repo))
        old=WORK/'evidence/vdot-load-m5fpvT'
        prior=json.loads((old/'result.json').read_text())
        require(APP=='vdot-load-v1','Unexpected app')
        require(any(s['name']=='build' and s['exit']==0 for s in prior['stages']),'No successful prior build')
        dest=AM/'apps'/APP
        source_ids=json.loads((old/'application-source-identities.json').read_text())
        for name in ('main.c','cases.S','Makefile'):
            require(sha(dest/name)==sha(package/APP/name)==source_ids[name],'Application source changed: '+name)
        old_ids=json.loads((old/'runtime-identities.json').read_text())
        image_path=dest/'build'/f'{APP}-riscv64-xs.bin'
        require(sha(image_path)==sha(old/image_path.name)==old_ids[str(image_path)],'Application image changed')
        elf_path=image_path.with_suffix('.elf')
        require(sha(elf_path)==sha(old/elf_path.name),'Application ELF changed')
        shutil.copy2(old/'compiler.txt',out/'compiler.txt')
        summary['stages'].append(dict(name='build_reuse',exit=0,origin=str(old),compiler_record='copied from prior build'))
        dump(out/'build-reuse.json',dict(origin=str(old),source_sha256=source_ids,image_sha256=sha(image_path),elf_sha256=sha(elf_path)))
        print('BUILD_REUSED=1',flush=True)
        elf=dest/'build'/f'{APP}-riscv64-xs.elf';img=elf.with_suffix('.bin');image=img.read_bytes()
        nm=subprocess.check_output(['riscv64-linux-gnu-nm','-n',str(elf)],text=True);(out/'symbols.nm').write_text(nm)
        symbols={v[2]:int(v[0],16) for s in nm.splitlines() if len(v:=s.split())==3}
        with (out/'disasm.txt').open('w') as f:subprocess.run(['riscv64-linux-gnu-objdump','-d',str(elf)],stdout=f,check=True)
        kernels=[check_kernel(image,symbols,v) for v in matrix['variants']]
        dump(out/'kernel-identities.json',kernels);ids=PIN|{str(img):sha(img)};dump(out/'runtime-identities.json',ids)
        shutil.copy2(elf,out/elf.name);shutil.copy2(img,out/img.name)
        shutil.copytree(package/APP,out/'application-source')
        dump(out/'application-source-identities.json',{n:sha(package/APP/n) for n in ('main.c','cases.S','Makefile')})
        for k in kernels:print('KERNEL='+json.dumps(k),flush=True)
        common=[str(EMU),'-i',str(img),'--diff='+str(REF),'-F',str(FLASH),'--seed=1','--no-snapshot']
        stage('architecture',common+['--max-cycles=4000000'],10800)
        with (out/'architecture.log').open(errors='replace') as f:a=inspect(f,str(REF),{},matrix['pass_marker'])
        dump(out/'architecture-check.json',a)
        selected={'clock_cycle','commitInstr','waitLoadCycle','waitStoreCycle','waitFenCycle','sbuffer_req_valid','sbuffer_req_fire','dcache_req_valid','dcache_req_fire'}
        perf=[]
        with (out/'architecture.log').open(errors='replace') as f:
            for raw in f:
                clean=re.sub(r'\x1b\[[0-9;]*m','',raw)
                m=re.search(r'\[PERF\s*\]\s*\[time=\s*(\d+)\]\s*(.*):\s*(\w+),\s*([+-]?\d+)\s*$',clean)
                if m and m[3] in selected:perf.append(dict(time=int(m[1]),path=m[2],counter=m[3],value=int(m[4])))
        dump(out/'perf-context.json',dict(scope='whole_application_not_per_kernel',records=perf))
        require(a['reference'] and a['difftest'] and a['good_trap'] and a['arch_marker'] and not a['errors'] and not a['usage'] and not a['limit'],'Architecture runtime checks failed')
        with (out/'architecture.log').open(errors='replace') as log:
            shown=0
            for line in log:
                if any(s in line for s in ('The reference model is ','Difftest enabled.','PASS VDOT_OPT_','HIT GOOD TRAP')):
                    print(line.strip(),flush=True);shown+=1
                    if shown>=8:break
        require({p:sha(p) for p in ids}==ids,'Runtime artifact changed')
        with (out/'architecture.log').open(errors='replace') as f:samples,stats=inspect_samples(f,matrix)
        dump(out/'samples.json',samples);dump(out/'raw-statistics.json',stats)
        (out/'samples.csv').write_text('warm,round,position,variant,cycles,instret,consumer\n'+
            ''.join(','.join(str(r[k]) for k in ('warm','round','position','variant','cycles','instret','consumer'))+'\n' for r in samples))
        summary.update(status='vdot-opt-raw-results-review-required',experiment=matrix['experiment'],calls=matrix['calls'],samples=matrix['samples'],warmups=matrix['warmups'],
            performance_measured=True,final_speedup_accepted=False,application=str(img),scope='equal-output software-only experiments; loads, compute, loop, output, fence/readback counted')
        dump(out/'comparisons.json',comparisons(stats,matrix))
        print('OPT_IDENTITIES='+json.dumps(ids),flush=True)
        for stat in stats:print('OPT_RAW='+json.dumps(stat),flush=True)
        print('VDOT_OPT_READY experiment='+matrix['experiment']+' samples='+str(matrix['samples'])+' warmups='+str(matrix['warmups']),flush=True)
        print('SCOPE=prewarmed_load_or_tile equal_output_control no_cold_DRAM_claim',flush=True);return 0
    except Exception as error:
        summary.update(status='failed',error=str(error));print('OPT_ERROR='+str(error),flush=True);return 2
    finally:
        if checked:
            after={p:sha(p) for p in PIN};dump(out/'identity-after.json',after)
            if after!=PIN:
                summary.update(status='failed',error='Pinned identity changed after run')
                dump(out/'result.json',summary);print('OPT_ERROR=Identity drift after run',flush=True);return 2
        dump(out/'result.json',summary);print('LOG_DIR='+str(out),flush=True)

if __name__=='__main__':
    sys.exit(run(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve()))
