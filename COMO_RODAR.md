# Como rodar

Rodar sempre **a partir da raiz do repositório**. Dashboard publicado: <https://guaiba-poa.streamlit.app/>

## Só abrir o dashboard

Os dados processados já estão versionados em `dados/processados/` e `app/mapa.html`, então basta:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app/app.py
```

O app abre em <http://localhost:8501>. Telas:

- **Simulação INCT** (`?tela=inct`): o controle de 3,0 a 10,0 m atualiza pessoas, prédios e bairros atingidos, o mapa dos bairros colorido pela % de prédios afetados, o ranking, as barras por bairro e as curvas da população afetada (cidade toda e um bairro escolhido). Usa apenas `dados/processados/inct_longo_limpo.csv` e os limites de `dados/processados/bairros.geojson`.
- **Enchente 2024** (`?tela=enchente`, página inicial): mapa da enchente de maio de 2024, hora a hora, com a mancha da Prefeitura, o nível da ANA e as estimativas do INCT.
- **Histórico** (`?tela=enchente&painel=historico`): série diária da ANA desde 2014, com filtro de anos, dias acima da cota, picos anuais e a estimativa do INCT para cada pico (hipotética).

## Refazer tudo do zero

### 1. Colocar o JSON do INCT

Copie o arquivo fornecido pela disciplina para `dados/originais/inct/dados.json`.

### 2. Coletar

```bash
python scripts/coletar_tudo.py
```

Ou cada base separadamente:

| Script | Base | Como coleta | Saída |
|---|---|---|---|
| `scripts/coleta_ana.py` | Nível do Guaíba — ANA (Cais Mauá 87450004 e Usina do Gasômetro 87444000) | Web service público (XML) | `dados/originais/ana/` |
| `scripts/coleta_prefeitura.py` | Mancha por cota, bairros, eventos de 2024 e escolas (INEP) — GIS da Prefeitura (SMAMUS/DMAE) | ArcGIS FeatureServer público | `dados/originais/prefeitura/` |
| `scripts/carrega_inct.py` | Simulação do INCT SiMAI | Leitura do JSON + diagnóstico | `dados/processados/inct_longo_bruto.csv` |

Os scripts **não baixam de novo** o que já existe em `dados/originais/` (coleta responsável).

### 3. Limpar e processar

```bash
python scripts/limpa_inct.py       # dados/processados/inct_longo_limpo.csv
python scripts/processa_ana.py     # dados/processados/ana_diario.csv e enchente_2024_horario.csv
python scripts/gera_mapa.py        # dados/processados/mapa_dados.json e app/mapa.html
python scripts/extrai_bairros.py   # dados/processados/bairros.geojson (mapa da Tela 1)
```

Para atualizar só a contagem de escolas por bairro e cota, sem refazer os contornos grandes: `python scripts/gera_mapa.py --schools-only`.

### 4. Testes

```bash
python -m unittest discover -s tests -p 'test_*.py'
node --test tests/mapa.test.cjs
```

## Fontes usadas no mapa interativo

O mapa usa a série horária processada da ANA para avançar a linha do tempo. A mancha em cada cota, os limites dos bairros e a cronologia dos eventos vêm das camadas públicas do GIS da Prefeitura. O JSON do INCT SiMAI, fornecido pela disciplina, entra nas estimativas de pessoas e prédios atingidos e nos valores mostrados por bairro. Ele não contém o desenho da mancha exibida no mapa. A foto aérea da Esri e os prédios vetoriais do OpenFreeMap são camadas visuais de fundo, não medições da enchente.

As camadas da Prefeitura são polígonos por cota. Assim, a aparência da água no mapa não calcula a passagem entre cada prédio, nem modela o efeito de diques, comportas ou água retida durante a descida. O número de escolas no hover é contado ao cruzar os pontos da camada [Escolas_INEP_SCRPOA](https://gis-smamus.portoalegre.rs.gov.br/server/rest/services/Hosted/Escolas_INEP_SCRPOA/FeatureServer/0) com os bairros oficiais e com a mancha exibida em cada cota. É uma estimativa de **escolas dentro da área simulada**, não uma lista de escolas que sofreram danos reais em 2024. A data da coleta fica em `dados/originais/prefeitura/escolas_meta.json` e no rodapé do mapa.

## O que sabemos sobre os dados da ANA

- A estação **Cais Mauá C6 (87450004)** não tem série convencional no HidroWeb (o .zip vem vazio); só **telemetria**, desde 2014, com leituras a cada 15 min.
- Ela **parou em 02/05/2024 às 23h15, com 3,69 m**, durante a enchente.
- A estação **Usina do Gasômetro (87444000)** começa em **03/05/2024 às 15h** e registra o pico de **5,35 m em 05/05/2024 às 5h30**.
- Entre as duas há uma **lacuna de cerca de 18 h** (interpolada na série processada), e os **referenciais são diferentes** (nota ANA/SGB: correção de 1,18 m, **não aplicada**). Cota de inundação: 3,00 m no Cais Mauá, 3,60 m no Gasômetro.
- O tratamento de cada ponto está em `relatorios/limpeza_dados.pdf`.
