"""Leitura e limpeza da simulação do INCT (carrega_inct.py e limpa_inct.py)."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from carrega_inct import carregar  # noqa: E402
from limpa_inct import corrige_predios, limpar, maior_seq_nao_decrescente  # noqa: E402


def linha(bairro, nivel, afetados, total=200, populacao=1000):
    return {"bairro": bairro, "nivel_m": nivel, "affected_buildings": afetados,
            "total_buildings": total, "population": populacao,
            "percentage": 0.0, "affected_population": 0}


class CarregaInctTest(unittest.TestCase):
    def test_chave_do_nivel_vira_numero_e_cada_bairro_uma_linha(self):
        bruto = {
            "3_0m": {"Centro": {"affected_buildings": 0}, "Sarandi": {"affected_buildings": 2}},
            "10_0m": {"Centro": {"affected_buildings": 9}},
        }
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "dados.json"
            arquivo.write_text(json.dumps(bruto), encoding="utf-8")
            df = carregar(arquivo)

        self.assertEqual(len(df), 3)
        self.assertEqual(sorted(df["nivel_m"].unique()), [3.0, 10.0])
        self.assertEqual(df.set_index(["nivel_m", "bairro"]).loc[(3.0, "Sarandi"), "affected_buildings"], 2)


class MaiorSequenciaTest(unittest.TestCase):
    def test_descarta_so_o_ponto_fora_da_sequencia(self):
        self.assertEqual(maior_seq_nao_decrescente([1, 5, 2, 3, 4]), {0, 2, 3, 4})

    def test_valores_repetidos_contam_como_nao_decrescentes(self):
        self.assertEqual(maior_seq_nao_decrescente([3, 3, 3]), {0, 1, 2})
        self.assertEqual(maior_seq_nao_decrescente([1, 2, 2, 1, 3]), {0, 1, 2, 4})

    def test_sequencia_decrescente_mantem_um_unico_ponto(self):
        self.assertEqual(len(maior_seq_nao_decrescente([5, 4, 3])), 1)


class CorrigePrediosTest(unittest.TestCase):
    def test_interpola_ponto_interno(self):
        grupo = pd.DataFrame({"affected_buildings": [0, 10, 50, 20, 30]})
        self.assertEqual(corrige_predios(grupo).tolist(), [0, 10, 15, 20, 30])

    def test_ponta_repete_o_valor_valido_mais_proximo(self):
        grupo = pd.DataFrame({"affected_buildings": [90, 10, 20, 30]})
        self.assertEqual(corrige_predios(grupo).tolist(), [10, 10, 20, 30])


class LimparTest(unittest.TestCase):
    def setUp(self):
        # fora de ordem de propósito: limpar() tem de ordenar por bairro e nível
        self.bruto = pd.DataFrame([
            linha("B", 3.1, 1, total=3), linha("A", 3.1, 90), linha("A", 3.0, 0),
            linha("A", 3.3, 40), linha("A", 3.2, 20), linha("B", 3.0, 0, total=3),
        ])
        self.limpo, self.log = limpar(self.bruto)

    def test_corrige_predios_e_recalcula_percentual_e_populacao(self):
        a = self.limpo[self.limpo["bairro"] == "A"].set_index("nivel_m")
        self.assertEqual(a["affected_buildings"].tolist(), [0, 10, 20, 40])
        self.assertEqual(a.loc[3.1, "percentage"], 5.0)
        self.assertEqual(a.loc[3.1, "affected_population"], 50)
        self.assertEqual(a.loc[3.1, "affected_buildings_original"], 90)

    def test_percentual_exato_sem_arredondar_para_cima(self):
        b = self.limpo[self.limpo["bairro"] == "B"].set_index("nivel_m")
        self.assertEqual(b.loc[3.1, "percentage"], 33.33)
        self.assertEqual(b.loc[3.1, "affected_population"], 333)

    def test_log_lista_somente_valores_alterados(self):
        self.assertEqual(self.log[["bairro", "nivel_m", "valor_original", "valor_corrigido"]]
                         .values.tolist(), [["A", 3.1, 90, 10]])
        self.assertEqual(self.limpo["predios_corrigido"].sum(), 1)


if __name__ == "__main__":
    unittest.main()
