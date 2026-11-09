"""
Monta app/mapa.html: mapa navegável da enchente, com a mancha subindo conforme a linha do tempo.

Entradas: dados/originais/prefeitura/*.geojson (coleta_prefeitura.py),
          dados/processados/enchente_2024_horario.csv e inct_longo_limpo.csv
Saídas:   dados/processados/mapa_dados.json e app/mapa.html
Uso:      python scripts/gera_mapa.py
          python scripts/gera_mapa.py --html-only  # após mudar só o modelo HTML

Cada cota guarda uma única mancha acumulada. O navegador envia apenas a cota selecionada
ao MapLibre, para não tentar indexar todas as 25 geometrias de uma vez.
A suavização remove o ruído do modelo de 5 m e deixa o arquivo leve.
"""
import json
import argparse
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from shapely import make_valid, set_precision
from shapely.geometry import MultiPolygon, mapping, shape
from shapely.ops import unary_union

RAIZ = Path(__file__).resolve().parents[1]
ORIG = RAIZ / "dados" / "originais" / "prefeitura"
PROC = RAIZ / "dados" / "processados"
SUAVIZA, SIMPLIFICA = 0.00007, 0.00007  # em graus, cerca de 7 m
AREA_MIN = 0.00015 ** 2  # descarta manchas de ~250 m² ou menos
NOME_ESPECIAL = {"CEL APARICIO BORGES": "CORONEL APARICIO BORGES", "PASSO DA AREIA": "PASSO DAREIA"}


def le(nome: str) -> list[dict]:
    return json.loads((ORIG / f"{nome}.geojson").read_text(encoding="utf-8"))["features"]


def chave(nome: str) -> str:
    s = "".join(c for c in unicodedata.normalize("NFD", nome.upper()) if not unicodedata.combining(c))
    s = re.sub(r"\s+", " ", re.sub(r"[.'’]", "", s)).strip()
    return NOME_ESPECIAL.get(s, s)


def so_poligonos_grandes(g):
    partes = [p for p in getattr(g, "geoms", [g]) if p.geom_type == "Polygon" and p.area >= AREA_MIN]
    return MultiPolygon(partes)


def geo(g, casas: float = 1e-5) -> dict:
    return mapping(set_precision(g, casas))


def contornos() -> list[dict]:
    saida, anterior = [], None
    for f in sorted(le("cotas"), key=lambda f: f["properties"]["contourmax"]):
        cota = f["properties"]["contourmax"]
        g = make_valid(shape(f["geometry"])).buffer(SUAVIZA).buffer(-2 * SUAVIZA).buffer(SUAVIZA).simplify(SIMPLIFICA)
        anterior = unary_union([g, anterior]) if anterior is not None else g
        saida.append({"type": "Feature", "properties": {"cota": cota}, "geometry": geo(so_poligonos_grandes(anterior))})
        print(cota, end=" ", flush=True)
    print()
    return saida


def eventos() -> list[dict]:
    """A hora vem no início do texto do DMAE; eventos iguais (15 comportas às 22h40) viram um só marcador de texto."""
    saida = []
    for f in le("eventos"):
        p = f["properties"]
        m = re.match(r"(\d{1,2}):(\d{2})\s+(.*)", p["notas"] or "")
        if not m:
            continue
        dia = datetime.fromtimestamp(p["data"] / 1000, timezone.utc).replace(tzinfo=None)
        quando = dia + timedelta(hours=int(m[1]), minutes=int(m[2]))
        saida.append({"t": quando.strftime("%Y-%m-%dT%H:%M"), "txt": m[3], "lon": p["long"], "lat": p["lat"], "nome": p["projeto"]})
    return sorted(saida, key=lambda e: e["t"])


def serie() -> list[dict]:
    h = pd.read_csv(PROC / "enchente_2024_horario.csv", parse_dates=["data_hora"])
    h = h[h["data_hora"].between("2024-05-02", "2024-05-10 23:00")]
    return [{"t": r.data_hora.strftime("%Y-%m-%dT%H:00"), "cm": round(float(r.nivel_cm)),
             "p": None if pd.isna(r.pessoas_estimadas) else int(r.pessoas_estimadas),
             "b": None if pd.isna(r.bairros_atingidos) else int(r.bairros_atingidos),
             "med": r.origem == "medido", "n": None if pd.isna(r.pessoas_estimadas) else float(r.nivel_inct)}
            for r in h.itertuples()]


def bairros_inct() -> tuple[list[dict], dict]:
    inct = pd.read_csv(PROC / "inct_longo_limpo.csv")
    inct = inct[inct["nivel_m"] <= 5.4]
    por_chave = {chave(n): n for n in inct["bairro"].unique()}
    geos = []
    for f in le("bairros"):
        nome = por_chave[chave(f["properties"]["nome"])]  # KeyError aqui = nome sem correspondência
        g = make_valid(shape(f["geometry"])).simplify(0.0002)
        geos.append({"type": "Feature", "properties": {"nome": nome}, "geometry": geo(g, 1e-4)})
    assert len({f["properties"]["nome"] for f in geos}) == 94
    tabela = {b: {f"{n:.1f}": [int(p), float(pc)] for n, p, pc in zip(g["nivel_m"], g["affected_population"], g["percentage"])}
              for b, g in inct.groupby("bairro")}
    return geos, tabela


def grava_html(js: str) -> None:
    html = (RAIZ / "app" / "mapa_modelo.html").read_text(encoding="utf-8").replace("/*__DADOS__*/null", js)
    (RAIZ / "app" / "mapa.html").write_text(html, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html-only", action="store_true", help="Atualiza o HTML com o mapa_dados.json existente")
    args = parser.parse_args()
    if args.html_only:
        grava_html((PROC / "mapa_dados.json").read_text(encoding="utf-8"))
        raise SystemExit(0)
    geos, tabela = bairros_inct()
    dados = {"contornos": {"type": "FeatureCollection", "features": contornos()},
             "bairros": {"type": "FeatureCollection", "features": geos},
             "inct": tabela, "eventos": eventos(), "serie": serie()}
    assert [f["properties"]["cota"] for f in dados["contornos"]["features"]][-1] == 535
    assert max(s["cm"] for s in dados["serie"]) == 535
    js = json.dumps(dados, ensure_ascii=False, separators=(",", ":"))
    (PROC / "mapa_dados.json").write_text(js, encoding="utf-8")
    grava_html(js)
    print(f"mapa_dados.json: {len(js) / 1e6:.1f} MB")
