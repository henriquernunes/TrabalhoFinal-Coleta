"""Os scripts, rodados sobre os dados brutos versionados, reproduzem os CSVs processados do repositório."""

import sys
import unittest
from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import processa_ana  # noqa: E402
from carrega_inct import carregar  # noqa: E402
from limpa_inct import checar, limpar  # noqa: E402

PROC = RAIZ / "dados" / "processados"


class ReproducaoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inct, cls.log = limpar(carregar())
        cais, cls.picos_cais = processa_ana.separa_picos(processa_ana.ler("87450004"))
        gas, _ = processa_ana.separa_picos(processa_ana.ler("87444000"))
        cls.unida = processa_ana.unir(cais, gas)

    def test_inct_limpo_passa_nas_checagens_e_bate_com_o_csv(self):
        checar(self.inct)
        assert_frame_equal(self.inct, pd.read_csv(PROC / "inct_longo_limpo.csv"), check_dtype=False)

    def test_correcoes_documentadas_no_relatorio(self):
        self.assertEqual(len(self.log), 17)
        self.assertEqual(self.log["bairro"].nunique(), 5)

    def test_picos_falsos_documentados_no_relatorio(self):
        por_ano = self.picos_cais.groupby(self.picos_cais.index.year).size().to_dict()
        self.assertEqual(por_ano, {2015: 8, 2017: 39, 2019: 57, 2025: 2, 2026: 17})

    def test_ana_diario_bate_com_o_csv(self):
        dia = processa_ana.diario(self.unida).reset_index(drop=True)
        self.assertTrue(dia["data"].is_unique)
        esperado = pd.read_csv(PROC / "ana_diario.csv", parse_dates=["data"])
        assert_frame_equal(dia, esperado, check_dtype=False)

    def test_pico_oficial_sobrevive_a_limpeza(self):
        self.assertEqual(self.unida["nivel_cm"].max(), 535)
        self.assertEqual(self.unida["nivel_cm"].idxmax().strftime("%d/%m/%Y"), "05/05/2024")

    def test_enchente_horaria_bate_com_o_csv(self):
        h = processa_ana.enchente_horaria(self.unida, pd.read_csv(PROC / "inct_longo_limpo.csv"))
        self.assertTrue(h["nivel_cm"].notna().all())
        esperado = pd.read_csv(PROC / "enchente_2024_horario.csv", parse_dates=["data_hora"])
        assert_frame_equal(h, esperado, check_dtype=False)


if __name__ == "__main__":
    unittest.main()
