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
            with patch.object(media_engine_v2.PROVIDER, "search", return_value=[candidate]),                  patch.object(media_engine_v2.PROVIDER, "prepare", return_value=[candidate]),                  patch.object(media_engine_v2.PROVIDER, "download", return_value=(False, str(media/"scene_01.jpg"), {"error_class":"DOWNLOAD_FAILED"})),                  patch.object(media_engine_v2, "_local_library_asset", return_value=None):
                with self.assertRaisesRegex(RuntimeError, "MEDIA_DOWNLOAD_FAILED"):
                    media_engine_v2.acquire_scene("X",1,{"query":"ship","must_have":["ship"]},media)

    def test_local_library_is_only_fallback_after_provider_failure(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            media = base/"imagens"/"short_X"
            media.mkdir(parents=True)
            asset = media/"scene_01.jpg"
            asset.write_bytes(b"valid-local-asset")
            with patch.object(media_engine_v2.PROVIDER, "search", return_value=[]), \
                 patch.object(media_engine_v2, "_local_library_asset", return_value={
                     "source":"LocalLibrary","asset_id":"sha256:test",
                     "path":str(asset),"checksum_sha256":"expected","validated":True
                 }) as local:
                result = media_engine_v2.acquire_scene(
                    "X", 1, {"query":"ship","must_have":["ship"]}, media
                )
                local.assert_called_once()
                self.assertEqual(result["source"], "LocalLibrary")

if __name__=="__main__": unittest.main()
