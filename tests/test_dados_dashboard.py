"""Funções de dados das telas (app/dados_dashboard.py)."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import dados_dashboard  # noqa: E402
from dados_dashboard import carregar_inct, curva_inct, resumo_anual, resumo_inct  # noqa: E402


class CarregarInctTest(unittest.TestCase):
    def test_recusa_arquivo_sem_todos_os_niveis(self):
        incompleto = carregar_inct().query("nivel_m != 7.0")
        with tempfile.TemporaryDirectory() as pasta:
            incompleto.to_csv(Path(pasta) / "inct_longo_limpo.csv", index=False)
            with mock.patch.object(dados_dashboard, "PROCESSADOS", Path(pasta)):
                with self.assertRaises(ValueError):
                    carregar_inct()


class ResumoInctTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dados = carregar_inct()

    def test_lista_so_bairros_atingidos_e_totais_inteiros(self):
        bairros, totais = resumo_inct(self.dados, 5.4)
        self.assertTrue((bairros["affected_buildings"] > 0).all())
        self.assertEqual(totais["bairros"], len(bairros))
        self.assertEqual(totais["predios"], bairros["affected_buildings"].sum())
        self.assertTrue(all(isinstance(v, int) for v in totais.values()))

    def test_impacto_nao_diminui_quando_o_nivel_sobe(self):
        anteriores = {"pessoas": 0, "predios": 0, "bairros": 0}
        for decimo in range(30, 101):
            _, totais = resumo_inct(self.dados, decimo / 10)
            for chave, valor in totais.items():
                self.assertGreaterEqual(valor, anteriores[chave], f"{chave} em {decimo / 10} m")
            anteriores = totais

    def test_nivel_fora_da_simulacao_gera_erro(self):
        with self.assertRaises(ValueError):
            resumo_inct(self.dados, 2.9)

    def test_curva_tem_um_ponto_por_nivel_em_ordem(self):
        curva = curva_inct(self.dados)
        self.assertEqual(len(curva), 71)
        self.assertTrue(curva["nivel_m"].is_monotonic_increasing)


class ResumoAnualTest(unittest.TestCase):
    def test_pico_abaixo_de_tres_metros_fica_sem_estimativa(self):
        ana = pd.DataFrame({
            "data": pd.to_datetime(["2023-01-01", "2023-06-01", "2024-05-05", "2024-05-06"]),
            "nivel_max_cm": [250, 180, 535, 520],
            "estacao": ["Cais Mauá", "Cais Mauá", "Usina do Gasômetro", "Usina do Gasômetro"],
            "acima_cota": [False, False, True, True],
        })
        ana["ano"] = ana["data"].dt.year
        inct = pd.DataFrame({"nivel_m": [5.4, 5.4], "affected_population": [100, 20]})
        r = resumo_anual(ana, inct).set_index("ano")

        self.assertTrue(np.isnan(r.loc[2023, "pessoas_estimadas"]))
        self.assertEqual(r.loc[2023, "pico_cm"], 250)
        self.assertEqual(r.loc[2024, "pessoas_estimadas"], 120)
        self.assertEqual(r.loc[2024, "dias_acima_cota"], 2)
        self.assertEqual(r.loc[2024, "data_pico"], pd.Timestamp("2024-05-05"))


if __name__ == "__main__":
    unittest.main()
