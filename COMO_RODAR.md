# Coleta dos dados — como rodar

Scripts de coleta das bases escolhidas na Fase 1. Rodar sempre **a partir da raiz do repositório**.

## Dashboard em duas telas

```bash
.venv/bin/streamlit run app/app.py
```

- **Simulação INCT:** abra `?tela=inct`. O controle de 3,0 a 10,0 m atualiza pessoas, prédios, bairros, gráfico por bairro, ranking e curva da população. Essa tela usa apenas `dados/processados/inct_longo_limpo.csv`, derivado do JSON do INCT.
- **Enchente de 2024:** a página inicial mantém o mapa existente. O link **Histórico** abre o painel analítico da mesma tela, com três gráficos da ANA e filtro de anos. As estimativas de pessoas nesses gráficos vêm do INCT e são hipotéticas.

Testes de regressão: `.venv/bin/python -m unittest discover -s tests -p 'test_*.py'` e `node --test`.

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
python scripts/coletar_tudo.py
```

Ou cada base separadamente:

| Script | Base | Como coleta | Saída |
|---|---|---|---|
| `scripts/coleta_ana.py` | Nível do Guaíba — ANA (Cais Mauá 87450004 e Usina do Gasômetro 87444000) | API (web service público, XML) | `dados/originais/ana/` |
| `scripts/coleta_prefeitura.py` | Mancha por cota, limites dos bairros e eventos — GIS da Prefeitura de Porto Alegre (SMAMUS/DMAE) | ArcGIS FeatureServer público | `dados/originais/prefeitura/` |
| `scripts/carrega_inct.py` | Simulação do INCT SiMAI | Leitura do JSON + diagnóstico | `dados/processados/inct_longo_bruto.csv` |

Os scripts **não baixam de novo** o que já existe em `dados/originais/` (coleta responsável).
A coleta da Prefeitura também baixa a camada pública de escolas georreferenciadas da Prefeitura, derivada do cadastro INEP.

Depois de baixar as escolas, atualize os números por bairro e cota sem refazer os contornos grandes:

```bash
python scripts/gera_mapa.py --schools-only
```

## Fontes usadas no mapa interativo

O mapa usa a série horária processada da ANA para avançar a linha do tempo. A mancha em cada cota, os limites dos bairros e a cronologia dos eventos vêm das camadas públicas do GIS da Prefeitura. O JSON do INCT SiMAI, fornecido pela disciplina, entra nas estimativas de pessoas e prédios atingidos e nos valores mostrados por bairro. Ele não contém o desenho da mancha exibida no mapa. A foto aérea da Esri e os prédios vetoriais do OpenFreeMap são camadas visuais de fundo, não medições da enchente.

As camadas da Prefeitura são polígonos por cota. Assim, a aparência da água no mapa não calcula a passagem entre cada prédio, nem modela o efeito de diques, comportas ou água retida durante a descida. O número de escolas no hover é contado ao cruzar os pontos da camada [Escolas_INEP_SCRPOA](https://gis-smamus.portoalegre.rs.gov.br/server/rest/services/Hosted/Escolas_INEP_SCRPOA/FeatureServer/0) com os bairros oficiais e com a mancha exibida em cada cota. É uma estimativa de **escolas dentro da área simulada**, não uma lista de escolas que sofreram danos reais em 2024. A data da coleta fica em `dados/originais/prefeitura/escolas_meta.json` e no rodapé do mapa.

## O que já sabemos sobre os dados da ANA

- A estação **Cais Mauá C6 (87450004)** não tem série convencional no HidroWeb (o .zip vem vazio); só **telemetria**, desde 2014, com leituras a cada 15 min.
- Ela **parou em 02/05/2024 às 23h15, com 3,69 m**, durante a enchente.
- A estação **Usina do Gasômetro (87444000)** começa em **03/05/2024 às 15h** e registra o pico de **5,35 m em 05/05/2024 às 5h30**.
- Entre as duas há um **buraco de ~16 h**, e os **referenciais são diferentes** (nota ANA/SGB: correção de 1,18 m, ainda **não aplicada** nos dados servidos). Cota de inundação: 3,00 m no Cais Mauá, 3,60 m no Gasômetro.
- Esses pontos vão para o relatório de limpeza (Fase 2).
