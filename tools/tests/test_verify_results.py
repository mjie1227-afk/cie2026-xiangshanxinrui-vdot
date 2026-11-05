"""Suite acceptance must reject incomplete, altered or mixed-binary evidence."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from verify_results import SUITES, MARKERS, verify


class AcceptanceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        assert self.root.is_relative_to(Path(tempfile.gettempdir()).resolve())
        self.addCleanup(self.tmp.cleanup)
        for case in SUITES['smoke']:
            folder = self.root / case; folder.mkdir()
            text = 'Difftest enabled.\nThe reference model is /tmp/reference.so\n' + MARKERS[case] + '\nHIT GOOD TRAP\n'
            raw = text.encode()
            (folder / 'run.log').write_bytes(raw)
            (folder / 'exit-code.txt').write_text('0\n')
            identities = {key: {'sha256': hashlib.sha256(key.encode()).hexdigest(),
                                'path': '/tmp/reference.so' if key == 'reference' else '/tmp/' + key}
                          for key in ['emu', 'reference', 'flash', 'image']}
            record = dict(case=case, seed=1, exit_code=0, passed=True, identities=identities,
                          log_sha256=hashlib.sha256(raw).hexdigest())
            (folder / 'run-result.json').write_text(json.dumps(record))

    def test_complete_suite(self):
        self.assertTrue(verify('smoke', self.root)['passed_all'])

    def test_missing_case_rejected(self):
        (self.root / 'vadd4/run-result.json').unlink()
        self.assertFalse(verify('smoke', self.root)['passed_all'])

    def test_modified_log_rejected(self):
        with (self.root / 'vadd4/run.log').open('a') as f: f.write('modified\n')
        self.assertFalse(verify('smoke', self.root)['passed_all'])

    def test_mixed_reference_rejected(self):
        p = self.root / 'vadd4/run-result.json'; r = json.loads(p.read_text())
        r['identities']['reference']['sha256'] = 'different-library'
        p.write_text(json.dumps(r))
        self.assertFalse(verify('smoke', self.root)['passed_all'])

    def test_stored_pass_does_not_override_raw_failure(self):
        p = self.root / 'vadd4/run.log'; p.write_text(p.read_text().replace('HIT GOOD TRAP', 'HIT BAD TRAP'))
        j = self.root / 'vadd4/run-result.json'; r = json.loads(j.read_text())
        r['log_sha256'] = hashlib.sha256(p.read_bytes()).hexdigest(); j.write_text(json.dumps(r))
        self.assertFalse(verify('smoke', self.root)['passed_all'])


if __name__ == '__main__': unittest.main()
