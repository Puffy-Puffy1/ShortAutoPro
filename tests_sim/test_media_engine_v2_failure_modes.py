import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import media_engine_v2

class MediaEngineV2FailureTests(unittest.TestCase):
    def test_empty_provider_is_media_incomplete(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td); media=base/"imagens"/"short_X"; media.mkdir(parents=True)
            with patch.object(media_engine_v2.PROVIDER, "search", return_value=[]), patch.object(media_engine_v2, "_local_library_asset", return_value=None):
                with self.assertRaisesRegex(RuntimeError, "MEDIA_INCOMPLETE"):
                    media_engine_v2.acquire_scene("X", 1, {"query":"ship","must_have":["ship"]}, media)

    def test_download_failure_is_not_success(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td); media=base/"imagens"/"short_X"; media.mkdir(parents=True)
            candidate={"fonte":"Mock","id":"1","tipo":"imagem","must_hits":1}
            with patch.object(media_engine_v2.PROVIDER, "search", return_value=[candidate]),                  patch.object(media_engine_v2.PROVIDER, "prepare", return_value=[candidate]),                  patch.object(media_engine_v2.PROVIDER, "download", return_value=(False, str(media/"scene_01.jpg"))),                  patch.object(media_engine_v2, "_local_library_asset", return_value=None):
                with self.assertRaisesRegex(RuntimeError, "MEDIA_DOWNLOAD_FAILED"):
                    media_engine_v2.acquire_scene("X",1,{"query":"ship","must_have":["ship"]},media)

if __name__=="__main__": unittest.main()
