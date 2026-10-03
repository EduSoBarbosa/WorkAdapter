import unittest
from copy import deepcopy

from pydantic import ValidationError

from backend.agents.curriculo_evidencias import preparar_plano


class TestEvidenciasCurriculo(unittest.TestCase):
    def setUp(self):
        self.fontes = {
            "cursos:1": "nome: Análise\ndescricao: Limpeza de dados e estatística.",
            "projetos:1": "nome: WorkAdapter\ndescricao: Desenvolvimento com FastAPI.",
        }
        self.schema, self.dados, self.converter = preparar_plano(self.fontes, ["Python"])
        catalogo = self.dados["catalogo_evidencias"]
        self.curso = next(k for k, v in catalogo.items() if "Limpeza" in v["trecho"])
        self.projeto = next(k for k, v in catalogo.items() if "FastAPI" in v["trecho"])
        self.plano = {
            "resumo": {"texto": "Estudos em análise de dados.", "evidencias_ids": [self.curso]},
            "experiencias": [], "formacoes": [],
            "cursos": [{"fonte": "cursos:1", "destaques": [{
                "texto": "Estudo de limpeza de dados.", "evidencias_ids": [self.curso],
            }]}],
            "projetos": [], "habilidades": ["Python"], "idiomas": [],
            "alteracoes": [], "lacunas": [],
        }

    def test_recupera_texto_original_e_preserva_formato_publico(self):
        plano = self.converter(self.schema.model_validate(self.plano))
        evidencia = plano.cursos[0].destaques[0].evidencias[0]
        self.assertEqual(evidencia.fonte, "cursos:1")
        self.assertEqual(evidencia.trecho, "descricao: Limpeza de dados e estatística.")
        self.assertNotIn("evidencias_ids", plano.model_dump_json())

    def test_bloqueia_evidencia_de_outro_item(self):
        self.plano["cursos"][0]["destaques"][0]["evidencias_ids"] = [self.projeto]
        with self.assertRaises(ValidationError):
            self.schema.model_validate(self.plano)

    def test_nao_aceita_citacao_reescrita_nem_id_inventado(self):
        original = deepcopy(self.plano)
        self.plano["resumo"]["trecho"] = "Citação alterada pelo modelo."
        with self.assertRaises(ValidationError):
            self.schema.model_validate(self.plano)
        original["resumo"]["evidencias_ids"] = ["E99999"]
        with self.assertRaises(ValidationError):
            self.schema.model_validate(original)

    def test_secao_sem_registros_deve_ficar_vazia(self):
        self.plano["experiencias"] = [self.plano["cursos"][0]]
        with self.assertRaises(ValidationError):
            self.schema.model_validate(self.plano)

    def test_schema_impede_escolha_de_ids_cruzados(self):
        schema = self.schema.model_json_schema()
        item = schema["$defs"]["Destaque_cursos_0"]["properties"]["evidencias_ids"]["items"]
        permitidos = item.get("enum", [item.get("const")])
        self.assertIn(self.curso, permitidos)
        self.assertNotIn(self.projeto, permitidos)

    def test_multiplos_itens_mesma_secao_e_trechos_longos(self):
        fontes = {**self.fontes, "cursos:2": "descricao: " + "Dados " * 500}
        schema, dados, converter = preparar_plano(fontes, [])
        ids = [k for k, v in dados["catalogo_evidencias"].items() if v["fonte"] == "cursos:2"]
        self.assertGreater(len(ids), 1)
        for ref in ids:
            trecho = dados["catalogo_evidencias"][ref]["trecho"]
            self.assertLessEqual(len(trecho), 2000)
            self.assertIn(trecho, fontes["cursos:2"])
        self.plano["habilidades"] = []
        self.plano["cursos"] = [{"fonte": "cursos:2", "destaques": [{
            "texto": "Estudos em dados.", "evidencias_ids": ids,
        }]}]
        self.assertEqual(converter(schema.model_validate(self.plano)).cursos[0].fonte, "cursos:2")


if __name__ == "__main__":
    unittest.main()
