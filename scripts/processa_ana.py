"""
Limpa a telemetria da ANA, une as duas estações e cruza a enchente de 2024 com o INCT.

Entradas: dados/originais/ana/<codigo>_15min.csv (gerados por coleta_ana.py)
          dados/processados/inct_longo_limpo.csv (gerado por limpa_inct.py)
Saídas em dados/processados/:
  ana_diario.csv            uma linha por dia, com a estação usada e a cota de inundação dela
  enchente_2024_horario.csv nível de hora em hora (01 a 11/05/2024) + estimativas do INCT
Uso: python scripts/processa_ana.py

Limites: o Cais Mauá é a estação principal; o Gasômetro cobre só o período sem Cais Mauá.
As estações têm referenciais diferentes e os valores NÃO são ajustados (ver relatório).
"""
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
ANA = RAIZ / "dados" / "originais" / "ana"
PROC = RAIZ / "dados" / "processados"
CAIS, GASOMETRO = "Cais Mauá", "Usina do Gasômetro"
COTA_CM = {CAIS: 300, GASOMETRO: 360}
LIMIAR_TRAVADO_CM = 2  # em 15 dias o Guaíba real sempre varia mais que isso
LIMIAR_PICO_CM = 20  # desvio em relação à mediana de 9 leituras (~2 h); o rio nunca variou isso nesse intervalo


def ler(codigo: str) -> pd.Series:
    return pd.read_csv(ANA / f"{codigo}_15min.csv", parse_dates=["data_hora"]).set_index("data_hora")["nivel_cm"]


def separa_picos(s: pd.Series) -> tuple[pd.Series, pd.Series]:
    desvio = (s - s.rolling(9, center=True, min_periods=3).median()).abs()
    return s[desvio <= LIMIAR_PICO_CM], s[desvio > LIMIAR_PICO_CM]


def unir(cais: pd.Series, gas: pd.Series) -> pd.DataFrame:
    """Dias com Cais Mauá usam Cais Mauá, exceto 03/05/2024 em diante enquanto ele esteve fora do ar."""
    fim_cais = pd.Timestamp("2024-05-02 23:59")
    volta_cais = cais[cais.index > fim_cais].index.min()
    gas_ponte = gas[(gas.index > fim_cais) & (gas.index < volta_cais)] if pd.notna(volta_cais) else gas[gas.index > fim_cais]
    return pd.concat([
        cais[cais.index <= fim_cais].to_frame().assign(estacao=CAIS),
        gas_ponte.to_frame().assign(estacao=GASOMETRO),
        cais[cais.index > fim_cais].to_frame().assign(estacao=CAIS),
    ]).sort_index()


def diario(u: pd.DataFrame) -> pd.DataFrame:
    d = (u.groupby([u.index.normalize(), "estacao"])["nivel_cm"]
          .agg(nivel_max_cm="max", nivel_medio_cm="mean", n_leituras="count")
          .reset_index().rename(columns={"data_hora": "data"}))
    # 03/05/2024 e dias de troca podem ter duas estações: fica a de mais leituras
    d = d.sort_values("n_leituras").drop_duplicates("data", keep="last").sort_values("data")
    # sensor travado: média diária quase constante por semanas (ex.: 268 cm e 98 cm em 2015-16)
    faixa = d.set_index("data")["nivel_medio_cm"].rolling("15D", center=True)
    travado = (faixa.max() - faixa.min() <= LIMIAR_TRAVADO_CM).to_numpy() & (faixa.count() >= 10).to_numpy()
    d = d[~travado].copy()
    d["cota_cm"] = d["estacao"].map(COTA_CM)
    d["acima_cota"] = d["nivel_max_cm"] >= d["cota_cm"]
    d["nivel_medio_cm"] = d["nivel_medio_cm"].round(1)
    return d


def enchente_horaria(u: pd.DataFrame, inct: pd.DataFrame) -> pd.DataFrame:
    janela = u["2024-05-01":"2024-05-11"]
    h = janela["nivel_cm"].resample("h").max().to_frame("nivel_cm")  # máximo: a média da hora esconderia o pico de 5,35 m
    h["estacao"] = janela["estacao"].resample("h").last()
    h["origem"] = h["nivel_cm"].notna().map({True: "medido", False: "interpolado"})
    h["nivel_cm"] = h["nivel_cm"].interpolate()
    h["nivel_m"] = (h["nivel_cm"] / 100).round(2)
    h["nivel_inct"] = np.floor(h["nivel_cm"] / 10 + 0.5) / 10  # meio para cima (5,35 -> 5,4); abaixo de 3,0 m fica sem simulação

    atingido = inct[inct["affected_buildings"] > 0]
    por_nivel = pd.DataFrame({
        "pessoas_estimadas": inct.groupby("nivel_m")["affected_population"].sum(),
        "predios_estimados": inct.groupby("nivel_m")["affected_buildings"].sum(),
        "bairros_atingidos": atingido.groupby("nivel_m")["bairro"].nunique(),
    })
    return h.join(por_nivel, on="nivel_inct").rename_axis("data_hora").reset_index()


if __name__ == "__main__":
    cais, picos_c = separa_picos(ler("87450004"))
    gas, picos_g = separa_picos(ler("87444000"))

    unida = unir(cais, gas)
    dia = diario(unida)
    h = enchente_horaria(unida, pd.read_csv(PROC / "inct_longo_limpo.csv"))

    assert dia["data"].is_unique and h["nivel_cm"].notna().all()
    assert unida["nivel_cm"].max() == 535, "o pico oficial de 5,35 m tem de sobreviver à limpeza"
    dia.to_csv(PROC / "ana_diario.csv", index=False)
    h.to_csv(PROC / "enchente_2024_horario.csv", index=False)
    print(f"Picos removidos: Cais {len(picos_c)}, Gasômetro {len(picos_g)}")
    print(f"Dias: {len(dia)} | Horas interpoladas em maio/2024: {(h['origem'] == 'interpolado').sum()}")
    print(unida.groupby('estacao').apply(lambda x: (x.index.min(), x.index.max(), len(x))).to_string())
