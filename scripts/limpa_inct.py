"""
Limpa a simulação do INCT SiMAI e grava o formato longo final.

Entrada: dados/originais/inct/dados.json
Saída:   dados/processados/inct_longo_limpo.csv (6674 linhas; uma por nível e bairro)
Uso:     python scripts/limpa_inct.py

Decisões (justificadas em relatorios/limpeza_dados.pdf):
  1. affected_buildings tem de ser não decrescente com o nível. Mantemos a maior sequência
     não decrescente de cada bairro; o que fica fora é erro e é interpolado pelos vizinhos.
  2. percentage vem arredondado para cima; recalculamos o valor exato.
  3. affected_population herdou esse arredondamento; recalculamos com o percentual exato.
"""
from bisect import bisect_right
from pathlib import Path

import pandas as pd

from carrega_inct import carregar, ENTRADA

RAIZ = Path(__file__).resolve().parents[1]
SAIDA = RAIZ / "dados" / "processados" / "inct_longo_limpo.csv"


def maior_seq_nao_decrescente(valores: list[int]) -> set[int]:
    """Posições da maior subsequência não decrescente (patience sorting, O(n log n))."""
    caudas, pos_caudas, anterior = [], [], [-1] * len(valores)
    for i, v in enumerate(valores):
        j = bisect_right(caudas, v)
        anterior[i] = pos_caudas[j - 1] if j else -1
        if j == len(caudas):
            caudas.append(v)
            pos_caudas.append(i)
        else:
            caudas[j] = v
            pos_caudas[j] = i
    mantidos, i = set(), pos_caudas[-1]
    while i != -1:
        mantidos.add(i)
        i = anterior[i]
    return mantidos


def corrige_predios(grupo: pd.DataFrame) -> pd.Series:
    """Interpola os pontos fora da sequência; nas pontas repete o valor válido mais próximo."""
    valores = grupo["affected_buildings"].tolist()
    mantidos = maior_seq_nao_decrescente(valores)
    s = pd.Series([v if i in mantidos else None for i, v in enumerate(valores)],
                  index=grupo.index, dtype="float")
    return s.interpolate(limit_area="inside").bfill().ffill().round().astype(int)


def limpar(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    d = df.sort_values(["bairro", "nivel_m"]).reset_index(drop=True)
    d["affected_buildings_original"] = d["affected_buildings"]
    d["percentage_original"] = d["percentage"]
    d["affected_population_original"] = d["affected_population"]

    for _, grupo in d.groupby("bairro"):
        d.loc[grupo.index, "affected_buildings"] = corrige_predios(grupo)
    d["predios_corrigido"] = d["affected_buildings"] != d["affected_buildings_original"]

    razao = d["affected_buildings"] / d["total_buildings"]
    d["percentage"] = (100 * razao).round(2)
    d["affected_population"] = (d["population"] * razao).round().astype(int)

    log = d.loc[d["predios_corrigido"], ["bairro", "nivel_m", "affected_buildings_original",
                                         "affected_buildings", "total_buildings"]]
    log = log.rename(columns={"affected_buildings_original": "valor_original",
                              "affected_buildings": "valor_corrigido"})
    return d, log


def checar(d: pd.DataFrame) -> None:
    assert d.shape[0] == 6674 and d["nivel_m"].nunique() == 71 and d["bairro"].nunique() == 94
    assert not d.duplicated(["nivel_m", "bairro"]).any()
    assert (d.groupby("bairro")["affected_buildings"].diff().dropna() >= 0).all()
    assert (d["affected_buildings"] <= d["total_buildings"]).all()
    assert d["percentage"].between(0, 100).all()
    assert (d["affected_population"] <= d["population"]).all()


if __name__ == "__main__":
    limpo, log = limpar(carregar(ENTRADA))
    checar(limpo)
    limpo.to_csv(SAIDA, index=False)
    print(f"{len(limpo)} linhas em {SAIDA.name}; {len(log)} valores de prédios corrigidos em {log['bairro'].nunique()} bairros")
    print(log.groupby("bairro").size().to_string())
