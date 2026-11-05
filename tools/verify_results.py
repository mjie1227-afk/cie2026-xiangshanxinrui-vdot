"""Validate one exact suite directory from raw logs and recorded input identities."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
from run_case import MARKERS, assess

BASIC = ['hello-meijie', 'vadd4', 'vdot-smoke']
SUITES = {
    'smoke': BASIC,
    'functional': BASIC + ['vdot-exceptions', 'vdot-overlap', 'vdot-deps', 'vdot-mixed',
                          'vdot-cancel-csr', 'vdot-port-contend-v1', 'vdot-rvv-equiv-v1'],
    'performance': ['vdot-timing-pilot-v1', 'vdot-chain-v1', 'vdot-throughput-v1',
                    'vdot-e2e-v1', 'vdot-segment-v1', 'vdot-load-v1', 'vdot-tile-v1'],
}


def verify(suite, directory):
    rows, common, errors = [], None, []
    for case in SUITES[suite]:
        folder = directory / case
        try:
            record = json.loads((folder / 'run-result.json').read_text(encoding='utf8'))
            raw = (folder / 'run.log').read_bytes()
            identities = record['identities']
            checks, passed = assess(raw.decode(errors='replace'), record['exit_code'],
                                    MARKERS[case], identities['reference']['path'])
            identity = {key: identities[key]['sha256'] for key in ['emu', 'reference', 'flash']}
            if common is None: common = identity
            valid = (passed and record.get('passed') is True and record['case'] == case
                     and record['seed'] == 1 and identity == common
                     and hashlib.sha256(raw).hexdigest() == record.get('log_sha256')
                     and (folder / 'exit-code.txt').read_text().strip() == '0')
            if not valid: errors.append(case)
            rows.append(dict(case=case, passed=valid, checks=checks,
                             image_sha256=identities['image']['sha256'], log=case + '/run.log'))
        except (OSError, ValueError, KeyError, TypeError) as error:
            errors.append(case)
            rows.append(dict(case=case, passed=False, error=str(error)))
    return dict(suite=suite, expected=len(SUITES[suite]), passed=sum(row['passed'] for row in rows),
                passed_all=not errors, common_identities=common, results=rows, failed_cases=errors,
                scope='Raw application markers, DiffTest, trap and exit checks; performance values remain in each raw log.')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--list', choices=SUITES)
    ap.add_argument('--suite', choices=SUITES)
    ap.add_argument('--directory', type=Path)
    args = ap.parse_args()
    if args.list:
        print('\n'.join(SUITES[args.list])); return 0
    if not args.suite or not args.directory: ap.error('Provide --suite and --directory.')
    if not args.directory.is_dir(): ap.error('Suite directory does not exist.')
    result = verify(args.suite, args.directory)
    output = args.directory / 'acceptance.json'
    output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
    print('ACCEPTANCE_FILE=' + str(output.resolve()))
    print('SUITE_%s %s %d/%d' % ('PASS' if result['passed_all'] else 'FAIL', args.suite,
                                 result['passed'], result['expected']))
    return 0 if result['passed_all'] else 1


if __name__ == '__main__': raise SystemExit(main())
