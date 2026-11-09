"""
Carrega a simulação do INCT SiMAI (data.json) em formato longo, SEM limpar nada.
A limpeza fica para o script da Fase 2; aqui só convertemos e listamos sinais de problema.

Fonte: INCT SiMAI — arquivo fornecido pela disciplina (copiar para dados/originais/inct/dados.json)
Saída: dados/processados/inct_longo_bruto.csv  (uma linha por nível e bairro)
Uso:   python scripts/carrega_inct.py
"""
import json
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
ENTRADA = RAIZ / "dados" / "originais" / "inct" / "dados.json"
SAIDA = RAIZ / "dados" / "processados" / "inct_longo_bruto.csv"


def carregar(caminho: Path = ENTRADA) -> pd.DataFrame:
    """Código-base do enunciado: chave '3_0m' vira nivel_m = 3.0."""
    with open(caminho, encoding="utf-8") as f:
        raw = json.load(f)
    return pd.DataFrame([
        {"nivel_m": float(nivel.removesuffix("m").replace("_", ".")), "bairro": bairro, **valores}
        for nivel, bairros in raw.items()
        for bairro, valores in bairros.items()
    ])


def diagnostico(df: pd.DataFrame) -> None:
    """Primeiras checagens sugeridas no enunciado (não altera os dados)."""
    print(f"Formato: {df.shape}  (esperado: (6674, 7))")
    print(f"Níveis: {df['nivel_m'].nunique()} (esperado 71) | bairros distintos: {df['bairro'].nunique()} (esperado 94)")

    por_nivel = df.groupby("nivel_m")["bairro"].count()
    fora = por_nivel[por_nivel != 94]
    print(f"Níveis com número de bairros diferente de 94: {len(fora)}" + (f" -> {fora.to_dict()}" if len(fora) else ""))

    print(f"Valores ausentes por coluna: {df.isna().sum().to_dict()}")

    d = df.sort_values(["bairro", "nivel_m"])
    queda = d.groupby("bairro")["affected_buildings"].diff() < 0
    print(f"Quedas de prédios afetados quando o rio sobe: {queda.sum()} casos")

    pct_calc = 100 * df["affected_buildings"] / df["total_buildings"]
    print(f"percentage diferente do cálculo (tolerância de arredondamento, 0,5 p.p.): {((df['percentage'] - pct_calc).abs() > 0.5).sum()} casos")

    pop_calc = df["population"] * df["percentage"] / 100
    print(f"affected_population diferente de population*percentage/100 (tol. 1): {((df['affected_population'] - pop_calc).abs() > 1).sum()} casos")

    print(f"affected_buildings > total_buildings: {(df['affected_buildings'] > df['total_buildings']).sum()} casos")

    varia = df.groupby("bairro")[["total_buildings", "population"]].nunique()
    print(f"Bairros cujo total_buildings ou population muda entre níveis: {(varia > 1).any(axis=1).sum()}")


if __name__ == "__main__":
    if not ENTRADA.exists():
        raise SystemExit(f"Copie o dados.json do INCT para {ENTRADA}")
    df = carregar()
    diagnostico(df)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(SAIDA, index=False)
    print(f"\nSalvo em {SAIDA}")
