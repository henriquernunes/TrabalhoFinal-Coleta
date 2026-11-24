"""Regressões dos fluxos visíveis das duas telas analíticas."""

import base64
import json
import sys
import unittest
from pathlib import Path

import numpy as np
from streamlit.testing.v1 import AppTest

TEMPO_LIMITE = 30
APP = Path(__file__).resolve().parents[1] / "app" / "app.py"
sys.path.insert(0, str(APP.parent))
from dados_dashboard import carregar_ana, carregar_inct, resumo_anual  # noqa: E402


def valores(serie):
    """Séries numéricas do Plotly chegam codificadas em binário ({'dtype', 'bdata'})."""
    if isinstance(serie, dict):
        return np.frombuffer(base64.b64decode(serie["bdata"]), dtype=serie["dtype"]).tolist()
    return serie


class DashboardTest(unittest.TestCase):
    def test_pico_de_2024_relaciona_ana_ao_inct(self):
        linha = resumo_anual(carregar_ana(), carregar_inct()).set_index("ano").loc[2024]
        self.assertEqual(linha["pico_cm"], 535)
        self.assertEqual(linha["nivel_inct"], 5.4)
        self.assertEqual(linha["pessoas_estimadas"], 139179)

    def test_simulacao_inct_atualiza_indicadores_e_graficos(self):
        app = AppTest.from_file(str(APP), default_timeout=TEMPO_LIMITE)
        app.query_params["tela"] = "inct"
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual([x.value for x in app.metric], ["139.179", "55.170", "36"])
        self.assertEqual(len(app.get("plotly_chart")), 3)
        barras = json.loads(app.get("plotly_chart")[0].proto.spec)["data"][0]
        self.assertEqual(len(barras["y"]), 36)

        app.slider[0].set_value(3.0).run()
        self.assertFalse(app.exception)
        self.assertEqual([x.value for x in app.metric], ["32.112", "14.647", "24"])

        app.slider[0].set_value(10.0).run()
        self.assertFalse(app.exception)
        self.assertEqual([x.value for x in app.metric], ["271.875", "101.211", "54"])

    def test_painel_historico_filtra_anos_e_exibe_tres_graficos(self):
        app = AppTest.from_file(str(APP), default_timeout=TEMPO_LIMITE)
        app.query_params.update(tela="enchente", painel="historico")
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get("plotly_chart")), 3)
        self.assertEqual(app.slider[0].value, (2014, 2026))

        app.slider[0].set_value((2023, 2024)).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.slider[0].value, (2023, 2024))
        self.assertEqual(len(app.get("plotly_chart")), 3)
        for grafico in app.get("plotly_chart"):
            serie = json.loads(grafico.proto.spec)["data"][0]
            self.assertEqual(serie["x"], ["2023", "2024"])

    def test_mapa_anterior_continua_na_tela_de_2024(self):
        app = AppTest.from_file(str(APP), default_timeout=TEMPO_LIMITE).run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get("iframe")), 1)
        self.assertIn("Realçar água", app.get("iframe")[0].proto.srcdoc)

    def test_ranking_troca_entre_pessoas_e_predios(self):
        app = AppTest.from_file(str(APP), default_timeout=TEMPO_LIMITE)
        app.query_params["tela"] = "inct"
        app.run()
        tabela = app.dataframe[0].value
        self.assertEqual(len(tabela), 10)
        self.assertTrue(tabela["Pessoas"].is_monotonic_decreasing)

        app.radio[0].set_value("Prédios").run()
        self.assertFalse(app.exception)
        tabela = app.dataframe[0].value
        self.assertTrue(tabela["Prédios"].is_monotonic_decreasing)
        self.assertEqual(len(tabela), 10)

    def test_seletor_de_bairro_mostra_a_curva_e_acompanha_o_nivel(self):
        app = AppTest.from_file(str(APP), default_timeout=TEMPO_LIMITE)
        app.query_params["tela"] = "inct"
        app.run()
        seletor = app.selectbox(key="bairro_inct")
        self.assertEqual(seletor.value, "Sarandi")
        self.assertEqual(len(seletor.options), 94)
        curva = json.loads(app.get("plotly_chart")[2].proto.spec)
        self.assertEqual(len(valores(curva["data"][0]["x"])), 71)
        self.assertEqual(max(valores(curva["data"][0]["y"])), 78.39)
        self.assertIn("Sarandi", curva["layout"]["title"]["text"])
        texto = " ".join(m.value for m in app.markdown)
        self.assertIn("começa a ter prédios atingidos a **3,0 m**", texto)
        self.assertIn("**24.391 pessoas**", texto)
        self.assertIn("**47,32%**", texto)

        seletor.set_value("Bom Fim").run()
        self.assertFalse(app.exception)
        self.assertIn("não tem prédios atingidos", " ".join(m.value for m in app.markdown))

        app.selectbox(key="bairro_inct").set_value("Menino Deus").run()
        app.slider[0].set_value(3.0).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox(key="bairro_inct").value, "Menino Deus")
        texto = " ".join(m.value for m in app.markdown)
        self.assertIn("a **3,3 m**", texto)
        self.assertIn("A 3,0 m: **0 pessoas**", texto)

    def test_tela_inct_ignora_painel_historico(self):
        app = AppTest.from_file(str(APP), default_timeout=TEMPO_LIMITE)
        app.query_params.update(tela="inct", painel="historico")
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(app.title[0].value, "Simulação do INCT SiMAI")
        self.assertEqual(len(app.get("iframe")), 0)

    def test_tela_desconhecida_abre_o_mapa(self):
        app = AppTest.from_file(str(APP), default_timeout=TEMPO_LIMITE)
        app.query_params["tela"] = "nao-existe"
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get("iframe")), 1)


if __name__ == "__main__":
    unittest.main()
