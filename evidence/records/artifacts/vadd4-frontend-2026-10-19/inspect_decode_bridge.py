"""Read IBuffer -> CtrlBlock decode buffer -> DecodeStage in the existing VADD VCD.
No RTL simulation. Produces JSON on stdout; run wrapper chooses evidence files.
"""
import hashlib,json,platform,re,sys
from pathlib import Path

BASE='TOP.SimTop.l_soc.core_with_l2.core.'
SCOPES={'ibuffer':BASE+'frontend.inner_ibuffer',
        'ctrl':BASE+'backend.inner_ctrlBlock',
        'decode':BASE+'backend.inner_ctrlBlock.decode'}
TIMES=range(5085,5114)
def wanted(key,n):
    if n in {'clock','reset'}:return True
    fields=r'(pc|instr|ftqPtr_(flag|value)|ftqOffset)'
    if key=='ibuffer':
        return n in {'io_flush','io_decodeCanAccept'} or bool(re.fullmatch(r'io_out_\d+_(valid|ready|bits_'+fields+r')',n))
    if key=='decode':
        return n=='io_redirect' or bool(re.fullmatch(r'io_in_\d+_(valid|ready|bits_'+fields+r')',n))
    return n in {'io_frontend_canAccept','decodeBufAcceptNum','decodeFromFrontendAcceptNum'} or bool(
        re.fullmatch(r'io_frontend_cfVec_\d+_(valid|ready|bits_'+fields+r')',n) or
        re.fullmatch(r'decodeBufValid_\d+',n) or
        re.fullmatch(r'decodeBufBits_\d+_'+fields,n))
def inspect(p):
    stack=[];signals={};widths={};values={};time=0;rows=[]
    def snapshot():
        if time in TIMES:
            rows.append({'time_ps':time,'scopes':{key:{n:hex(values[i]) if values.get(i) is not None else None
                for (k,n),i in signals.items() if k==key} for key in SCOPES}})
    with p.open() as f:
        for line in f:
            t=line.split()
            if not t:continue
            if t[0]=='$scope':stack.append(t[2])
            elif t[0]=='$upscope':stack.pop()
            elif t[0]=='$var':
                scope='.'.join(stack)
                for key,path in SCOPES.items():
                    if scope==path and wanted(key,t[4]):
                        signals[key,t[4]]=t[3];widths[key+'.'+t[4]]=int(t[2])
            elif t[0]=='$enddefinitions':break
        ids=set(signals.values())
        for line in f:
            if line[0]=='#':
                snapshot();time=int(line[1:])
                if time>max(TIMES):break
            elif line[0]=='b':
                b,i=line[1:].split()
                if i in ids:values[i]=int(b,2) if set(b)<={'0','1'} else None
            elif line[0] in '01xz':
                i=line[1:].strip()
                if i in ids:values[i]=int(line[0]) if line[0] in '01' else None
    with p.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
    return {'vcd':str(p),'bytes':p.stat().st_size,'sha256':digest,'python':platform.python_version(),
            'scopes':SCOPES,'widths':widths,'samples':rows,
            'scope_limit':'Existing trace, settled timestamp samples; user observations recorded separately.'}
if __name__=='__main__':
    print(json.dumps(inspect(Path(sys.argv[1])),indent=2))
