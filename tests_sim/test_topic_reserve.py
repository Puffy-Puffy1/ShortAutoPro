import json
import math
import os
import tempfile
import unittest
from unittest.mock import patch

import topic_reserve


class TopicReserveTests(unittest.TestCase):
    def test_score_seguro_rejects_non_finite_and_invalid_values(self):
        self.assertEqual(topic_reserve.score_seguro(None), 0.0)
        self.assertEqual(topic_reserve.score_seguro("abc"), 0.0)
        self.assertEqual(topic_reserve.score_seguro(float("nan")), 0.0)
        self.assertEqual(topic_reserve.score_seguro(float("inf")), 0.0)
        self.assertEqual(topic_reserve.score_seguro("12.5"), 12.5)

    def test_index_candidates_are_sorted_and_history_duplicates_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            index_path = os.path.join(tmp, "topic_index.json")
            history_path = os.path.join(tmp, "historico_assuntos.json")
            with open(history_path, "w", encoding="utf-8") as f:
                json.dump([{"topic": "Mary Celeste"}], f)
            with open(index_path, "w", encoding="utf-8") as f:
                json.dump({
                    "topics": [
                        {"topic": "Mary Celeste", "wiki_title": "Mary Celeste", "score": 99},
                        {"topic": "Alpha Mystery", "wiki_title": "Alpha Mystery", "score": 5},
                        {"topic": "Beta Mystery", "wiki_title": "Beta Mystery", "score": 20},
                    ]
                }, f)

            with patch.object(topic_reserve, "INDEX", index_path), patch.object(topic_reserve, "HISTORICO", history_path):
                result = topic_reserve.carregar_do_indice()

            self.assertEqual([x["topic"] for x in result], ["Beta Mystery", "Alpha Mystery"])
            self.assertTrue(all(x["source"] == "topic_index" for x in result))

    def test_corrupt_history_blocks_reserve_instead_of_reusing_topics(self):
        with tempfile.TemporaryDirectory() as tmp:
            index_path = os.path.join(tmp, "topic_index.json")
            history_path = os.path.join(tmp, "historico_assuntos.json")
            with open(history_path, "w", encoding="utf-8") as f:
                f.write("{invalid json")
            with open(index_path, "w", encoding="utf-8") as f:
                json.dump({"topics": [{"topic": "Alpha", "wiki_title": "Alpha", "score": 10}]}, f)

            with patch.object(topic_reserve, "INDEX", index_path), patch.object(topic_reserve, "HISTORICO", history_path):
                result = topic_reserve.carregar_do_indice()

            self.assertEqual(result, [])

    def test_verified_fallback_keeps_best_score_for_same_topic(self):
        with tempfile.TemporaryDirectory() as tmp:
            roteiros = os.path.join(tmp, "roteiros")
            os.makedirs(roteiros)
            history_path = os.path.join(tmp, "historico_assuntos.json")
            with open(history_path, "w", encoding="utf-8") as f:
                json.dump([], f)

            for filename, score in (("topic_verified_a.json", 3), ("topic_verified_b.json", 9)):
                with open(os.path.join(roteiros, filename), "w", encoding="utf-8") as f:
                    json.dump({"ranking": [{"topic": "Gamma Case", "wiki_title": "Gamma Case", "score": score}]}, f)

            with patch.object(topic_reserve, "ROTEIROS", roteiros), patch.object(topic_reserve, "HISTORICO", history_path):
                result = topic_reserve.carregar_dos_verified()

            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["topic"], "Gamma Case")
            self.assertEqual(result[0]["score"], 9.0)

    def test_melhor_reserva_returns_none_when_empty(self):
        with patch.object(topic_reserve, "carregar_reserva", return_value=[]):
            self.assertIsNone(topic_reserve.melhor_reserva())


if __name__ == "__main__":
    unittest.main()
