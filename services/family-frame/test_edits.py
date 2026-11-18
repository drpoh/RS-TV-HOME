"""Isolated tests: no real photo paths, USB or credentials."""
import importlib.util
import json
import secrets
import tempfile
import threading
import unittest
from unittest import mock
from types import SimpleNamespace
import urllib.request
import urllib.error
from pathlib import Path

class Edits(unittest.TestCase):
    def test_faststart_cache(self):
        import subprocess
        spec=importlib.util.spec_from_file_location("frame_cache",Path(__file__).with_name("server.py"))
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);m.USB=root/"usb";m.USB.mkdir();m.ALBUM=root/"album";m.ALBUM.mkdir()
            m.CACHE=root/"cache";m.CACHE.mkdir()
            m.VIDEO_CACHE=m.CACHE/"video"
            src=m.USB/"sample.mp4"
            subprocess.run(["ffmpeg","-nostdin","-loglevel","error","-f","lavfi","-i",
                "testsrc=size=128x72:rate=10","-t","1","-pix_fmt","yuv420p",
                "-c:v","mpeg4","-y",str(src)],check=True,timeout=12)
            original=src.read_bytes()
            self.assertNotIn(b"moov",original[:100])
            with mock.patch.object(m.shutil,"disk_usage",return_value=SimpleNamespace(free=10*1024**3)):
                cached=m.prepare_video(src)
            self.assertTrue(m.video_cache_ready(cached))
            self.assertEqual(src.read_bytes(),original)
            self.assertNotEqual(src,cached)
            self.assertEqual(m.queue_video(src),cached)
            self.assertEqual(m.prepare_video(src),cached)
            self.assertEqual(cached.stat().st_mode & 0o777,0o600)
            self.assertEqual(m.VIDEO_CACHE.stat().st_mode & 0o777,0o700)

    def test_album_edits(self):
        spec=importlib.util.spec_from_file_location("frame",Path(__file__).with_name("server.py"))
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            m.ALBUM=root/"album";m.ALBUM.mkdir()
            m.USB=root/"usb";m.USB.mkdir()
            m.STATE=root/"state"/"frame-state.json"
            m.CACHE=root/"cache"
            m.TV=m.HOST="127.0.0.1"
            m.EDIT_KEY=secrets.token_hex(32)
            photo=m.ALBUM/"example.jpg";photo.write_bytes(b"test-image")
            video=m.USB/"example.mp4";video.write_bytes(b"test-video")
            link=m.ALBUM/"link.jpg";link.symlink_to(photo)
            http=m.ThreadingHTTPServer(("127.0.0.1",0),m.Handler)
            thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
            url="http://127.0.0.1:"+str(http.server_port)
            def get():
                with urllib.request.urlopen(url+"/api/album",timeout=4) as r:return json.load(r)
            def post(body,authenticated=True):
                body=dict(body,key=m.EDIT_KEY if authenticated else "")
                req=urllib.request.Request(url+"/api/edit",data=json.dumps(body).encode(),headers={"Content-Type":"text/plain"})
                try:
                    with urllib.request.urlopen(req,timeout=4) as r:return r.status
                except urllib.error.HTTPError as e:return e.code
            try:
                album=get();self.assertEqual(len(album["items"]),2)
                by_type={a["type"]:a["id"] for a in album["items"]}
                for typ,key in by_type.items():
                    self.assertEqual(post({"op":"rotate","id":key,"rotation":90},False),403)
                    self.assertEqual(post({"op":"rotate","id":key,"rotation":45}),400)
                    self.assertEqual(post({"op":"rotate","id":key,"rotation":90}),200)
                    self.assertEqual(next(a for a in get()["items"] if a["id"]==key)["rotation"],90)
                    self.assertEqual(post({"op":"hide","id":key}),200)
                    self.assertNotIn(key,[a["id"] for a in get()["items"]])
                    self.assertEqual(post({"op":"restore"}),200)
                    self.assertIn(key,[a["id"] for a in get()["items"]])
                self.assertEqual(photo.read_bytes(),b"test-image")
                self.assertEqual(video.read_bytes(),b"test-video")
                self.assertEqual(m.STATE.stat().st_mode&0o777,0o600)
                req=urllib.request.Request(url+"/video/"+by_type["video"],headers={"Range":"bytes=0-3"})
                with urllib.request.urlopen(req,timeout=4) as r:
                    self.assertEqual(r.status,206);self.assertEqual(r.read(),b"test")
            finally:http.shutdown();http.server_close();thread.join(timeout=3)

if __name__=="__main__":unittest.main()
