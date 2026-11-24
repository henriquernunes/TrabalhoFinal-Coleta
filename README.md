# Enchentes em Porto Alegre — dashboard com a simulação do INCT SiMAI

Trabalho final da disciplina **Coleta, Preparação e Análise de Dados** (PUCRS, 2026/2), com a Profª Katherine Bianchini Esper de Vargas.

O objetivo é um dashboard com duas telas:

1. **Simulação INCT:** usa apenas o JSON do INCT, já limpo. Mostra o que a simulação estima para cada nível do Guaíba, de 3,0 a 10,0 m.
2. **Enchente de 2024:** mapa navegável da cheia de maio de 2024 e histórico do nível do Guaíba, ligando as bases externas à simulação.

Os números de pessoas e prédios são **estimativas de simulação**, não previsões nem contagens oficiais.

## Equipe

| Nome | GitHub |
|---|---|
| Henrique Nunes | [@henriquernunes](https://github.com/henriquernunes) |
| Jayme Fortes | [@JaymeFortes](https://github.com/JaymeFortes) |

## Dashboard

Link público: <https://guaiba-poa.streamlit.app/>

## Bases de dados

| Base | Como é obtida | Script |
|---|---|---|
| Simulação do INCT SiMAI (JSON fornecido pela disciplina) | Arquivo copiado para `dados/originais/inct/dados.json` | `scripts/carrega_inct.py`, `scripts/limpa_inct.py` |
| Nível do Guaíba — ANA, estações Cais Mauá C6 (`87450004`) e Usina do Gasômetro (`87444000`) | Web service público de telemetria (XML) | `scripts/coleta_ana.py`, `scripts/processa_ana.py` |
| Mancha por cota, bairros, eventos de 2024 e escolas — GIS da Prefeitura de Porto Alegre (SMAMUS/DMAE) | ArcGIS FeatureServer público | `scripts/coleta_prefeitura.py`, `scripts/gera_mapa.py` |

Os dados brutos ficam em `dados/originais/` e os dados limpos em `dados/processados/`. Os scripts não baixam de novo o que já existe.

## Como rodar

Execute tudo a partir da raiz do repositório.

1. Prepare o ambiente:
   ```bash
   python -m venv .venv
   source .venv/bin/activate          # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Copie o JSON do INCT para `dados/originais/inct/dados.json`.
3. Colete as bases:
   ```bash
   python scripts/coletar_tudo.py
   ```
4. Limpe e processe os dados:
   ```bash
   python scripts/limpa_inct.py
   python scripts/processa_ana.py
   python scripts/gera_mapa.py
   ```
5. Abra o dashboard:
   ```bash
   streamlit run app/app.py
   ```

Mais detalhes sobre cada script e sobre as fontes do mapa estão em [`COMO_RODAR.md`](COMO_RODAR.md).

## Estrutura

```
├── app/          # dashboard (Streamlit) e mapa interativo
├── dados/
│   ├── originais/    # dados como vieram das fontes
│   └── processados/  # dados limpos usados pelo dashboard
├── notebooks/    # análise exploratória (eda.ipynb)
├── relatorios/   # relatórios de cada fase
├── scripts/      # coleta, limpeza e geração do mapa
└── tests/        # testes de regressão
```

## Relatórios

- `relatorios/base_dados.pdf` — levantamento das bases (Fase 1).
- `relatorios/limpeza_dados.pdf` — limpeza dos dados (fonte LaTeX em `relatorios/limpeza_dados.tex`).
- `relatorios/wireframe.png` — esboço das duas telas (Fase 2).
- `relatorios/dashboard.pdf` — objetivo de cada tela, visualizações, como usar e limitações (fonte LaTeX em `relatorios/dashboard.tex`).

## Uso de IA

| Ferramenta | Onde foi usada | Como foi usada |
|---|---|---|
| Claude Code (Anthropic) | Scripts de coleta e limpeza | Apoio para escrever e testar os scripts e para investigar as inconsistências do JSON do INCT e da série da ANA. As decisões de tratamento foram revisadas pela equipe. |
| Claude Code (Anthropic) | Mapa e dashboard | Apoio para escrever o código do mapa (MapLibre) e das telas em Streamlit, e os testes. |
| Claude Code (Anthropic) | Relatório de limpeza | Rascunho do texto em LaTeX, revisado e editado pela equipe no Overleaf. |
| Claude Code (Anthropic) | Relatório do dashboard (Fase 3 e versão final) | Rascunho do texto em LaTeX a partir do código das telas, revisado e editado pela equipe no Overleaf. |
