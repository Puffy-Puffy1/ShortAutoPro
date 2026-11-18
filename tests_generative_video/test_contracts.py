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

    def test_rejects_invalid_kind_and_short_longform(self):
        with self.assertRaises(ValueError):
            ProjectSpec.from_dict({"kind":"other"})
        with self.assertRaisesRegex(ValueError, "exceed 180"):
            ProjectSpec.from_dict({"kind":"longform","target_duration_seconds":180,"aspect_ratio":"16:9","width":1920,"height":1080})

if __name__ == "__main__":
    unittest.main()
