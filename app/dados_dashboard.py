"""Leituras já limpas usadas pelas duas telas do dashboard."""

from pathlib import Path

import numpy as np
import pandas as pd


RAIZ = Path(__file__).resolve().parents[1]
PROCESSADOS = RAIZ / "dados" / "processados"


def carregar_inct() -> pd.DataFrame:
    dados = pd.read_csv(PROCESSADOS / "inct_longo_limpo.csv")
    niveis = set(dados["nivel_m"].round(1))
    esperado = {n / 10 for n in range(30, 101)}
    if niveis != esperado or dados["bairro"].nunique() != 94:
        raise ValueError("O arquivo limpo do INCT não contém os 71 níveis e 94 bairros esperados.")
    return dados


def resumo_inct(dados: pd.DataFrame, nivel: float) -> tuple[pd.DataFrame, dict[str, int]]:
    selecionado = dados[dados["nivel_m"].eq(round(nivel, 1))].copy()
    if len(selecionado) != 94:
        raise ValueError(f"Dados incompletos do INCT para {nivel:.1f} m.")
    atingidos = selecionado["affected_buildings"].gt(0)
    totais = {
        "pessoas": int(selecionado["affected_population"].sum()),
        "predios": int(selecionado["affected_buildings"].sum()),
        "bairros": int(atingidos.sum()),
    }
    return selecionado[atingidos], totais


def curva_inct(dados: pd.DataFrame) -> pd.DataFrame:
    return (dados.groupby("nivel_m", as_index=False)["affected_population"]
            .sum().sort_values("nivel_m"))


def serie_bairro(dados: pd.DataFrame, bairro: str) -> pd.DataFrame:
    """Uma linha por nível para o bairro escolhido, do menor para o maior nível."""
    serie = dados[dados["bairro"].eq(bairro)].sort_values("nivel_m")
    if len(serie) != 71:
        raise ValueError(f"Dados incompletos do INCT para o bairro {bairro}.")
    return serie


def nivel_inicial(serie: pd.DataFrame) -> float | None:
    """Primeiro nível com algum prédio atingido; None se o bairro não é atingido até 10 m."""
    atingidos = serie.loc[serie["affected_buildings"].gt(0), "nivel_m"]
    return None if atingidos.empty else float(atingidos.min())


def carregar_ana() -> pd.DataFrame:
    dados = pd.read_csv(PROCESSADOS / "ana_diario.csv", parse_dates=["data"])
    dados["ano"] = dados["data"].dt.year
    return dados


def resumo_anual(ana: pd.DataFrame, inct: pd.DataFrame) -> pd.DataFrame:
    """Contagens observadas da ANA e impacto hipotético do pico segundo o INCT."""
    resumo = (ana.groupby("ano", as_index=False)
              .agg(dias_com_leitura=("data", "count"), dias_acima_cota=("acima_cota", "sum")))
    picos = ana.loc[ana.groupby("ano")["nivel_max_cm"].idxmax(),
                    ["ano", "nivel_max_cm", "estacao", "data"]].copy()
    picos = picos.rename(columns={"nivel_max_cm": "pico_cm", "estacao": "estacao_pico", "data": "data_pico"})
    picos["pico_m"] = picos["pico_cm"] / 100
    picos["nivel_inct"] = np.floor(picos["pico_cm"] / 10 + 0.5) / 10
    pessoas = inct.groupby("nivel_m")["affected_population"].sum()
    picos["pessoas_estimadas"] = picos["nivel_inct"].map(pessoas)
    return resumo.merge(picos, on="ano", validate="one_to_one").sort_values("ano")
