"""
Baixa as camadas públicas da enchente de 2024 no GIS da Prefeitura de Porto Alegre (SMAMUS).

Fonte: https://gis-smamus.portoalegre.rs.gov.br/server/rest/services/Hosted
Camadas: manchas de inundação de 3,00 a 5,35 m, cronologia de eventos,
limites dos bairros e localização de escolas da camada Escolas_INEP_SCRPOA.
Saídas: dados/originais/prefeitura/*.geojson (não baixa de novo o que já existe)
Uso: python scripts/coleta_prefeitura.py
"""
import json
import time
from datetime import date
from pathlib import Path

import requests

BASE = "https://gis-smamus.portoalegre.rs.gov.br/server/rest/services/Hosted"
PASTA = Path(__file__).resolve().parents[1] / "dados" / "originais" / "prefeitura"
CAMADAS = {"cotas": "Cotas_inunda_300_535_cronologia", "eventos": "cronologia_cheia24",
           "bairros": "BAIRROS", "escolas": "Escolas_INEP_SCRPOA"}


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


def baixar_escolas() -> None:
    """Baixa todos os pontos por ID para não depender do limite de 2.000 feições."""
    destino = PASTA / "escolas.geojson"
    meta_destino = PASTA / "escolas_meta.json"
    if destino.exists() and meta_destino.exists():
        return
    camada = CAMADAS["escolas"]
    url = f"{BASE}/{camada}/FeatureServer/0"
    resposta = requests.get(f"{url}/query", params={"where": "1=1", "returnIdsOnly": "true", "f": "json"}, timeout=60)
    resposta.raise_for_status()
    bruto = resposta.json()
    ids = bruto.get("objectIds") or bruto.get("properties", {}).get("objectIds")
    if not ids:
        raise ValueError(f"A camada de escolas não retornou IDs: {bruto}")
    feicoes = []
    for i in range(0, len(ids), 400):
        parte = consulta(camada, objectIds=",".join(map(str, ids[i:i + 400])))
        if parte.get("type") != "FeatureCollection" or parte.get("exceededTransferLimit"):
            raise ValueError("Resposta incompleta da camada de escolas")
        feicoes.extend(parte["features"])
    if len(feicoes) != len(ids):
        raise ValueError(f"Escolas recebidas: {len(feicoes)} de {len(ids)} IDs")
    if not all(f.get("geometry", {}).get("type") == "Point" for f in feicoes):
        raise ValueError("A camada de escolas retornou geometria diferente de ponto")
    destino.write_text(json.dumps({"type": "FeatureCollection", "features": feicoes}, ensure_ascii=False), encoding="utf-8")
    meta_destino.write_text(json.dumps({"fonte": url, "coleta": date.today().isoformat(),
                                        "registros": len(feicoes)}, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    PASTA.mkdir(parents=True, exist_ok=True)
    baixar_cotas()
    baixar_escolas()
    for nome in ("eventos", "bairros"):
        if not (PASTA / f"{nome}.geojson").exists():
            dados = consulta(CAMADAS[nome], where="1=1")
            assert not dados.get("exceededTransferLimit")
            (PASTA / f"{nome}.geojson").write_text(json.dumps(dados), encoding="utf-8")
    print("Camadas em", PASTA)
