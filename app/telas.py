"""Telas analíticas do dashboard. O mapa de 2024 vive em mapa.html."""

import plotly.graph_objects as go
import streamlit as st

from dados_dashboard import carregar_ana, carregar_inct, curva_inct, resumo_anual, resumo_inct


RIO = "#17313a"
AZUL = "#5f9fad"
AMARELO = "#f2c94c"


def estilo_grafico(fig: go.Figure, titulo: str, altura: int = 430) -> go.Figure:
    fig.update_layout(
        title=titulo, template="plotly_dark", height=altura,
        paper_bgcolor=RIO, plot_bgcolor=RIO, font={"family": "Arial", "color": "#eef2f0"},
        margin={"l": 12, "r": 20, "t": 64, "b": 28},
        hoverlabel={"bgcolor": RIO},
    )
    fig.update_xaxes(gridcolor="#34525b", zeroline=False)
    fig.update_yaxes(gridcolor="#34525b", zeroline=False)
    return fig


def tela_inct() -> None:
    st.title("Simulação do INCT SiMAI")
    st.caption("Se o Guaíba chegar a um determinado nível, qual seria o impacto estimado em Porto Alegre?")
    dados = carregar_inct()
    nivel = st.slider("Nível do Guaíba", min_value=3.0, max_value=10.0,
                      value=5.4, step=0.1, format="%.1f m")
    nivel = round(nivel, 1)
    bairros, totais = resumo_inct(dados, nivel)

    colunas = st.columns(3)
    for coluna, rotulo, valor in zip(colunas,
                                     ("Pessoas afetadas", "Prédios afetados", "Bairros atingidos"),
                                     (totais["pessoas"], totais["predios"], totais["bairros"])):
        coluna.metric(rotulo, f"{valor:,}".replace(",", "."))

    esquerda, direita = st.columns([1.8, 1], gap="large")
    with esquerda:
        ordenados = bairros.sort_values("percentage")
        fig = go.Figure(go.Bar(
            x=ordenados["percentage"], y=ordenados["bairro"], orientation="h",
            marker_color=AZUL, customdata=ordenados[["affected_buildings", "total_buildings"]],
            hovertemplate="%{y}: %{x:.2f}% dos prédios<br>%{customdata[0]:,.0f} de %{customdata[1]:,.0f} prédios<extra></extra>",
        ))
        estilo_grafico(fig, f"Prédios afetados por bairro a {nivel:.1f} m", max(450, len(ordenados) * 27 + 100))
        fig.update_xaxes(title="Prédios afetados (%)", range=[0, 100])
        fig.update_yaxes(title=None, automargin=True)
        with st.container(height=570, border=False):
            st.plotly_chart(fig, width="stretch", key="bairros_inct")
        st.caption(f"Todos os {len(ordenados)} bairros com pelo menos um prédio atingido estão no gráfico; role para ver a lista completa.")

    with direita:
        criterio = st.radio("Ranking por", ["Pessoas", "Prédios"], horizontal=True)
        coluna = "affected_population" if criterio == "Pessoas" else "affected_buildings"
        ranking = bairros.sort_values(coluna, ascending=False).head(10)
        tabela = ranking[["bairro", "affected_population", "affected_buildings", "percentage"]].copy()
        tabela.columns = ["Bairro", "Pessoas", "Prédios", "% dos prédios"]
        st.subheader("Bairros mais afetados")
        st.dataframe(tabela, hide_index=True, width="stretch",
                     column_config={"% dos prédios": st.column_config.NumberColumn(format="%.2f%%")})

    curva = curva_inct(dados)
    fig_curva = go.Figure(go.Scatter(
        x=curva["nivel_m"], y=curva["affected_population"], mode="lines",
        line={"color": AZUL, "width": 3}, fill="tozeroy", fillcolor="rgba(95,159,173,.18)",
        hovertemplate="%{x:.1f} m: %{y:,.0f} pessoas estimadas<extra></extra>",
    ))
    fig_curva.add_vline(x=5.35, line_color=AMARELO, line_dash="dash",
                         annotation_text="Recorde de 2024: 5,35 m", annotation_position="top left")
    fig_curva.add_vline(x=nivel, line_color="#eef2f0", line_width=1)
    estilo_grafico(fig_curva, "População afetada estimada por nível")
    fig_curva.update_xaxes(title="Nível do Guaíba (m)", range=[3, 10])
    fig_curva.update_yaxes(title="Pessoas estimadas")
    st.plotly_chart(fig_curva, width="stretch", key="curva_inct")

    st.info("Estimativas da simulação do INCT SiMAI, não previsões nem contagens da enchente real. "
            "A população afetada é estimada pela proporção de prédios atingidos; isso supõe distribuição "
            "uniforme de moradores, inclusive em prédios não residenciais. Inconsistências do JSON foram "
            "tratadas e documentadas no relatório de limpeza. O recorde de 5,35 m é uma referência de maio de 2024.")
    st.caption("Fonte dos indicadores e gráficos: JSON do INCT SiMAI fornecido pela disciplina, após limpeza local.")


