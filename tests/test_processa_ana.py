"""Leitura do XML da ANA e limpeza da telemetria (coleta_ana.py e processa_ana.py)."""

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from coleta_ana import ler_xml  # noqa: E402
from processa_ana import CAIS, GASOMETRO, diario, enchente_horaria, separa_picos, unir  # noqa: E402


def serie(inicio, valores, freq="15min"):
    return pd.Series(valores, index=pd.date_range(inicio, periods=len(valores), freq=freq),
                     name="nivel_cm", dtype=float).rename_axis("data_hora")


class LerXmlTest(unittest.TestCase):
    def test_extrai_registros_com_namespace_e_ignora_nivel_vazio(self):
        xml = """<?xml version="1.0" encoding="utf-8"?>
<DataTable xmlns="http://MRCS/"><diffgram><DocumentElement>
  <DadosHidrometereologicos><DataHora> 2024-05-05 10:00:00 </DataHora><Nivel>535.00</Nivel></DadosHidrometereologicos>
  <DadosHidrometereologicos><DataHora>2024-05-05 10:15:00</DataHora><Nivel></Nivel></DadosHidrometereologicos>
  <DadosHidrometereologicos><DataHora>2024-05-05 10:30:00</DataHora><Nivel>534.00</Nivel></DadosHidrometereologicos>
</DocumentElement></diffgram></DataTable>"""
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "teste.xml"
            arquivo.write_text(xml, encoding="utf-8")
            df = ler_xml(arquivo)
        self.assertEqual(df.values.tolist(), [["2024-05-05 10:00:00", "535.00"],
                                              ["2024-05-05 10:30:00", "534.00"]])

    def test_xml_sem_registros_devolve_tabela_vazia_com_colunas(self):
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "vazio.xml"
            arquivo.write_text("<DataTable/>", encoding="utf-8")
            df = ler_xml(arquivo)
        self.assertTrue(df.empty)
        self.assertEqual(list(df.columns), ["data_hora", "nivel_cm"])


class SeparaPicosTest(unittest.TestCase):
    def test_remove_leitura_isolada_e_mantem_subida_gradual(self):
        valores = [100.0] * 10 + [180.0] + [100.0 + 2 * i for i in range(20)]
        bons, picos = separa_picos(serie("2024-05-01", valores))
        self.assertEqual(picos.tolist(), [180.0])
        self.assertEqual(len(bons), len(valores) - 1)


class UnirTest(unittest.TestCase):
    def test_gasometro_so_cobre_o_periodo_sem_cais_maua(self):
        cais = pd.concat([serie("2024-05-02 22:00", [300.0] * 2, "h"),
                          serie("2024-05-20 00:00", [250.0] * 2, "h")])
        gas = serie("2024-05-02 00:00", [400.0] * (24 * 20), "h")
        u = unir(cais, gas)

        self.assertTrue(u.index.is_monotonic_increasing)
        usados = u[u["estacao"] == GASOMETRO].index
        self.assertEqual(usados.min(), pd.Timestamp("2024-05-03 00:00"))
        self.assertLess(usados.max(), pd.Timestamp("2024-05-20 00:00"))
        self.assertEqual((u["estacao"] == CAIS).sum(), len(cais))

    def test_sem_retorno_do_cais_gasometro_segue_ate_o_fim(self):
        cais = serie("2024-05-02 20:00", [300.0] * 3, "h")
        gas = serie("2024-05-02 00:00", [400.0] * 72, "h")
        u = unir(cais, gas)
        self.assertEqual(u.index.max(), gas.index.max())
        self.assertEqual(u.loc[gas.index.max(), "estacao"], GASOMETRO)


