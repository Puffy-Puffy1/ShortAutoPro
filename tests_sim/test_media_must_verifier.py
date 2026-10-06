import unittest

from media_must_verifier import requirement_matches


class MediaMustVerifierSecuritySensorTests(unittest.TestCase):
    def test_security_sensor_accepts_verified_visual_equivalents(self):
        for evidence in (
            "close-up of a motion sensor on a security door",
            "alarm sensor installed on a building entrance",
            "door sensor security alarm hardware",
        ):
            self.assertTrue(
                requirement_matches("security sensor", {"description": evidence}),
                evidence,
            )

    def test_security_sensor_does_not_accept_generic_security_camera(self):
        self.assertFalse(
            requirement_matches(
                "security sensor",
                {"description": "security camera monitoring a building"},
            )
        )


if __name__ == "__main__":
    unittest.main()
