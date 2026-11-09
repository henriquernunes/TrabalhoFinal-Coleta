# Coleta dos dados — como rodar

Scripts de coleta das bases escolhidas na Fase 1. Rodar sempre **a partir da raiz do repositório**.

## 1. Preparar o ambiente

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Colocar o JSON do INCT

Copie o arquivo fornecido pela disciplina para:

```
dados/originais/inct/dados.json
```

## 3. Coletar tudo

```bash
python scripts/coletar_tudo.py            # rápido, sem o arquivo grande da mancha
python scripts/coletar_tudo.py --gpkg     # inclui a mancha de inundação de 2024 (centenas de MB)
```

Ou cada base separadamente:

| Script | Base | Como coleta | Saída |
|---|---|---|---|
| `scripts/coleta_ana.py` | Nível do Guaíba — ANA (Cais Mauá 87450004 e Usina do Gasômetro 87444000) | API (web service público, XML) | `dados/originais/ana/` |
| `scripts/coleta_prefeitura.py` | Mancha por cota, limites dos bairros e eventos — GIS da Prefeitura de Porto Alegre (SMAMUS/DMAE) | ArcGIS FeatureServer público | `dados/originais/prefeitura/` |
| `scripts/coleta_observapoa.py` | Limites e população dos bairros — ObservaPOA | Web scraping da página de mapas | `dados/originais/observapoa/` |
| `scripts/coleta_zenodo.py` | Cheias de maio/2024 — UFRGS (Zenodo) | API REST do Zenodo | `dados/originais/zenodo/` |
| `scripts/carrega_inct.py` | Simulação do INCT SiMAI | Leitura do JSON + diagnóstico | `dados/processados/inct_longo_bruto.csv` |

Os scripts **não baixam de novo** o que já existe em `dados/originais/` (coleta responsável).
Para gerar o mapa interativo, execute `python scripts/coleta_prefeitura.py` separadamente; essa coleta ainda não faz parte de `coletar_tudo.py`.

## Fontes usadas no mapa interativo

O mapa usa a série horária processada da ANA para avançar a linha do tempo. A mancha em cada cota, os limites dos bairros e a cronologia dos eventos vêm das camadas públicas do GIS da Prefeitura. O JSON do INCT SiMAI, fornecido pela disciplina, entra nas estimativas de pessoas e prédios atingidos e nos valores mostrados por bairro. Ele não contém o desenho da mancha exibida no mapa. A foto aérea da Esri e os prédios vetoriais do OpenFreeMap são camadas visuais de fundo, não medições da enchente.

As camadas da Prefeitura são polígonos por cota. Assim, a aparência da água no mapa não calcula a passagem entre cada prédio, nem modela o efeito de diques, comportas ou água retida durante a descida.

## O que já sabemos sobre os dados da ANA

- A estação **Cais Mauá C6 (87450004)** não tem série convencional no HidroWeb (o .zip vem vazio); só **telemetria**, desde 2014, com leituras a cada 15 min.
- Ela **parou em 02/05/2024 às 23h15, com 3,69 m**, durante a enchente.
- A estação **Usina do Gasômetro (87444000)** começa em **03/05/2024 às 15h** e registra o pico de **5,35 m em 05/05/2024 às 5h30**.
- Entre as duas há um **buraco de ~16 h**, e os **referenciais são diferentes** (nota ANA/SGB: correção de 1,18 m, ainda **não aplicada** nos dados servidos). Cota de inundação: 3,00 m no Cais Mauá, 3,60 m no Gasômetro.
- Esses pontos vão para o relatório de limpeza (Fase 2).

## Arquivos grandes

O `.gpkg` do Zenodo não deve ir para o GitHub (limite de 100 MB). Ele está no `.gitignore`; quem clonar o repositório baixa rodando o script.