class DiarioTest(unittest.TestCase):
    def test_cota_depende_da_estacao(self):
        u = pd.DataFrame({"nivel_cm": [300.0, 330.0], "estacao": [CAIS, GASOMETRO]},
                         index=pd.DatetimeIndex(["2024-04-01 10:00", "2024-05-05 10:00"], name="data_hora"))
        d = diario(u).set_index("estacao")
        self.assertTrue(d.loc[CAIS, "acima_cota"])
        self.assertFalse(d.loc[GASOMETRO, "acima_cota"])
        self.assertEqual(d["cota_cm"].to_dict(), {CAIS: 300, GASOMETRO: 360})

    def test_dia_com_duas_estacoes_fica_com_a_de_mais_leituras(self):
        u = pd.DataFrame({"nivel_cm": [300.0, 410.0, 420.0], "estacao": [CAIS, GASOMETRO, GASOMETRO]},
                         index=pd.DatetimeIndex(["2024-05-03 00:00", "2024-05-03 10:00", "2024-05-03 11:00"],
                                                name="data_hora"))
        d = diario(u)
        self.assertEqual(len(d), 1)
        self.assertEqual(d.iloc[0]["estacao"], GASOMETRO)
        self.assertEqual(d.iloc[0]["n_leituras"], 2)

    def test_remove_semanas_de_sensor_travado(self):
        travado = [268.0] * 20
        variando = [100.0 + 10 * (i % 3) for i in range(20)]
        u = serie("2015-01-01", travado + variando, "D").to_frame().assign(estacao=CAIS)
        dias = set(diario(u)["data"])
        self.assertNotIn(pd.Timestamp("2015-01-10"), dias)
        self.assertTrue(set(pd.date_range("2015-01-21", periods=20, freq="D")) <= dias)


class EnchenteHorariaTest(unittest.TestCase):
    def setUp(self):
        u = serie("2024-05-01", [200.0] * (24 * 11), "h").to_frame()
        u.loc["2024-05-05 10:00", "nivel_cm"] = 535
        u.loc["2024-05-05 11:00", "nivel_cm"] = 534
        u.loc["2024-05-05 12:00", "nivel_cm"] = 295
        u.loc["2024-05-06 05:00", "nivel_cm"] = 230
        u = u.drop(pd.to_datetime(["2024-05-06 03:00", "2024-05-06 04:00"]))
        u["estacao"] = GASOMETRO
        inct = pd.DataFrame({
            "nivel_m": [3.0, 3.0, 5.3, 5.3, 5.4, 5.4],
            "bairro": ["A", "B"] * 3,
            "affected_population": [0, 10, 100, 50, 200, 80],
            "affected_buildings": [0, 1, 5, 2, 9, 3],
        })
        self.h = enchente_horaria(u, inct).set_index("data_hora")

    def test_horas_sem_leitura_sao_interpoladas_e_marcadas(self):
        lacuna = self.h.loc["2024-05-06 03:00":"2024-05-06 04:00"]
        self.assertEqual(lacuna["origem"].tolist(), ["interpolado", "interpolado"])
        self.assertEqual(lacuna["nivel_cm"].tolist(), [210.0, 220.0])
        self.assertEqual((self.h["origem"] == "interpolado").sum(), 2)

    def test_arredonda_meio_para_cima_e_cruza_com_o_inct(self):
        pico = self.h.loc["2024-05-05 10:00"]
        self.assertEqual(pico["nivel_inct"], 5.4)
        self.assertEqual(pico["pessoas_estimadas"], 280)
        self.assertEqual(pico["predios_estimados"], 12)
        self.assertEqual(self.h.loc["2024-05-05 11:00", "nivel_inct"], 5.3)
        self.assertEqual(self.h.loc["2024-05-05 12:00", "nivel_inct"], 3.0)
        self.assertEqual(self.h.loc["2024-05-05 12:00", "bairros_atingidos"], 1)

    def test_abaixo_de_tres_metros_fica_sem_estimativa(self):
        self.assertTrue(np.isnan(self.h.loc["2024-05-01 00:00", "pessoas_estimadas"]))


if __name__ == "__main__":
    unittest.main()
