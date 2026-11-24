"""Funções auxiliares do gerador do mapa (scripts/gera_mapa.py)."""

import unittest
from unittest import mock

from shapely.geometry import MultiPolygon, box

from scripts import gera_mapa
from scripts.gera_mapa import AREA_MIN, chave, so_poligonos_grandes


class ChaveTest(unittest.TestCase):
    def test_ignora_acento_caixa_pontuacao_e_espacos(self):
        self.assertEqual(chave("  Petrópolis "), "PETROPOLIS")
        self.assertEqual(chave("São   João"), "SAO JOAO")
        self.assertEqual(chave("Passo d’Areia"), chave("PASSO DAREIA"))

    def test_nomes_especiais_da_prefeitura_casam_com_o_inct(self):
        self.assertEqual(chave("Cel. Aparício Borges"), "CORONEL APARICIO BORGES")
        self.assertEqual(chave("Passo da Areia"), "PASSO DAREIA")


class PoligonosTest(unittest.TestCase):
    def test_descarta_manchas_menores_que_a_area_minima(self):
        lado = AREA_MIN ** 0.5
        grande, pequeno = box(0, 0, 2 * lado, 2 * lado), box(10, 10, 10 + lado / 2, 10 + lado / 2)
        resultado = so_poligonos_grandes(MultiPolygon([grande, pequeno]))
        self.assertEqual(len(resultado.geoms), 1)
        self.assertTrue(resultado.geoms[0].equals(grande))


class EventosTest(unittest.TestCase):
    def test_soma_hora_do_texto_ao_dia_e_ordena(self):
        meia_noite_4_5 = 1714780800000  # 2024-05-04 00:00 UTC, em milissegundos
        feicoes = [
            {"properties": {"notas": "22:40 Fechamento das comportas", "data": meia_noite_4_5,
                            "long": -51.2, "lat": -30.0, "projeto": "DMAE"}},
            {"properties": {"notas": "sem horário", "data": meia_noite_4_5,
                            "long": 0, "lat": 0, "projeto": "x"}},
            {"properties": {"notas": "8:05 Casa de bombas desligada", "data": meia_noite_4_5,
                            "long": -51.1, "lat": -30.1, "projeto": "EBAP"}},
            {"properties": {"notas": None, "data": meia_noite_4_5, "long": 0, "lat": 0, "projeto": "y"}},
        ]
        with mock.patch.object(gera_mapa, "le", return_value=feicoes):
            eventos = gera_mapa.eventos()
        self.assertEqual([(e["t"], e["txt"]) for e in eventos],
                         [("2024-05-04T08:05", "Casa de bombas desligada"),
                          ("2024-05-04T22:40", "Fechamento das comportas")])


class SerieTest(unittest.TestCase):
    def test_linha_do_tempo_vai_de_2_a_10_de_maio_com_o_pico(self):
        serie = gera_mapa.serie()
        self.assertEqual(serie[0]["t"], "2024-05-02T00:00")
        self.assertEqual(serie[-1]["t"], "2024-05-10T23:00")
        self.assertEqual(len(serie), 9 * 24)
        pico = max(serie, key=lambda s: s["cm"])
        self.assertEqual((pico["cm"], pico["n"]), (535, 5.4))
        self.assertTrue(all(s["p"] is None for s in serie if s["cm"] < 295))


if __name__ == "__main__":
    unittest.main()
