import unittest
from generative_video_poc.contracts import ProjectSpec

class ProjectContractTests(unittest.TestCase):
    def test_shorts_and_longform_share_one_planner(self):
        short = ProjectSpec.from_dict({"kind":"shorts","target_duration_seconds":60,"aspect_ratio":"9:16","width":1080,"height":1920,"clip_seconds":10})
        long = ProjectSpec.from_dict({"kind":"longform","target_duration_seconds":1800,"aspect_ratio":"16:9","width":1920,"height":1080,"clip_seconds":10})
        self.assertEqual(len(short.clip_schedule()), 6)
        self.assertEqual(len(long.clip_schedule()), 180)
        self.assertEqual(sum(c.duration_seconds for c in long.clip_schedule()), 1800)
        self.assertEqual(long.summary()["generation_status"], "NOT_STARTED")

    def test_last_clip_is_trimmed_to_exact_duration(self):
        spec = ProjectSpec.from_dict({"kind":"shorts","target_duration_seconds":63,"aspect_ratio":"9:16","width":1080,"height":1920,"clip_seconds":10})
        self.assertEqual([c.duration_seconds for c in spec.clip_schedule()], [10,10,10,10,10,10,3])

    def test_rejects_orientation_mismatch(self):
        with self.assertRaisesRegex(ValueError, "portrait"):
            ProjectSpec.from_dict({"kind":"shorts","target_duration_seconds":30,"aspect_ratio":"9:16","width":1920,"height":1080})

    def test_accepts_short_landscape_chapter_projects(self):
        chapter = ProjectSpec.from_dict({
            "kind": "longform", "target_duration_seconds": 120,
            "aspect_ratio": "16:9", "width": 1280, "height": 720,
            "clip_seconds": 10,
        })
        self.assertEqual(len(chapter.clip_schedule()), 12)

    def test_rejects_invalid_kind_prompt_count_and_duration_over_two_hours(self):
        with self.assertRaises(ValueError):
            ProjectSpec.from_dict({"kind":"other"})
        with self.assertRaisesRegex(ValueError, "exactly 2"):
            ProjectSpec.from_dict({
                "kind": "shorts", "target_duration_seconds": 20,
                "aspect_ratio": "9:16", "width": 360, "height": 640,
                "clip_seconds": 10, "clip_prompts": ["only one prompt"],
            })
        with self.assertRaisesRegex(ValueError, "120 minutes"):
            ProjectSpec.from_dict({
                "kind": "longform", "target_duration_seconds": 7201,
                "aspect_ratio": "16:9", "width": 1280, "height": 720,
            })

if __name__ == "__main__":
    unittest.main()
