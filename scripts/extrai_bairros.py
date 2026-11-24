"""
Extrai os limites dos 94 bairros já embutidos no mapa de 2024 para um GeoJSON próprio da Tela 1.

Entrada: app/mapa.html (gerado por gera_mapa.py; nomes já na grafia do INCT)
Saída:   dados/processados/bairros.geojson
Uso:     python scripts/extrai_bairros.py

Fonte dos limites: camada BAIRROS do GIS da Prefeitura de Porto Alegre (SMAMUS), coletada em 09/11/2026
por coleta_prefeitura.py. Não há novo download: a geometria simplificada já está versionada no mapa.
"""
import json
from pathlib import Path

import pandas as pd
from shapely.geometry import MultiPolygon, mapping, shape
from shapely.geometry.polygon import orient

RAIZ = Path(__file__).resolve().parents[1]
MAPA = RAIZ / "app" / "mapa.html"
INCT = RAIZ / "dados" / "processados" / "inct_longo_limpo.csv"
SAIDA = RAIZ / "dados" / "processados" / "bairros.geojson"


def sentido_horario(geometria: dict) -> dict:
    """O mapa em SVG do Plotly (d3-geo) só preenche certo polígonos com contorno externo no sentido horário."""
    g = shape(geometria)
    partes = [orient(p, sign=-1.0) for p in getattr(g, "geoms", [g])]
    return mapping(partes[0] if g.geom_type == "Polygon" else MultiPolygon(partes))


def extrair(html: str) -> dict:
    """Lê o objeto de dados do mapa (começa em {"contornos") e devolve só a coleção de bairros."""
    inicio = html.find('{"contornos"')
    if inicio < 0:
        raise ValueError("Dados do mapa não encontrados no HTML.")
    dados, _ = json.JSONDecoder().raw_decode(html[inicio:])
    feicoes = [{"type": "Feature", "properties": {"nome": f["properties"]["nome"]},
                "geometry": sentido_horario(f["geometry"])} for f in dados["bairros"]["features"]]
    # passa por JSON para que tuplas virem listas, igual ao arquivo gravado
    return json.loads(json.dumps({"type": "FeatureCollection", "features": feicoes}))


def checar(bairros: dict, nomes_inct: set[str]) -> None:
    nomes = [f["properties"]["nome"] for f in bairros["features"]]
    assert len(nomes) == len(set(nomes)) == 94, "esperados 94 bairros sem repetição"
    assert set(nomes) == nomes_inct, f"nomes diferentes do INCT: {set(nomes) ^ nomes_inct}"


if __name__ == "__main__":
    bairros = extrair(MAPA.read_text(encoding="utf-8"))
    checar(bairros, set(pd.read_csv(INCT)["bairro"]))
    SAIDA.write_text(json.dumps(bairros, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(bairros['features'])} bairros em {SAIDA.name} ({SAIDA.stat().st_size / 1e3:.0f} KB)")
