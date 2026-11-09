"""
Baixa as camadas públicas da enchente de 2024 no GIS da Prefeitura de Porto Alegre (SMAMUS).

Fonte: https://gis-smamus.portoalegre.rs.gov.br/server/rest/services/Hosted
Camadas: manchas de inundação de 3,00 a 5,35 m, cronologia de eventos e limites dos bairros.
Saídas: dados/originais/prefeitura/*.geojson (não baixa de novo o que já existe)
Uso: python scripts/coleta_prefeitura.py
"""
import json
import time
from pathlib import Path

import requests

BASE = "https://gis-smamus.portoalegre.rs.gov.br/server/rest/services/Hosted"
PASTA = Path(__file__).resolve().parents[1] / "dados" / "originais" / "prefeitura"
CAMADAS = {"cotas": "Cotas_inunda_300_535_cronologia", "eventos": "cronologia_cheia24", "bairros": "BAIRROS"}


def consulta(camada: str, **extra) -> dict:
    params = {"outFields": "*", "returnGeometry": "true", "outSR": 4326, "f": "geojson", **extra}
    r = requests.get(f"{BASE}/{camada}/FeatureServer/0/query", params=params, timeout=300)
    r.raise_for_status()
    time.sleep(1)  # coleta responsável
    return r.json()


def baixar_cotas() -> None:
    """Uma requisição por polígono: juntos eles passam do limite de resposta do servidor."""
    destino = PASTA / "cotas.geojson"
    if destino.exists():
        return
    ids = requests.get(f"{BASE}/{CAMADAS['cotas']}/FeatureServer/0/query",
                       params={"where": "1=1", "returnIdsOnly": "true", "f": "json"}, timeout=60).json()
    feicoes = []
    for oid in ids.get("objectIds") or ids["properties"]["objectIds"]:
        feicoes += consulta(CAMADAS["cotas"], objectIds=oid)["features"]
    assert len(feicoes) == 25
    destino.write_text(json.dumps({"type": "FeatureCollection", "features": feicoes}), encoding="utf-8")


if __name__ == "__main__":
    PASTA.mkdir(parents=True, exist_ok=True)
    baixar_cotas()
    for nome in ("eventos", "bairros"):
        if not (PASTA / f"{nome}.geojson").exists():
            dados = consulta(CAMADAS[nome], where="1=1")
            assert not dados.get("exceededTransferLimit")
            (PASTA / f"{nome}.geojson").write_text(json.dumps(dados), encoding="utf-8")
    print("Camadas em", PASTA)
