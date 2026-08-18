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
APP_VERSION = "v1.3.0"

def get_git_commit_hash():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode("utf-8").strip()
    except Exception:
        return "main"

GIT_COMMIT = get_git_commit_hash()

# Streamlit Page Setup
st.set_page_config(
    page_title="Dashboard Financeiro de Investimentos - B3",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Dark Theme CSS matching the exact Mockup Image
st.markdown("""
<style>
    /* Dark Theme Core Setup */
    .stApp {
        background-color: #0B0F19;
        color: #F3F4F6;
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #101726 !important;
        border-right: 1px solid #1E293B !important;
        padding-top: 10px;
    }
    .sidebar-logo {
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 1.4rem;
        font-weight: 800;
        color: #F8FAFC;
        margin-bottom: 25px;
    }
    .sidebar-section-title {
        font-size: 0.75rem;
        font-weight: 700;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 12px;
    }
    
    /* Upload Dropzone Box */
    .upload-box {
        border: 2px dashed #334155;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        background-color: #0F172A;
        margin-bottom: 15px;
    }
    
    /* Metric Cards Grid */
    .kpi-card {
        background: #1B2436;
        border: 1px solid #2A364F;
        border-radius: 16px;
        padding: 22px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
        margin-bottom: 15px;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .kpi-label {
        font-size: 0.85rem;
        color: #94A3B8;
        font-weight: 600;
        margin-bottom: 8px;
    }
    .kpi-value-row {
        display: flex;
        align-items: baseline;
        gap: 10px;
        flex-wrap: wrap;
    }
    .kpi-value {
        font-size: 1.75rem;
        font-weight: 800;
        color: #FFFFFF;
    }
    .kpi-value-green {
        font-size: 1.75rem;
        font-weight: 800;
        color: #10B981;
    }
    .kpi-badge-green {
        background-color: rgba(16, 185, 129, 0.15);
        color: #10B981;
        font-size: 0.8rem;
        font-weight: 700;
        padding: 4px 8px;
        border-radius: 6px;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .kpi-badge-red {
        background-color: rgba(239, 68, 68, 0.15);
        color: #EF4444;
        font-size: 0.8rem;
        font-weight: 700;
        padding: 4px 8px;
        border-radius: 6px;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }
    
    /* Section Content Card */
    .content-box {
        background: #1B2436;
        border: 1px solid #2A364F;
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
    }
    
    /* Resumo Recebido Item Card */
    .resumo-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 14px 16px;
        background-color: #0F172A;
        border: 1px solid #1E293B;
        border-radius: 12px;
        margin-bottom: 10px;
    }
    .avatar-circle {
        width: 42px;
        height: 42px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 800;
        font-size: 0.85rem;
        color: #FFFFFF;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    .ticker-name {
        font-weight: 700;
        color: #F8FAFC;
        font-size: 1rem;
    }
    .ticker-type {
        font-size: 0.78rem;
        color: #64748B;
    }
    .ticker-val {
        font-weight: 800;
        font-size: 1.05rem;
        color: #F8FAFC;
    }
    
    /* Sidebar Info Footer */
    .info-card {
        background-color: #0F172A;
        border: 1px solid #1E293B;
        border-radius: 12px;
        padding: 14px;
        color: #94A3B8;
        font-size: 0.8rem;
        line-height: 1.4;
        margin-top: 15px;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        border-bottom: 1px solid #1E293B;
        padding-bottom: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: transparent;
        border-radius: 8px;
        padding: 8px 18px;
        font-weight: 700;
        color: #94A3B8;
        border: none;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1E293B !important;
        color: #3B82F6 !important;
        border-bottom: 2px solid #3B82F6 !important;
    }
</style>
""", unsafe_allow_html=True)

# Database Helpers
def get_db_connection():
    if not os.path.exists(DB_NAME):
        database_etl.process_and_load_data()
    return sqlite3.connect(DB_NAME)

def load_versions():
    conn = get_db_connection()
    df = pd.read_sql("SELECT * FROM versoes_dados ORDER BY id DESC", conn)
    conn.close()
    return df

def load_ativos(versao_id):
    conn = get_db_connection()
    df = pd.read_sql("SELECT * FROM ativos WHERE versao_id = ?", conn, params=(versao_id,))
    conn.close()
    return df

def load_rendimentos(versao_id):
    conn = get_db_connection()
    df = pd.read_sql("SELECT * FROM rendimentos WHERE versao_id = ?", conn, params=(versao_id,))
    conn.close()
    return df

def load_transacoes(versao_id):
    conn = get_db_connection()
    df = pd.read_sql("SELECT * FROM transacoes WHERE versao_id = ?", conn, params=(versao_id,))
    conn.close()
    return df

# Ensure DB initialized
if not os.path.exists(DB_NAME):
    with st.spinner("Inicializando Banco de Dados e Importando Planilha B3..."):
        database_etl.process_and_load_data()

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.markdown('<div class="sidebar-logo">📈 <span>Painel B3</span></div>', unsafe_allow_html=True)
    
    st.markdown('<div class="sidebar-section-title">IMPORTAR PLANILHA</div>', unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "Arraste sua planilha .xlsx ou clique para procurar", 
        type=["xlsx"],
        help="Limite de 200MB por arquivo"
    )
    
    if uploaded_file is not None:
        # Save temp file & run ETL
        temp_path = "extrato_temp.xlsx"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        with st.spinner("Processando nova planilha..."):
            database_etl.process_and_load_data()
            st.success("Planilha processada e nova versão criada!")
            st.rerun()

    st.markdown("---")
    
    # Version Selector
    df_versions = load_versions()
    selected_version_id = 1
    if not df_versions.empty:
        version_options = {
            row['id']: f"Versão #{row['id']} ({row['data_importacao'][:16]})" 
            for _, row in df_versions.iterrows()
        }
        selected_version_id = st.selectbox(
            "📌 Histórico de Versões:",
            options=list(version_options.keys()),
            format_func=lambda x: version_options[x]
        )
    
    if st.button("🔄 Atualizar Cotações / Re-importar", use_container_width=True):
        with st.spinner("Atualizando cotações de mercado via yfinance..."):
            database_etl.process_and_load_data()
            st.success("Cotações atualizadas com sucesso!")
            st.rerun()

    st.markdown("---")
    
    # Export Section
    st.markdown('<div class="sidebar-section-title">EXPORTAR CARTEIRA</div>', unsafe_allow_html=True)
    df_ativos = load_ativos(selected_version_id)
    df_rendimentos = load_rendimentos(selected_version_id)
    df_transacoes = load_transacoes(selected_version_id)
    
    if not df_ativos.empty:
        csv_data = df_ativos.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📄 Baixar Arquivo CSV",
            data=csv_data,
            file_name="carteira_b3.csv",
            mime="text/csv",
            use_container_width=True
        )

        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df_ativos.to_excel(writer, sheet_name='Ativos', index=False)
            df_rendimentos.to_excel(writer, sheet_name='Rendimentos', index=False)
            df_transacoes.to_excel(writer, sheet_name='Transações', index=False)
        excel_data = excel_buffer.getvalue()

        st.download_button(
            label="📊 Baixar Planilha Excel (.xlsx)",
            data=excel_data,
            file_name="carteira_b3.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    st.markdown("""
    <div class="info-card">
        ℹ️ <b>Modo Visualização:</b> Os dados exibidos são processados em tempo real a partir dos extratos oficiais da B3 e cotações do mercado financeiro.
    </div>
    """, unsafe_allow_html=True)


# ==========================================
# MAIN CONTENT HEADER
# ==========================================
col_hdr, col_gear = st.columns([0.92, 0.08])
with col_hdr:
    st.markdown("""
    <h1 style="font-size: 2rem; font-weight: 800; color: #F8FAFC; margin-bottom: 4px;">
        📊 Dashboard Financeiro de Investimentos - B3
    </h1>
    <p style="font-size: 0.95rem; color: #94A3B8; margin-bottom: 20px;">
        Análise integrada de Carteira, Preço Médio, Rendimentos e Performance
    </p>
    """, unsafe_allow_html=True)

with col_gear:
    st.markdown("""
    <div style="text-align: right; padding-top: 10px;">
        <button style="background: #1B2436; border: 1px solid #2A364F; color: #94A3B8; padding: 10px 14px; border-radius: 10px; cursor: pointer;">⚙️</button>
    </div>
    """, unsafe_allow_html=True)


# ==========================================
# TOP 4 KPI CARDS GRID (Matches Mockup Image!)
# ==========================================
if not df_ativos.empty:
    patrimonio_total = df_ativos['valor_atual'].sum()
    total_investido = df_ativos['valor_investido'].sum()
    lucro_total = df_ativos['lucro_prejuizo_rs'].sum()
    rentabilidade_geral = ((patrimonio_total - total_investido) / total_investido * 100) if total_investido > 0 else 0.0
    total_proventos = df_rendimentos['valor_total'].sum() if not df_rendimentos.empty else 0.0

    k1, k2, k3, k4 = st.columns(4)

    with k1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Total Investido</div>
            <div class="kpi-value">R$ {total_investido:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    with k2:
        badge_cls = "kpi-badge-green" if rentabilidade_geral >= 0 else "kpi-badge-red"
        sign = "+" if rentabilidade_geral >= 0 else ""
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Patrimônio Atual</div>
            <div class="kpi-value-row">
                <span class="kpi-value">R$ {patrimonio_total:,.2f}</span>
                <span class="{badge_cls}">{sign}{rentabilidade_geral:.2f}%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with k3:
        val_cls = "kpi-value-green" if lucro_total >= 0 else "kpi-value"
        arrow = "↑" if lucro_total >= 0 else "↓"
        sign = "+" if lucro_total >= 0 else ""
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Lucro / Prejuízo Total</div>
            <div class="kpi-value-row">
                <span class="{val_cls}">{sign}R$ {lucro_total:,.2f}</span>
                <span style="color: {'#10B981' if lucro_total >= 0 else '#EF4444'}; font-size: 1.2rem; font-weight: 800;">{arrow}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with k4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Rendimentos Recebidos</div>
            <div class="kpi-value">R$ {total_proventos:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# ==========================================
# MAIN TABS (Matches Mockup Navigation!)
# ==========================================
tab_pm, tab_top, tab_rend = st.tabs([
    "📊 Preço Médio vs. Cotação",
    "🏆 Top 5 Melhores & Piores",
    "💰 Extrato de Rendimentos"
])


# ==========================================
# TAB 1: PREÇO MÉDIO VS COTAÇÃO
# ==========================================
with tab_pm:
    col_search, col_filter = st.columns([2, 1])
    with col_search:
        search_ticker = st.text_input("🔍 Pesquisar Ativo (Ticker ou Nome):", "").strip().upper()
    with col_filter:
        tipos = ["Todos"] + sorted(df_ativos['tipo_ativo'].unique().tolist()) if not df_ativos.empty else ["Todos"]
        selected_tipo = st.selectbox("🏷️ Filtrar por Classe de Ativo:", tipos)

    df_filtered = df_ativos.copy()
    if search_ticker:
        df_filtered = df_filtered[
            df_filtered['ticker'].str.contains(search_ticker, case=False) |
            df_filtered['nome_produto'].str.contains(search_ticker, case=False)
        ]
    if selected_tipo != "Todos":
        df_filtered = df_filtered[df_filtered['tipo_ativo'] == selected_tipo]

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
            lambda v: 'color: #10B981; font-weight: bold;' if v > 0 else ('color: #EF4444; font-weight: bold;' if v < 0 else ''),
            subset=['Lucro/Prejuízo (R$)', 'Rentabilidade (%)']
        ),
        use_container_width=True,
        height=400
    )

    if not df_filtered.empty:
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=df_filtered['ticker'],
            y=df_filtered['preco_medio'],
            name='Preço Médio (R$)',
            marker_color='#6366F1'
        ))
        fig_bar.add_trace(go.Bar(
            x=df_filtered['ticker'],
            y=df_filtered['cotacao_atual'],
            name='Cotação Atual (R$)',
            marker_color='#10B981'
        ))
        fig_bar.update_layout(
            barmode='group',
            xaxis_title="Ativo",
            yaxis_title="Preço em R$",
            template="plotly_dark",
            paper_bgcolor="#1B2436",
            plot_bgcolor="#1B2436",
            margin=dict(l=20, r=20, t=30, b=20)
        )
        st.plotly_chart(fig_bar, use_container_width=True)


# ==========================================
# TAB 2: TOP 5 MELHORES & PIORES
# ==========================================
with tab_top:
    c_best, c_worst = st.columns(2)
    
    with c_best:
        st.markdown("### 🚀 Top 5 Melhores Ativos")
        top5_best = df_ativos.sort_values(by='rentabilidade_pct', ascending=False).head(5)
        if not top5_best.empty:
            best_display = top5_best[['ticker', 'quantidade_atual', 'preco_medio', 'cotacao_atual', 'rentabilidade_pct']].copy()
            best_display.columns = ['Ticker', 'Qtd', 'Preço Médio', 'Cotação', 'Rentabilidade (%)']
            st.dataframe(
                best_display.style.format({
                    'Preço Médio': 'R$ {:,.2f}',
                    'Cotação': 'R$ {:,.2f}',
                    'Rentabilidade (%)': '+{:,.2f}%'
                }).map(lambda v: 'color: #10B981; font-weight: bold;', subset=['Rentabilidade (%)']),
                use_container_width=True
            )
            
            fig_b = px.bar(
                top5_best, x='rentabilidade_pct', y='ticker', orientation='h',
                text='rentabilidade_pct', color='rentabilidade_pct', color_continuous_scale='Greens'
            )
            fig_b.update_traces(texttemplate='+%{text:.2f}%', textposition='outside')
            fig_b.update_layout(
                yaxis=dict(autorange="reversed"), xaxis_title="Rentabilidade (%)",
                template="plotly_dark", paper_bgcolor="#1B2436", plot_bgcolor="#1B2436", coloraxis_showscale=False
            )
            st.plotly_chart(fig_b, use_container_width=True)

    with c_worst:
        st.markdown("### 📉 Top 5 Piores Ativos")
        top5_worst = df_ativos.sort_values(by='rentabilidade_pct', ascending=True).head(5)
        if not top5_worst.empty:
            worst_display = top5_worst[['ticker', 'quantidade_atual', 'preco_medio', 'cotacao_atual', 'rentabilidade_pct']].copy()
            worst_display.columns = ['Ticker', 'Qtd', 'Preço Médio', 'Cotação', 'Rentabilidade (%)']
            st.dataframe(
                worst_display.style.format({
                    'Preço Médio': 'R$ {:,.2f}',
                    'Cotação': 'R$ {:,.2f}',
                    'Rentabilidade (%)': '{:,.2f}%'
                }).map(lambda v: 'color: #EF4444; font-weight: bold;', subset=['Rentabilidade (%)']),
                use_container_width=True
            )
            
            fig_w = px.bar(
                top5_worst, x='rentabilidade_pct', y='ticker', orientation='h',
                text='rentabilidade_pct', color='rentabilidade_pct', color_continuous_scale='Reds_r'
            )
            fig_w.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
            fig_w.update_layout(
                yaxis=dict(autorange="reversed"), xaxis_title="Rentabilidade (%)",
                template="plotly_dark", paper_bgcolor="#1B2436", plot_bgcolor="#1B2436", coloraxis_showscale=False
            )
            st.plotly_chart(fig_w, use_container_width=True)


# ==========================================
# TAB 3: EXTRATO DE RENDIMENTOS (Matches Mockup Image Layout!)
# ==========================================
with tab_rend:
    if not df_rendimentos.empty:
        rend_summary = df_rendimentos.groupby(['ticker', 'tipo_rendimento'])['valor_total'].sum().reset_index()
        rend_by_ticker = df_rendimentos.groupby('ticker')['valor_total'].sum().reset_index().sort_values(by='valor_total', ascending=False)
        
        c_chart, c_resumo = st.columns([1.1, 0.9])
        
        with c_chart:
            st.markdown('<div class="content-box">', unsafe_allow_html=True)
            st.markdown("<h3 style='font-size: 1.2rem; font-weight: 700; color: #F8FAFC;'>Distribuição de Rendimentos</h3>", unsafe_allow_html=True)
            
            colors_palette = ['#3B82F6', '#F59E0B', '#8B5CF6', '#10B981', '#EC4899', '#6366F1', '#14B8A6']
            fig_pie = px.pie(
                rend_by_ticker.head(7),
                names='ticker',
                values='valor_total',
                hole=0.55,
                color_discrete_sequence=colors_palette
            )
            fig_pie.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
                margin=dict(l=10, r=10, t=40, b=10)
            )
            st.plotly_chart(fig_pie, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with c_resumo:
            st.markdown('<div class="content-box">', unsafe_allow_html=True)
            st.markdown("<h3 style='font-size: 1.2rem; font-weight: 700; color: #F8FAFC; margin-bottom: 16px;'>Resumo Recebido</h3>", unsafe_allow_html=True)
            
            top_rend_list = rend_summary.sort_values(by='valor_total', ascending=False).head(5)
            
            colors_map = {
                'PETR4': '#3B82F6', 'BBAS3': '#F59E0B', 'ITUB4': '#8B5CF6', 
                'MXRF11': '#10B981', 'HGLG11': '#EC4899', 'XPML11': '#6366F1',
                'BTLG11': '#14B8A6', 'CPFE3': '#3B82F6'
            }
            
            for idx, row in top_rend_list.iterrows():
                ticker_code = row['ticker']
                tipo_name = row['tipo_rendimento']
                val_amt = row['valor_total']
                avatar_bg = colors_map.get(ticker_code, '#3B82F6')
                avatar_letters = ticker_code[:4]
                
                st.markdown(f"""
                <div class="resumo-item">
                    <div style="display: flex; align-items: center; gap: 14px;">
                        <div class="avatar-circle" style="background-color: {avatar_bg};">
                            {avatar_letters}
                        </div>
                        <div>
                            <div class="ticker-name">{ticker_code}</div>
                            <div class="ticker-type">{tipo_name}s</div>
                        </div>
                    </div>
                    <div class="ticker-val">R$ {val_amt:,.2f}</div>
                </div>
                """, unsafe_allow_html=True)
                
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("📋 Tabela Completa de Extrato de Rendimentos")
        display_r = df_rendimentos[['data', 'ticker', 'tipo_rendimento', 'quantidade', 'preco_unitario', 'valor_total']].copy()
        display_r.columns = ['Data', 'Ticker', 'Tipo de Provento', 'Quantidade', 'Valor Unitário (R$)', 'Valor Total (R$)']
        st.dataframe(
            display_r.style.format({
                'Valor Unitário (R$)': 'R$ {:,.4f}',
                'Valor Total (R$)': 'R$ {:,.2f}'
            }),
            use_container_width=True,
            height=300
        )
    else:
        st.info("Nenhum extrato de rendimento registrado nesta versão.")
