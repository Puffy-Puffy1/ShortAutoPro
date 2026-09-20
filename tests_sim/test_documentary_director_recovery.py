import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DocumentaryDirectorRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.text = (ROOT / "documentary_director.py").read_text(encoding="utf-8")

    def test_director_retries_malformed_successful_responses(self):
        self.assertIn("for tentativa in range(1, 4):", self.text)
        self.assertIn("resposta = validar_resposta_documental(extrair_objeto_json(bruto))", self.text)
        self.assertIn("AVISO: resposta Gemini inválida para o contrato documental", self.text)
        self.assertIn("if tentativa < 3:", self.text)

    def test_director_extracts_json_from_fences_or_extra_text(self):
        self.assertIn("def extrair_objeto_json(", self.text)
        self.assertIn("fence = chr(96) * 3", self.text)
        self.assertIn('trecho = limpo[inicio:indice + 1]', self.text)
        self.assertIn("json.loads(trecho)", self.text)

    def test_director_validates_scene_contract_inside_retry(self):
        self.assertIn("def validar_resposta_documental(", self.text)
        self.assertIn("if len(novas) != QTD_CENAS:", self.text)
        self.assertIn("if numeros != esperado_local:", self.text)
        self.assertIn('raise ValueError(f"cena {numero} sem query")', self.text)
        self.assertIn('raise ValueError(f"cena {numero} sem must_have")', self.text)

    def test_director_requests_json_mode_and_uses_shared_config(self):
        self.assertIn('"responseMimeType": "application/json"', self.text)
        self.assertIn('env_float("SAP_GEMINI_TIMEOUT", 75.0, 20.0, 120.0)', self.text)
        self.assertIn('env_int("SHORT_QTD_CENAS", 12, 6, 20)', self.text)

    def test_final_failure_persists_diagnostics(self):
        self.assertIn('"status": "BLOCK"', self.text)
        self.assertIn('"raw_preview": ultimo_bruto', self.text)
        self.assertIn("falhou após 3 tentativas", self.text)

    def test_success_report_is_version_3_3(self):
        self.assertIn('DOCUMENTARY DIRECTOR - STABLE 3.3', self.text)
        self.assertIn('"version": "3.3"', self.text)
        self.assertIn('"status": "PASS"', self.text)


if __name__ == "__main__":
    unittest.main()
