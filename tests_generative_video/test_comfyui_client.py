import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlparse
from generative_video_poc.comfyui_client import ComfyUIClient, ComfyUIError

FIXTURE = b"POC-VIDEO-FIXTURE-NOT-A-REAL-MP4"
class Handler(BaseHTTPRequestHandler):
    no_output = False
    seen = []
    def log_message(self, *_args): pass
    def send_body(self, status, body, content_type="application/json"):
        self.send_response(status); self.send_header("Content-Type", content_type); self.end_headers(); self.wfile.write(body)
    def do_POST(self):
        size = int(self.headers.get("Content-Length","0")); payload = json.loads(self.rfile.read(size))
        self.__class__.seen.append((self.path,payload))
        self.send_body(200,json.dumps({"prompt_id":"poc-123"}).encode())
    def do_GET(self):
        path = urlparse(self.path).path; self.__class__.seen.append((path,{}))
        if path == "/history/poc-123":
            outputs = {} if self.__class__.no_output else {"9":{"videos":[{"filename":"clip.mp4","subfolder":"","type":"output"}]}}
            item = {"status":{"completed":True,"status_str":"success"},"outputs":outputs}
            self.send_body(200,json.dumps({"poc-123":item}).encode())
        elif path == "/view": self.send_body(200,FIXTURE,"video/mp4")
        else: self.send_body(404,b"not found","text/plain")

class ComfyClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1",0),Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever,daemon=True); cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(timeout=2)
    def setUp(self):
        Handler.seen=[]; Handler.no_output=False
        self.client=ComfyUIClient(self.url,request_timeout=2,job_timeout=1,poll_interval=.01)
    def test_submit_poll_download_with_local_fake_server(self):
        workflow={"1":{"class_type":"TestNode","inputs":{}}}
        with TemporaryDirectory() as temp:
            files=self.client.generate(workflow,Path(temp))
            self.assertEqual(len(files),1); self.assertEqual(files[0].name,"clip.mp4")
            self.assertEqual(files[0].read_bytes(),FIXTURE)
        self.assertEqual(Handler.seen[0][0],"/prompt")
        self.assertEqual(Handler.seen[0][1]["prompt"],workflow)
        self.assertIn("/history/poc-123",[item[0] for item in Handler.seen])
    def test_completed_job_without_video_fails_closed(self):
        Handler.no_output=True
        with self.assertRaisesRegex(ComfyUIError,"without video output"):
            self.client.generate({"1":{"class_type":"TestNode","inputs":{}}},Path("unused"))
    def test_rejects_invalid_server_and_empty_workflow(self):
        with self.assertRaises(ValueError): ComfyUIClient("file:///tmp/comfy")
        with self.assertRaises(ValueError): self.client.submit({})

if __name__ == "__main__": unittest.main()
