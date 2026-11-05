"""Recording output and delivery enumeration regression checks."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import recording_case
import verify_bundle

class RecordingAndManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='vdot-entry-')
        self.root=Path(self.tmp.name).resolve()
        assert self.root.is_relative_to(Path(tempfile.gettempdir()).resolve())
        self.addCleanup(self.tmp.cleanup)

    def write(self,path,text='x'):
        p=self.root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf8');return p

    def result(self,passed=True,code=0):
        self.write('run-result.json',json.dumps(dict(case='vdot-smoke',passed=passed,exit_code=code)))
        self.write('recording-launch.json',json.dumps(dict(runner_exit_code=code)))
        self.write('run.log','Difftest enabled.\n'+''.join('PASS vdot case=%d full128=OK\n'%i for i in range(7))+'PASS VDOT_SMOKE cases=7\n\x1b[34mHIT GOOD TRAP\n')

    def test_cache_pruning_preserves_sources_and_editor_config(self):
        keep=['src/XiangShan/build.sc','src/XiangShan/src/main/scala/out/Real.scala','.vscode/settings.json','docs/new.md','configs/source-tree.json']
        excluded=['.metals/metals.log','.scala-build/generated.scala','src/XiangShan/.bloop/x.json','src/XiangShan/.bsp/x.json','src/XiangShan/out/generated.scala','src/XiangShan/.metals/x.db','apps/vdot-smoke/build/app.bin','tools/__pycache__/x.pyc','work/x','runs/x','recording/outputs/x']
        for name in keep+excluded:self.write(name)
        with patch.object(verify_bundle,'ROOT',self.root):
            found={p.relative_to(self.root).as_posix() for p in verify_bundle.bundle_files()}
        self.assertEqual(found,set(keep))

    def test_lfs_videos_separate_from_build_payload_but_indexes_preserved(self):
        keep=['videos/README.md','docs/README.md','docs/unexpected.mp4']
        excluded=['videos/stage1.mp4','videos/stage2.MP4','videos/subdir/stage3.mkv']
        for name in keep+excluded:self.write(name)
        with patch.object(verify_bundle,'ROOT',self.root):
            found={p.relative_to(self.root).as_posix() for p in verify_bundle.bundle_files()}
        self.assertEqual(found,set(keep))

    def test_new_source_is_not_hidden(self):
        self.write('src/XiangShan/src/main/scala/New.scala')
        with patch.object(verify_bundle,'ROOT',self.root):self.assertEqual(len(verify_bundle.bundle_files()),1)

    def test_smoke_result_shows_all_cases_without_color_leak(self):
        self.result();output=io.StringIO()
        with contextlib.redirect_stdout(output):rc=recording_case.display_result(self.root,'vdot-smoke')
        self.assertEqual(rc,0);text=output.getvalue()
        self.assertEqual(text.count('PASS vdot case='),7)
        self.assertIn('PASS VDOT_SMOKE cases=7',text);self.assertIn('RUN_CHECK=PASS',text)
        self.assertNotIn('\x1b',text)

    def test_result_rejects_other_case(self):
        self.result()
        with self.assertRaises(ValueError):recording_case.display_result(self.root,'vadd4')

    def test_nonzero_exit_cannot_display_pass(self):
        self.result(passed=True,code=1);output=io.StringIO()
        with contextlib.redirect_stdout(output):rc=recording_case.display_result(self.root,'vdot-smoke')
        self.assertEqual(rc,1);self.assertIn('RUN_CHECK=FAIL',output.getvalue())

if __name__=='__main__':unittest.main()
