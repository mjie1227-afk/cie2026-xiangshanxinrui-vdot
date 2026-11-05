import hashlib,json,sys,tempfile,unittest
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from verify_videos import verify

class VideoChecks(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.directory=self.root/'videos';self.directory.mkdir()
        self.content=b'recorded-media-fixture'
        self.video=self.directory/'stage1.mp4';self.video.write_bytes(self.content)
        (self.directory/'manifest.json').write_text(json.dumps({'videos':[{'filename':'stage1.mp4','bytes':len(self.content),'sha256':hashlib.sha256(self.content).hexdigest()}]}),encoding='utf8')
    def test_downloaded_body_matches(self):self.assertTrue(verify(self.root)[0]['ok'])
    def test_pointer_is_not_accepted_as_video(self):
        self.video.write_text('version https://git-lfs.github.com/spec/v1\noid sha256:abc\nsize 100\n')
        self.assertIn('LFS pointer',verify(self.root)[0]['error'])
    def test_same_size_corruption_is_rejected(self):
        self.video.write_bytes(b'x'*len(self.content));self.assertIn('SHA256',verify(self.root)[0]['error'])
    def test_missing_body_is_rejected(self):
        self.video.unlink();self.assertIn('git lfs pull',verify(self.root)[0]['error'])
if __name__=='__main__':unittest.main()
