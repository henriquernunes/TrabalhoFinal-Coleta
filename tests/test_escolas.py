"""Cruzamento espacial das escolas com bairros e cotas exibidas no mapa."""

import unittest

from shapely.geometry import Point, box, mapping

from scripts.gera_mapa import escolas_por_bairro


def feicao(geometria, **propriedades):
    return {"type": "Feature", "geometry": mapping(geometria), "properties": propriedades}


class EscolasNoMapaTest(unittest.TestCase):
    def test_conta_cada_escola_uma_vez_e_sobe_com_a_cota(self):
        escolas = [
            feicao(Point(0.5, 0.5), codigo=11, escola="A"),
            feicao(Point(0.5, 0.5), codigo=11, escola="A duplicada"),
            feicao(Point(1.5, 0.5), codigo=22, escola="B"),
            feicao(Point(3, 0.5), codigo=33, escola="Fora do município"),
        ]
        bairros = [feicao(box(0, 0, 1, 1), nome="Bairro A"),
                   feicao(box(1, 0, 2, 1), nome="Bairro B")]
        contornos = [feicao(box(0, 0, 1.2, 1), cota=300),
                    feicao(box(0, 0, 2, 1), cota=400)]

        resultado, diagnostico = escolas_por_bairro(
            escolas, bairros, contornos, {"BAIRRO A": "Bairro A", "BAIRRO B": "Bairro B"})

        self.assertEqual(diagnostico["escolas_unicas"], 3)
        self.assertEqual(diagnostico["sem_bairro"], 1)
        self.assertEqual(resultado["Bairro A"], {"total": 1, "por_cota": {"300": 1, "400": 1}})
        self.assertEqual(resultado["Bairro B"], {"total": 1, "por_cota": {"300": 0, "400": 1}})


if __name__ == "__main__":
    unittest.main()
