"""Synthetic HTTP Range and security tests; does not contact a TV or user's media."""
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from http.server import ThreadingHTTPServer

from smartshare_rotation_probe import SourceHandler

class MediaRangeTests(unittest.TestCase):
    def test_media_is_limited_and_ranges_work(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "synthetic.mp4"
            source.write_bytes(b"abcdefghij")
            server = ThreadingHTTPServer(("127.0.0.1", 0), SourceHandler)
            server.routes = {"/sample.mp4": source}
            server.allowed = {"127.0.0.1"}
            server.requests = server.bytes = 0
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            root = f"http://127.0.0.1:{server.server_port}"
            try:
                request = urllib.request.Request(root + "/sample.mp4",
                                                 headers={"Range": "bytes=2-5"})
                with urllib.request.urlopen(request, timeout=3) as reply:
                    self.assertEqual(reply.status, 206)
                    self.assertEqual(reply.read(), b"cdef")
                    self.assertEqual(reply.headers["Content-Range"], "bytes 2-5/10")
                request = urllib.request.Request(root + "/sample.mp4", method="HEAD")
                with urllib.request.urlopen(request, timeout=3) as reply:
                    self.assertEqual(reply.status, 200)
                    self.assertEqual(reply.headers["Content-Length"], "10")
                    self.assertEqual(reply.read(), b"")
                for path in ("/nope", "/sample.mp4/../"):
                    with self.assertRaises(urllib.error.HTTPError) as error:
                        urllib.request.urlopen(root + path, timeout=3)
                    self.assertEqual(error.exception.code, 404)
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(
                        urllib.request.Request(root + "/sample.mp4",
                            headers={"Range": "bytes=999-1000"}), timeout=3)
                self.assertEqual(error.exception.code, 416)
                server.allowed = set()
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(root + "/sample.mp4", timeout=3)
                self.assertEqual(error.exception.code, 403)
                self.assertEqual(server.bytes, 4)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)

if __name__ == "__main__":
    unittest.main()
