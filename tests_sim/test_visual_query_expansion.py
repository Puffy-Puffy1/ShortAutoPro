#!/usr/bin/env python3
import os
import unittest


class VisualQueryExpansionTests(unittest.TestCase):
    def test_expansion_is_rescue_only_when_primary_has_candidates(self):
        from visual_query_expansion_v4 import wrap_search_function

        calls = []

        def search(query, must_have=None):
            calls.append(query)
            return [{"id": "primary"}]

        old = os.environ.get("SAP_VSE4_QUERY_ONLY_ON_EMPTY")
        os.environ["SAP_VSE4_QUERY_ONLY_ON_EMPTY"] = "1"
        try:
            wrapped = wrap_search_function(search)
            result = wrapped(
                "abandoned merchant ship",
                ["ship", "ocean"],
            )
        finally:
            if old is None:
                os.environ.pop("SAP_VSE4_QUERY_ONLY_ON_EMPTY", None)
            else:
                os.environ["SAP_VSE4_QUERY_ONLY_ON_EMPTY"] = old

        self.assertEqual(len(result), 1)
        self.assertEqual(calls, ["abandoned merchant ship"])

    def test_document_scenes_get_bounded_legal_filing_searches(self):
        from media_engine_v2 import _targeted_visual_search_queries

        queries = _targeted_visual_search_queries(
            "legal documents and pen on table",
            ["document"],
            avoid=["children"],
            scene_context="parents filed a separate lawsuit",
        )

        self.assertIn("court filing legal paperwork on desk", queries)
        self.assertIn("legal case file document close up", queries)
        self.assertLessEqual(len(queries), 3)

    def test_document_scenes_get_legal_searches_only_with_legal_narration(self):
        from media_engine_v2 import _targeted_visual_search_queries

        queries = _targeted_visual_search_queries(
            "legal documents and pen on table",
            ["document"],
            avoid=["children"],
            scene_context="Scene: parents filed a separate lawsuit",
        )

        self.assertEqual(
            queries,
            [
                "court filing legal paperwork on desk",
                "legal case file document close up",
                "archival court record documents on table",
            ],
        )

    def test_medical_document_scene_does_not_get_legal_searches(self):
        from media_engine_v2 import _targeted_visual_search_queries

        queries = _targeted_visual_search_queries(
            "medical examination paperwork medical record close up",
            ["document"],
            scene_context="Scene: a doctor reviews a medical examination report",
        )

        self.assertFalse(any("court filing" in query for query in queries))
        self.assertFalse(any("legal case file" in query for query in queries))

    def test_empty_ship_deck_search_respects_no_crowd_context(self):
        from media_engine_v2 import _targeted_visual_search_queries

        queries = _targeted_visual_search_queries(
            "empty deck of vintage wooden ship",
            ["deck"],
            avoid=["crowd"],
            scene_context=(
                "Scene: the abandoned vessel deck\n"
                "ASSUNTO: The disappearance of the Mary Celeste crew"
            ),
        )

        self.assertIn(
            "The disappearance of the Mary Celeste crew empty wooden sailing ship deck with no crowd",
            queries,
        )
        self.assertLessEqual(len(queries), 3)

    def test_historical_newspaper_with_color_avoid_prioritizes_monochrome_search(self):
        from media_engine_v2 import _targeted_visual_search_queries

        queries = _targeted_visual_search_queries(
            "vintage tragedy newspaper archive document photo",
            ["document"],
            avoid=["color", "modern"],
            scene_context=(
                "Scene: the Dyatlov Pass incident began in 1959\n"
                "ASSUNTO: O caso das mortes no Passo Dyatlov"
            ),
        )

        self.assertEqual(
            queries,
            [
                "O caso das mortes no Passo Dyatlov Dyatlov Pass incident 1959 black and white newspaper clipping archive",
                "monochrome Soviet newspaper archive 1959 scanned black and white page",
                "black and white historical newspaper clipping archival photograph",
            ],
        )
        self.assertLessEqual(len(queries), 3)

    def test_historical_investigation_document_search_is_topic_specific(self):
        from media_engine_v2 import _targeted_visual_search_queries

        queries = _targeted_visual_search_queries(
            "vintage soviet investigative archive documents on wooden table",
            ["document"],
            avoid=["digital computer screen"],
            scene_context=(
                "Scene: A ausência de testemunhas e as investigações subsequentes\n"
                "ASSUNTO: O caso das mortes no Passo Dyatlov"
            ),
        )

        self.assertEqual(
            queries,
            [
                "Dyatlov Pass incident archival investigation records documents",
                "1959 Soviet investigation archive case files handwritten documents",
                "historical investigative records paper files from Soviet archive",
            ],
        )

    def test_historical_investigation_search_does_not_apply_to_medical_documents(self):
        from media_engine_v2 import _targeted_visual_search_queries

        queries = _targeted_visual_search_queries(
            "medical examination paperwork medical record close up",
            ["document"],
            avoid=["digital computer screen"],
            scene_context="Scene: a doctor reviews a medical examination report",
        )

        self.assertFalse(any("Dyatlov" in query for query in queries))
        self.assertFalse(any("Soviet investigation archive" in query for query in queries))

    def test_empty_primary_uses_must_first_rescue(self):
        from visual_query_expansion_v4 import wrap_search_function

        calls = []

        def search(query, must_have=None):
            calls.append(query)
            if "vessel" in query.casefold():
                return [{"id": "rescued"}]
            return []

        old_expansion = os.environ.get("SAP_VSE4_QUERY_EXPANSION")
        old_extra = os.environ.get("SAP_VSE4_QUERY_EXTRA")
        old_only = os.environ.get("SAP_VSE4_QUERY_ONLY_ON_EMPTY")
        os.environ["SAP_VSE4_QUERY_EXPANSION"] = "1"
        os.environ["SAP_VSE4_QUERY_EXTRA"] = "1"
        os.environ["SAP_VSE4_QUERY_ONLY_ON_EMPTY"] = "1"
        try:
            wrapped = wrap_search_function(search)
            result = wrapped(
                "abandoned vintage merchant ship drifting at sea",
                ["ship", "ocean"],
            )
        finally:
            for name, value in (
                ("SAP_VSE4_QUERY_EXPANSION", old_expansion),
                ("SAP_VSE4_QUERY_EXTRA", old_extra),
                ("SAP_VSE4_QUERY_ONLY_ON_EMPTY", old_only),
            ):
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value

        self.assertEqual(result, [{"id": "rescued"}])
        self.assertEqual(calls[0], "abandoned vintage merchant ship drifting at sea")
        self.assertEqual(len(calls), 2)
        self.assertIn("ship", calls[1].casefold())
        self.assertIn("ocean", calls[1].casefold())
        self.assertIn("vessel", calls[1].casefold())


if __name__ == "__main__":
    unittest.main()
