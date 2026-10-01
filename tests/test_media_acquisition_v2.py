import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from media_provider_router_v2 import MediaProviderRouterV2
from media_validator_v2 import validate

class FakeProvider:
    def __init__(self,name,candidates): self.name=name; self.candidates=candidates
    def search(self,query,must,avoid): return list(self.candidates)

class AcquisitionV2Tests(unittest.TestCase):
    def test_router_falls_back_per_asset(self):
        a={"fonte":"pexels","tipo":"video","id":"a","url":"https://invalid/a.mp4","must_hits":1,"avoid_hits":0,"score":90}
        b={"fonte":"pixabay","tipo":"video","id":"b","url":"https://invalid/b.mp4","must_hits":1,"avoid_hits":0,"score":80}
        router=MediaProviderRouterV2([FakeProvider("pexels",[a]),FakeProvider("pixabay",[b])])
        self.assertEqual([x["id"] for x in router.search("x",["x"],[])],["a","b"])

    def test_validator_rejects_html_jpg(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"bad.jpg"
            p.write_bytes(b"<html>" + b"x"*2000)
            with self.assertRaises(ValueError):
                validate(p)

    def test_validator_rejects_empty_media(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"bad.mp4"; p.write_bytes(b"")
            with self.assertRaises(ValueError):
                validate(p)

    def test_provider_module_does_not_import_legacy(self):
        import media_provider_v2
        self.assertNotIn("midia", getattr(media_provider_v2,"__dict__",{}))

if __name__ == "__main__":
    unittest.main()
