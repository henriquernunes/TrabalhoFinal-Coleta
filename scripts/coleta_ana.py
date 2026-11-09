"""
Coleta do nível do Guaíba (telemetria) no web service público da ANA.

Fonte: ANA — ServiceANA, método DadosHidrometeorologicos
       https://telemetriaws1.ana.gov.br/ServiceANA.asmx
Estações:
  87450004  Cais Mauá C6        — 2014 até 02/05/2024 (sensor perdido na enchente)
  87444000  Usina do Gasômetro  — a partir de 03/05/2024 (registrou o pico de 5,35 m)
Nenhuma das duas tem série convencional no HidroWeb; por isso usamos a telemetria
(leituras automáticas a cada 15 min).

Saídas (em dados/originais/ana/):
  <codigo>_<ano>.xml       resposta bruta, um arquivo por ano (não é baixada de novo)
  <codigo>_<ano>_<mes>.xml quando o ano inteiro falha no servidor, um arquivo por mês
  <codigo>_15min.csv       todas as leituras: data_hora, nivel_cm
  <codigo>_diario.csv      resumo diário: nivel_max_cm, nivel_medio_cm, n_leituras

Uso (a partir da raiz do repositório):
  python scripts/coleta_ana.py              # as duas estações
  python scripts/coleta_ana.py 87444000     # só uma
"""
import calendar
import sys
import time
from datetime import date
from pathlib import Path
import xml.etree.ElementTree as ET

import pandas as pd
import requests

URL = "https://telemetriaws1.ana.gov.br/ServiceANA.asmx/DadosHidrometeorologicos"
RAIZ = Path(__file__).resolve().parents[1]
PASTA = RAIZ / "dados" / "originais" / "ana"
ESTACOES = {
    "87450004": {"nome": "Cais Mauá C6", "inicio": 2014},
    "87444000": {"nome": "Usina do Gasômetro", "inicio": 2024},
}


def baixar(destino: Path, codigo: str, inicio: date, fim: date) -> Path:
    """Baixa um intervalo de telemetria. Arquivos de períodos já encerrados não são pedidos de novo."""
    if destino.exists() and fim < date.today():
        return destino
    params = {"codEstacao": codigo, "dataInicio": f"{inicio:%d/%m/%Y}", "dataFim": f"{fim:%d/%m/%Y}"}
    r = requests.get(URL, params=params, timeout=180)
    r.raise_for_status()
    destino.write_bytes(r.content)
    time.sleep(1)  # coleta responsável: uma requisição por segundo
    return destino


def baixar_ano(codigo: str, ano: int) -> list[Path]:
    """Baixa um ano inteiro; se o servidor falhar (ex.: 2021 do Cais Mauá dá erro 500), baixa mês a mês."""
    mensais = sorted(PASTA.glob(f"{codigo}_{ano}_*.xml"))
    if mensais and ano < date.today().year:
        return mensais
    try:
        return [baixar(PASTA / f"{codigo}_{ano}.xml", codigo, date(ano, 1, 1), date(ano, 12, 31))]
    except requests.RequestException as e:
        print(f"  {ano}: ano inteiro falhou ({e.__class__.__name__}), baixando mês a mês")
    meses = range(1, 13 if ano < date.today().year else date.today().month + 1)
    return [baixar(PASTA / f"{codigo}_{ano}_{m:02d}.xml", codigo, date(ano, m, 1),
                   date(ano, m, calendar.monthrange(ano, m)[1]))
            for m in meses]


def ler_xml(arquivo: Path) -> pd.DataFrame:
    """Extrai DataHora e Nivel de cada registro <DadosHidrometereologicos> (registros sem nível são ignorados)."""
    raiz = ET.parse(arquivo).getroot()
    linhas = []
    for reg in raiz.iter():
        if not reg.tag.lower().endswith("dadoshidrometereologicos"):
            continue
        campos = {c.tag.split("}")[-1]: (c.text or "").strip() for c in reg}
        if campos.get("Nivel", "") == "":
            continue
        linhas.append({"data_hora": campos.get("DataHora", ""), "nivel_cm": campos["Nivel"]})
    return pd.DataFrame(linhas, columns=["data_hora", "nivel_cm"])


def coletar(codigo: str) -> None:
    info = ESTACOES.get(codigo, {"nome": codigo, "inicio": 2014})
    print(f"\n== {codigo} — {info['nome']} ==")
    partes = []
    for ano in range(info["inicio"], date.today().year + 1):
        try:
            df_ano = pd.concat([ler_xml(arq) for arq in baixar_ano(codigo, ano)], ignore_index=True)
        except (requests.RequestException, ET.ParseError) as e:
            print(f"  {ano}: falha — {e}")
            continue
        print(f"  {ano}: {len(df_ano)} leituras com nível")
        partes.append(df_ano)

    df = pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()
    if df.empty:
        print("  Nenhuma leitura de nível encontrada.")
        return

    df["data_hora"] = pd.to_datetime(df["data_hora"].str.strip(), errors="coerce")
    df["nivel_cm"] = pd.to_numeric(df["nivel_cm"].str.replace(",", "."), errors="coerce")
    df = df.dropna().drop_duplicates("data_hora").sort_values("data_hora")
    df.to_csv(PASTA / f"{codigo}_15min.csv", index=False)

    diario = (df.set_index("data_hora")["nivel_cm"]
                .resample("D").agg(["max", "mean", "count"])
                .rename(columns={"max": "nivel_max_cm", "mean": "nivel_medio_cm", "count": "n_leituras"})
                .query("n_leituras > 0"))
    diario.to_csv(PASTA / f"{codigo}_diario.csv")

    pico = df.loc[df["nivel_cm"].idxmax()]
    print(f"  Total: {len(df)} leituras, {df['data_hora'].min():%d/%m/%Y} a {df['data_hora'].max():%d/%m/%Y}")
    print(f"  Máximo: {pico['nivel_cm'] / 100:.2f} m em {pico['data_hora']:%d/%m/%Y %H:%M}")


if __name__ == "__main__":
    PASTA.mkdir(parents=True, exist_ok=True)
    codigos = sys.argv[1:] or list(ESTACOES)
    for codigo in codigos:
        coletar(codigo)
