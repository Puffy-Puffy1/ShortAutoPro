import tempfile
import unittest
from pathlib import Path


from motion_director import choose_profile, locate_media, normalize_shot


class ShotAwareMotionTests(unittest.TestCase):
    def test_normalizes_common_shot_aliases(self):
        self.assertEqual(normalize_shot("establishing_shot"), "wide")
        self.assertEqual(normalize_shot("close-up"), "closeup")
        self.assertEqual(normalize_shot("top down"), "overhead")
        self.assertEqual(normalize_shot("face"), "portrait")

    def test_video_keeps_native_motion(self):
        name, profile = choose_profile(1, "environment", "wide", "video")
        self.assertEqual(name, "native_video")
        self.assertEqual(profile["zoom_start"], 1.0)
        self.assertEqual(profile["zoom_end"], 1.0)
        self.assertEqual(profile["pan"], "none")

    def test_portrait_uses_subtle_motion(self):
        name, profile = choose_profile(4, "human_context", "portrait", "photo")
        self.assertEqual(name, "portrait_push")
        self.assertLessEqual(profile["zoom_end"], 1.04)
        self.assertLessEqual(profile["intensity"], 2)

    def test_document_detail_is_held_for_readability(self):
        name, profile = choose_profile(5, "evidence", "detail", "photo")
        self.assertEqual(name, "detail_hold")
        self.assertLessEqual(profile["zoom_end"], 1.03)
        self.assertEqual(profile["pan"], "center")

    def test_wide_shots_use_restrained_alternating_drift(self):
        odd_name, odd = choose_profile(3, "environment", "wide", "photo")
        even_name, even = choose_profile(4, "environment", "wide", "photo")
        self.assertEqual(odd_name, "wide_drift_right")
        self.assertEqual(even_name, "wide_drift_left")
        self.assertEqual(odd["pan"], "right")
        self.assertEqual(even["pan"], "left")
        self.assertLessEqual(odd["zoom_end"], 1.05)
        self.assertLessEqual(even["zoom_end"], 1.05)

    def test_hook_push_is_reserved_for_closeup_opening(self):
        close_name, _ = choose_profile(1, "object", "closeup", "photo")
        portrait_name, _ = choose_profile(1, "human_context", "portrait", "photo")
        wide_name, _ = choose_profile(1, "environment", "wide", "photo")
        self.assertEqual(close_name, "hook_push")
        self.assertNotEqual(portrait_name, "hook_push")
        self.assertNotEqual(wide_name, "hook_push")


    def test_locates_provider_suffixed_scene_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            media_dir = Path(tmp)
            asset = media_dir / "scene_01_wikimedia.jpg"
            asset.write_bytes(b"fixture")
            self.assertEqual(locate_media(media_dir, 1), asset)

    def test_locates_provider_suffixed_video_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            media_dir = Path(tmp)
            asset = media_dir / "scene_02_archive-video.webm"
            asset.write_bytes(b"fixture")
            self.assertEqual(locate_media(media_dir, 2), asset)

    def test_rejects_ambiguous_assets_for_same_scene(self):
        with tempfile.TemporaryDirectory() as tmp:
            media_dir = Path(tmp)
            (media_dir / "scene_01_wikimedia.jpg").write_bytes(b"one")
            (media_dir / "scene_01_pixabay.jpg").write_bytes(b"two")
            with self.assertRaisesRegex(ValueError, "mídia ambígua"):
                locate_media(media_dir, 1)


if __name__ == "__main__":
    unittest.main()
