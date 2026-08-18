import sqlite3
import os
import io
import subprocess
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import database_etl

DB_NAME = "b3_investimentos.db"
APP_VERSION = "v1.2.0"

def get_git_commit_hash():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode("utf-8").strip()
    except Exception:
        return "main"

GIT_COMMIT = get_git_commit_hash()

# Streamlit Page Setup
st.set_page_config(
    page_title="Dashboard Financeiro B3",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    /* Metric Cards */
    .metric-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        text-align: center;
        margin-bottom: 15px;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #94a3b8;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #f8fafc;
        margin-top: 5px;
    }
    .metric-delta-pos {
        color: #10b981;
        font-weight: 600;
        font-size: 1rem;
    }
    .metric-delta-neg {
        color: #ef4444;
        font-weight: 600;
        font-size: 1rem;
    }
    
    /* Headers & Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #0f172a;
        border-radius: 8px 8px 0 0;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
        padding-left: 20px;
        padding-right: 20px;
        font-weight: 600;
    }
    .version-badge {
        background-color: #1e293b;
        color: #38bdf8;
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: bold;
        border: 1px solid #334155;
    }
</style>
""", unsafe_allow_html=True)

# Database Helper Functions
def get_db_connection():
    if not os.path.exists(DB_NAME):
        database_etl.process_and_load_data()
    return sqlite3.connect(DB_NAME)

@st.cache_data(ttl=60)
def load_versions():
    conn = get_db_connection()
    df = pd.read_sql("SELECT * FROM versoes_dados ORDER BY id DESC", conn)
    conn.close()
    return df

@st.cache_data(ttl=60)
def load_ativos(versao_id):
    conn = get_db_connection()
    df = pd.read_sql("SELECT * FROM ativos WHERE versao_id = ?", conn, params=(versao_id,))
    conn.close()
    return df

@st.cache_data(ttl=60)
def load_rendimentos(versao_id):
    conn = get_db_connection()
    df = pd.read_sql("SELECT * FROM rendimentos WHERE versao_id = ?", conn, params=(versao_id,))
    conn.close()
    return df

@st.cache_data(ttl=60)
def load_transacoes(versao_id):
    conn = get_db_connection()
    df = pd.read_sql("SELECT * FROM transacoes WHERE versao_id = ?", conn, params=(versao_id,))
    conn.close()
    return df

# Ensure DB exists
if not os.path.exists(DB_NAME):
    with st.spinner("Inicializando Banco de Dados e Importando Planilha B3..."):
        database_etl.process_and_load_data()

# Sidebar Navigation & Controls
st.sidebar.image("https://img.icons8.com/color/96/bullish.png", width=70)
st.sidebar.title("B3 Investimentos")
st.sidebar.markdown(f"**Versão do Sistema:** <span class='version-badge'>{APP_VERSION}</span> `#{GIT_COMMIT}`", unsafe_allow_html=True)
st.sidebar.markdown("---")

df_versions = load_versions()
selected_version_id = 1
if not df_versions.empty:
    selected_version_id = df_versions.iloc[0]['id']

# Re-run ETL button
if st.sidebar.button("🔄 Atualizar Cotações / Re-importar ETL", use_container_width=True):
    with st.spinner("Re-importando dados e atualizando cotações via yfinance..."):
        database_etl.process_and_load_data()
        st.cache_data.clear()
        st.sidebar.success("Cotações atualizadas com sucesso!")
        st.rerun()

st.sidebar.markdown("---")

# Fetch Data for Selected Version
df_ativos = load_ativos(selected_version_id)
df_rendimentos = load_rendimentos(selected_version_id)
df_transacoes = load_transacoes(selected_version_id)

# Export Buttons in Sidebar
st.sidebar.subheader("📥 Exportar Carteira")
if not df_ativos.empty:
    csv_data = df_ativos.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button(
        label="📄 Exportar CSV",
        data=csv_data,
        file_name=f"relatorio_b3_carteira.csv",
        mime="text/csv",
        use_container_width=True
    )

    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        df_ativos.to_excel(writer, sheet_name='Ativos', index=False)
        df_rendimentos.to_excel(writer, sheet_name='Rendimentos', index=False)
        df_transacoes.to_excel(writer, sheet_name='Transações', index=False)
    excel_data = excel_buffer.getvalue()

    st.sidebar.download_button(
        label="📊 Exportar Excel (.xlsx)",
        data=excel_data,
        file_name=f"carteira_b3.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

st.sidebar.markdown("---")
st.sidebar.caption(f"💡 **Dashboard B3 {APP_VERSION}** (`git #{GIT_COMMIT}`)\nPython | Pandas | SQLite | Streamlit")

# Main Title & Header
st.title("📈 Dashboard Interativo Financeiro B3")

# Top KPI Summary Cards
if not df_ativos.empty:
    patrimonio_total = df_ativos['valor_atual'].sum()
    total_investido = df_ativos['valor_investido'].sum()
    lucro_total = df_ativos['lucro_prejuizo_rs'].sum()
    rentabilidade_geral = ((patrimonio_total - total_investido) / total_investido * 100) if total_investido > 0 else 0.0
    total_proventos = df_rendimentos['valor_total'].sum() if not df_rendimentos.empty else 0.0

    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    
    with kpi1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Patrimônio Atual</div>
            <div class="metric-value">R$ {patrimonio_total:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
        
    with kpi2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Investido</div>
            <div class="metric-value">R$ {total_investido:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi3:
        color_cls = "metric-delta-pos" if lucro_total >= 0 else "metric-delta-neg"
        signal = "+" if lucro_total >= 0 else ""
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Lucro / Prejuízo R$</div>
            <div class="metric-value {color_cls}">{signal}R$ {lucro_total:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi4:
        color_cls = "metric-delta-pos" if rentabilidade_geral >= 0 else "metric-delta-neg"
        signal = "+" if rentabilidade_geral >= 0 else ""
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Rentabilidade Geral</div>
            <div class="metric-value {color_cls}">{signal}{rentabilidade_geral:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Proventos Recebidos</div>
            <div class="metric-value" style="color: #38bdf8;">R$ {total_proventos:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# Main Navigation Tabs (4 Tabs)
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Preço Médio vs. Cotação Atual",
    "🚀 Top 5 Melhores Ativos",
    "📉 Top 5 Piores Ativos",
    "💰 Rendimentos & Provendos"
])

# ==========================================
# TAB 1: PREÇO MÉDIO VS COTAÇÃO ATUAL
# ==========================================
with tab1:
    st.header("📊 Relatório: Preço Médio vs. Cotação Atual")
    
    col_f1, col_f2 = st.columns([2, 1])
    with col_f1:
        search_ticker = st.text_input("🔍 Pesquisar Ativo (Ticker ou Nome):", "").strip().upper()
    with col_f2:
        tipos_disponiveis = ["Todos"] + sorted(df_ativos['tipo_ativo'].unique().tolist())
        selected_tipo = st.selectbox("🏷️ Filtrar por Classe de Ativo:", tipos_disponiveis)

    # Filter Dataframe
    df_filtered = df_ativos.copy()
    if search_ticker:
        df_filtered = df_filtered[
            df_filtered['ticker'].str.contains(search_ticker, case=False) |
            df_filtered['nome_produto'].str.contains(search_ticker, case=False)
        ]
    if selected_tipo != "Todos":
        df_filtered = df_filtered[df_filtered['tipo_ativo'] == selected_tipo]

    # Format Table for Display
    display_df = df_filtered[[
        'ticker', 'nome_produto', 'tipo_ativo', 'quantidade_atual', 
        'preco_medio', 'cotacao_atual', 'valor_investido', 
        'valor_atual', 'lucro_prejuizo_rs', 'rentabilidade_pct'
    ]].copy()

    display_df.columns = [
        'Ticker', 'Nome do Produto', 'Classe', 'Qtd', 
        'Preço Médio (R$)', 'Cotação Atual (R$)', 'Total Investido (R$)', 
        'Valor Atual (R$)', 'Lucro/Prejuízo (R$)', 'Rentabilidade (%)'
    ]

    st.dataframe(
        display_df.style.format({
            'Preço Médio (R$)': 'R$ {:,.2f}',
            'Cotação Atual (R$)': 'R$ {:,.2f}',
            'Total Investido (R$)': 'R$ {:,.2f}',
            'Valor Atual (R$)': 'R$ {:,.2f}',
            'Lucro/Prejuízo (R$)': 'R$ {:,.2f}',
            'Rentabilidade (%)': '{:+.2f}%'
        }).map(
            lambda v: 'color: #10b981; font-weight: bold;' if v > 0 else ('color: #ef4444; font-weight: bold;' if v < 0 else ''),
            subset=['Lucro/Prejuízo (R$)', 'Rentabilidade (%)']
        ),
        use_container_width=True,
        height=400
    )

    st.markdown("---")
    st.subheader("Visualização Gráfica: Preço Médio vs. Cotação Atual por Ativo")

    if not df_filtered.empty:
        fig_pm_cot = go.Figure()
        fig_pm_cot.add_trace(go.Bar(
            x=df_filtered['ticker'],
            y=df_filtered['preco_medio'],
            name='Preço Médio (R$)',
            marker_color='#6366f1'
        ))
        fig_pm_cot.add_trace(go.Bar(
            x=df_filtered['ticker'],
            y=df_filtered['cotacao_atual'],
            name='Cotação Atual (R$)',
            marker_color='#14b8a6'
        ))
        fig_pm_cot.update_layout(
            barmode='group',
            xaxis_title="Ativo (Ticker)",
            yaxis_title="Preço em R$",
            template="plotly_dark",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=20, r=20, t=50, b=20)
        )
        st.plotly_chart(fig_pm_cot, use_container_width=True)


# ==========================================
# TAB 2: TOP 5 MELHORES ATIVOS
# ==========================================
with tab2:
    st.header("🚀 TOP 5 MELHORES ATIVOS")
    st.caption("Ativos com maior rentabilidade percentual (%) na carteira consolidada.")

    top5_best = df_ativos.sort_values(by='rentabilidade_pct', ascending=False).head(5)

    if not top5_best.empty:
        best_1 = top5_best.iloc[0]
        st.success(f"🏆 **Maior Destaque:** {best_1['ticker']} com valorização de **+{best_1['rentabilidade_pct']:.2f}%** (Lucro de R$ {best_1['lucro_prejuizo_rs']:,.2f})")

        c1, c2 = st.columns([1.2, 1])

        with c1:
            display_top5 = top5_best[[
                'ticker', 'nome_produto', 'tipo_ativo', 'quantidade_atual',
                'preco_medio', 'cotacao_atual', 'lucro_prejuizo_rs', 'rentabilidade_pct'
            ]].copy()
            display_top5.columns = [
                'Ticker', 'Produto', 'Classe', 'Qtd', 'Preço Médio (R$)',
                'Cotação (R$)', 'Lucro (R$)', 'Rentabilidade (%)'
            ]

            st.dataframe(
                display_top5.style.format({
                    'Preço Médio (R$)': 'R$ {:,.2f}',
                    'Cotação (R$)': 'R$ {:,.2f}',
                    'Lucro (R$)': 'R$ {:,.2f}',
                    'Rentabilidade (%)': '+{:,.2f}%'
                }).map(
                    lambda v: 'color: #10b981; font-weight: bold;',
                    subset=['Lucro (R$)', 'Rentabilidade (%)']
                ),
                use_container_width=True
            )

        with c2:
            fig_best = px.bar(
                top5_best,
                x='rentabilidade_pct',
                y='ticker',
                orientation='h',
                text='rentabilidade_pct',
                color='rentabilidade_pct',
                color_continuous_scale='Greens',
                title="Top 5 - Valorização (%)"
            )
            fig_best.update_traces(texttemplate='+%{text:.2f}%', textposition='outside')
            fig_best.update_layout(
                yaxis=dict(autorange="reversed"),
                xaxis_title="Rentabilidade (%)",
                yaxis_title="Ativo",
                template="plotly_dark",
                coloraxis_showscale=False
            )
            st.plotly_chart(fig_best, use_container_width=True)


# ==========================================
# TAB 3: TOP 5 PIORES ATIVOS
# ==========================================
with tab3:
    st.header("📉 TOP 5 PIORES ATIVOS")
    st.caption("Ativos com menor desempenho/maior desvalorização percentual (%) na carteira.")

    top5_worst = df_ativos.sort_values(by='rentabilidade_pct', ascending=True).head(5)

    if not top5_worst.empty:
        worst_1 = top5_worst.iloc[0]
        st.error(f"⚠️ **Maior Queda:** {worst_1['ticker']} com desvalorização de **{worst_1['rentabilidade_pct']:.2f}%** (Perda de R$ {worst_1['lucro_prejuizo_rs']:,.2f})")

        c1, c2 = st.columns([1.2, 1])

        with c1:
            display_worst5 = top5_worst[[
                'ticker', 'nome_produto', 'tipo_ativo', 'quantidade_atual',
                'preco_medio', 'cotacao_atual', 'lucro_prejuizo_rs', 'rentabilidade_pct'
            ]].copy()
            display_worst5.columns = [
                'Ticker', 'Produto', 'Classe', 'Qtd', 'Preço Médio (R$)',
                'Cotação (R$)', 'Prejuízo (R$)', 'Rentabilidade (%)'
            ]

            st.dataframe(
                display_worst5.style.format({
                    'Preço Médio (R$)': 'R$ {:,.2f}',
                    'Cotação (R$)': 'R$ {:,.2f}',
                    'Prejuízo (R$)': 'R$ {:,.2f}',
                    'Rentabilidade (%)': '{:,.2f}%'
                }).map(
                    lambda v: 'color: #ef4444; font-weight: bold;',
                    subset=['Prejuízo (R$)', 'Rentabilidade (%)']
                ),
                use_container_width=True
            )

        with c2:
            fig_worst = px.bar(
                top5_worst,
                x='rentabilidade_pct',
                y='ticker',
                orientation='h',
                text='rentabilidade_pct',
                color='rentabilidade_pct',
                color_continuous_scale='Reds_r',
                title="Top 5 - Desvalorização (%)"
            )
            fig_worst.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
            fig_worst.update_layout(
                yaxis=dict(autorange="reversed"),
                xaxis_title="Rentabilidade (%)",
                yaxis_title="Ativo",
                template="plotly_dark",
                coloraxis_showscale=False
            )
            st.plotly_chart(fig_worst, use_container_width=True)


# ==========================================
# TAB 4: RENDIMENTOS & PROVENTOS
# ==========================================
with tab4:
    st.header("💰 Histórico de Rendimentos & Dividendos")
    
    if not df_rendimentos.empty:
        col_r1, col_r2 = st.columns([1, 2])
        
        with col_r1:
            st.subheader("Resumo por Ativo")
            rend_by_ticker = df_rendimentos.groupby('ticker')['valor_total'].sum().reset_index()
            rend_by_ticker = rend_by_ticker.sort_values(by='valor_total', ascending=False)
            rend_by_ticker.columns = ['Ticker', 'Total Recebido (R$)']
            
            st.dataframe(
                rend_by_ticker.style.format({'Total Recebido (R$)': 'R$ {:,.2f}'}),
                use_container_width=True,
                height=350
            )

        with col_r2:
            st.subheader("Distribuição dos Rendimentos")
            fig_pie_rend = px.pie(
                rend_by_ticker.head(8),
                names='Ticker',
                values='Total Recebido (R$)',
                hole=0.4,
                title="Top 8 Pagadores de Rendimentos"
            )
            fig_pie_rend.update_layout(template="plotly_dark")
            st.plotly_chart(fig_pie_rend, use_container_width=True)

        st.markdown("---")
        st.subheader("📋 Tabela Completa de Rendimentos")
        
        display_rend = df_rendimentos[[
            'data', 'ticker', 'tipo_rendimento', 'quantidade', 'preco_unitario', 'valor_total'
        ]].copy()
        display_rend.columns = ['Data', 'Ticker', 'Tipo', 'Qtd', 'Valor Unitário (R$)', 'Valor Total (R$)']
        
        st.dataframe(
            display_rend.style.format({
                'Valor Unitário (R$)': 'R$ {:,.4f}',
                'Valor Total (R$)': 'R$ {:,.2f}'
            }),
            use_container_width=True,
            height=300
        )
    else:
        st.info("Nenhum rendimento registrado nesta versão.")