def tela_historico() -> None:
    st.title("Histórico do Guaíba")
    st.caption("Com que frequência o Guaíba chega a níveis de inundação, e o que cada cheia representaria segundo a simulação do INCT?")
    st.markdown("[← Voltar ao mapa](?tela=enchente)")
    inct = carregar_inct()
    anuais = resumo_anual(carregar_ana(), inct)
    minimo, maximo = int(anuais["ano"].min()), int(anuais["ano"].max())
    inicio, fim = st.slider("Intervalo de anos", min_value=minimo, max_value=maximo,
                            value=(minimo, maximo), step=1)
    filtrados = anuais[anuais["ano"].between(inicio, fim)]
    anos = filtrados["ano"].astype(str)

    fig_dias = go.Figure(go.Bar(
        x=anos, y=filtrados["dias_acima_cota"], marker_color=AZUL,
        customdata=filtrados["dias_com_leitura"],
        hovertemplate="%{x}: %{y} dias acima da cota<br>%{customdata} dias com leitura<extra></extra>",
    ))
    estilo_grafico(fig_dias, "Dias acima da cota de inundação por ano")
    fig_dias.update_xaxes(title="Ano", type="category")
    fig_dias.update_yaxes(title="Dias com leitura acima da cota", rangemode="tozero")
    st.plotly_chart(fig_dias, width="stretch", key="dias_ana")
    st.caption("Cotas usadas na série processada: 3,00 m no Cais Mauá e 3,60 m na Usina do Gasômetro. "
               "Cada barra conta apenas os dias com leitura disponível.")

    esquerda, direita = st.columns(2, gap="large")
    with esquerda:
        fig_picos = go.Figure(go.Scatter(
            x=anos, y=filtrados["pico_m"], mode="lines+markers",
            line={"color": AZUL, "width": 2}, marker={"size": 9, "color": AMARELO},
            customdata=filtrados["estacao_pico"],
            hovertemplate="%{x}: %{y:.2f} m<br>Estação: %{customdata}<extra></extra>",
        ))
        fig_picos.add_hline(y=5.35, line_dash="dash", line_color=AMARELO)
        estilo_grafico(fig_picos, "Maior nível medido em cada ano")
        fig_picos.update_xaxes(title="Ano", type="category")
        fig_picos.update_yaxes(title="Nível (m)", rangemode="tozero")
        st.plotly_chart(fig_picos, width="stretch", key="picos_ana")

    with direita:
        com_estimativa = filtrados.dropna(subset=["pessoas_estimadas"])
        fig_pessoas = go.Figure(go.Bar(
            x=com_estimativa["ano"].astype(str), y=com_estimativa["pessoas_estimadas"],
            marker_color=AMARELO, customdata=com_estimativa["nivel_inct"],
            hovertemplate="%{x}: %{y:,.0f} pessoas estimadas<br>Nível usado no INCT: %{customdata:.1f} m<extra></extra>",
        ))
        estilo_grafico(fig_pessoas, "Pessoas estimadas no pico de cada ano")
        fig_pessoas.update_xaxes(title="Ano", type="category")
        fig_pessoas.update_yaxes(title="Pessoas estimadas", rangemode="tozero")
        st.plotly_chart(fig_pessoas, width="stretch", key="pessoas_picos")

    st.warning("A barra de pessoas é um cenário hipotético do INCT para o pico medido, não o número real "
               "de atingidos naquele ano. Para comparar, o nível é arredondado ao décimo mais próximo; "
               "abaixo de 3,0 m não há estimativa. Cais Mauá e Usina do Gasômetro têm referenciais "
               "diferentes e não foram ajustados entre si. Há lacunas nas leituras; dias sem dados não são contados.")
    st.markdown("Fonte dos níveis: [ANA, ServiceANA](https://telemetriaws1.ana.gov.br/ServiceANA.asmx) "
                "(coleta: 28/10/2026). Estimativas de pessoas: JSON do INCT SiMAI fornecido pela disciplina.")
