"""
Roda todas as coletas em sequência. Cada script guarda os dados brutos em dados/originais/
e não baixa de novo o que já existe, então pode ser executado várias vezes.

Uso (a partir da raiz do repositório):
  python scripts/coletar_tudo.py
"""
import subprocess
import sys
from pathlib import Path

PASTA = Path(__file__).resolve().parent
ETAPAS = [
    ("Níveis do Guaíba (ANA)", ["coleta_ana.py"]),
    ("Mancha, bairros, eventos e escolas (Prefeitura)", ["coleta_prefeitura.py"]),
    ("Simulação do INCT", ["carrega_inct.py"]),
]

falhas = []
for titulo, comando in ETAPAS:
    print(f"\n{'=' * 60}\n{titulo}\n{'=' * 60}")
    resultado = subprocess.run([sys.executable, str(PASTA / comando[0]), *comando[1:]])
    if resultado.returncode != 0:
        falhas.append(titulo)

print("\nResumo:", "tudo certo." if not falhas else f"falharam: {', '.join(falhas)}")
