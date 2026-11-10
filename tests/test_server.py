import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from reelkit.server import make_server


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.server=make_server(local=self.tmp.name)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.base=f'http://127.0.0.1:{self.server.server_port}'
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.tmp.cleanup()
    def test_missing_session_cannot_upload(self):
        req=urllib.request.Request(self.base+'/api/upload',data=b'private',headers={'X-Filename':'input.mp4'})
        with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(req)
        self.assertEqual(e.exception.code,403)
    def test_uploaded_name_cannot_escape(self):
        req=urllib.request.Request(self.base+'/api/upload',data=b'not a video',headers={'X-Filename':'../../elsewhere.mp4','X-Reel-Token':self.server.session_token})
        with urllib.request.urlopen(req) as f:answer=json.load(f)
        self.assertTrue(answer['path'].startswith('uploads/'))
        self.assertNotIn('..',answer['path'])
    def test_browser_video_ranges(self):
        p=Path(self.tmp.name)/'uploads/x.mp4';p.write_bytes(b'0123456789')
        req=urllib.request.Request(self.base+'/files/uploads/x.mp4?token='+self.server.session_token,headers={'Range':'bytes=2-5'})
        with urllib.request.urlopen(req) as f:
            self.assertEqual(f.status,206);self.assertEqual(f.read(),b'2345')
    def test_untrusted_origin_cannot_read(self):
        req=urllib.request.Request(self.base+'/api/templates',headers={'Origin':'https://unrelated.example'})
        with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(req)
        self.assertEqual(e.exception.code,403)
    def test_static_routes_cannot_escape_their_directory(self):
        req=urllib.request.Request(self.base+'/assets/%2e%2e/README.md')
        with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(req)
        self.assertEqual(e.exception.code,404)


if __name__=='__main__':unittest.main()
