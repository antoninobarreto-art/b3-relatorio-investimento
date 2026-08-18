import sqlite3
import datetime
import pandas as pd
import yfinance as yf

DB_NAME = "b3_investimentos.db"
EXCEL_FILE = "extrato_09ago2024.xlsx"

def clean_number(val):
    if pd.isna(val) or str(val).strip() in ['-', '']:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    # Convert string if necessary
    s = str(val).replace('R$', '').replace('.', '').replace(',', '.').strip()
    try:
        return float(s)
    except ValueError:
        return 0.0

def init_db(conn):
    cursor = conn.cursor()
    
    # Table 1: Versões de dados
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS versoes_dados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_importacao TEXT NOT NULL,
        arquivo_origem TEXT NOT NULL,
        total_registros INTEGER NOT NULL,
        descricao TEXT
    );
    """)
    
    # Table 2: Ativos (Posição Consolidada)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ativos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        versao_id INTEGER NOT NULL,
        ticker TEXT NOT NULL,
        nome_produto TEXT NOT NULL,
        tipo_ativo TEXT NOT NULL,
        quantidade_atual INTEGER NOT NULL,
        preco_medio REAL NOT NULL,
        cotacao_atual REAL NOT NULL,
        valor_investido REAL NOT NULL,
        valor_atual REAL NOT NULL,
        lucro_prejuizo_rs REAL NOT NULL,
        rentabilidade_pct REAL NOT NULL,
        FOREIGN KEY (versao_id) REFERENCES versoes_dados (id)
    );
    """)
    
    # Table 3: Rendimentos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rendimentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        versao_id INTEGER NOT NULL,
        data TEXT NOT NULL,
        ticker TEXT NOT NULL,
        produto TEXT NOT NULL,
        tipo_rendimento TEXT NOT NULL,
        instituicao TEXT,
        quantidade INTEGER NOT NULL,
        preco_unitario REAL NOT NULL,
        valor_total REAL NOT NULL,
        FOREIGN KEY (versao_id) REFERENCES versoes_dados (id)
    );
    """)
    
    # Table 4: Transações
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        versao_id INTEGER NOT NULL,
        data TEXT NOT NULL,
        entrada_saida TEXT NOT NULL,
        tipo_movimentacao TEXT NOT NULL,
        ticker TEXT NOT NULL,
        produto TEXT NOT NULL,
        instituicao TEXT,
        quantidade INTEGER NOT NULL,
        preco_unitario REAL NOT NULL,
        valor_total REAL NOT NULL,
        FOREIGN KEY (versao_id) REFERENCES versoes_dados (id)
    );
    """)
    
    conn.commit()

def process_and_load_data():
    conn = sqlite3.connect(DB_NAME)
    init_db(conn)
    
    # Read Excel file
    df = pd.read_excel(EXCEL_FILE)
    
    # Clean columns
    df['Preço_unitario_clean'] = df['Preço unitário'].apply(clean_number)
    df['Valor_operacao_clean'] = df['Valor da Operação'].apply(clean_number)
    df['Data_dt'] = pd.to_datetime(df['Data'], format='%d/%m/%Y')
    df['Ticker'] = df['Produto'].apply(lambda x: str(x).split('-')[0].strip())
    
    # Register Version
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO versoes_dados (data_importacao, arquivo_origem, total_registros, descricao)
        VALUES (?, ?, ?, ?)
    """, (now_str, EXCEL_FILE, len(df), f"Importação inicial do extrato B3 ({len(df)} registros)"))
    versao_id = cursor.lastrowid
    conn.commit()
    
    # Sort chronologically for calculation
    df_sorted = df.sort_values(by=['Data_dt', 'Ticker']).reset_index(drop=True)
    
    # Portfolio tracking
    portfolio = {}
    transacoes_list = []
    rendimentos_list = []
    
    for idx, row in df_sorted.iterrows():
        ticker = row['Ticker']
        mov = str(row['Movimentação']).strip()
        es = str(row['Entrada/Saída']).strip()
        qty = int(row['Quantidade']) if pd.notnull(row['Quantidade']) else 0
        price = float(row['Preço_unitario_clean'])
        val_total = float(row['Valor_operacao_clean'])
        data_str = row['Data']
        prod = str(row['Produto'])
        inst = str(row['Instituição']) if 'Instituição' in row else ''
        
        # Categorize
        if mov in ['Rendimento', 'Dividendo', 'Juros Sobre Capital Próprio']:
            rendimentos_list.append((
                versao_id, data_str, ticker, prod, mov, inst, qty, price, val_total
            ))
        else:
            transacoes_list.append((
                versao_id, data_str, es, mov, ticker, prod, inst, qty, price, val_total
            ))
            
            # Position calculation
            if ticker not in portfolio:
                portfolio[ticker] = {
                    'qty': 0,
                    'total_cost': 0.0,
                    'pm': 0.0,
                    'produto': prod
                }
            
            p = portfolio[ticker]
            
            if mov in ['Transferência - Liquidação', 'Direito de Subscrição']:
                if es == 'Credito' and qty > 0 and price > 0:
                    p['qty'] += qty
                    p['total_cost'] += qty * price
                    p['pm'] = p['total_cost'] / p['qty'] if p['qty'] > 0 else 0.0
                elif es == 'Debito' and qty > 0:
                    p['qty'] = max(0, p['qty'] - qty)
                    p['total_cost'] = p['qty'] * p['pm']
            elif mov == 'Desdobro':
                if es == 'Credito' and qty > 0:
                    p['qty'] += qty
                    p['pm'] = p['total_cost'] / p['qty'] if p['qty'] > 0 else 0.0
    
    # Save Rendimentos to DB
    cursor.executemany("""
        INSERT INTO rendimentos (versao_id, data, ticker, produto, tipo_rendimento, instituicao, quantidade, preco_unitario, valor_total)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rendimentos_list)
    
    # Save Transacoes to DB
    cursor.executemany("""
        INSERT INTO transacoes (versao_id, data, entrada_saida, tipo_movimentacao, ticker, produto, instituicao, quantidade, preco_unitario, valor_total)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, transacoes_list)
    
    # Fetch Market Quotes via yfinance
    active_portfolio = [p for t, p in portfolio.items() if p['qty'] > 0]
    tickers = [p['produto'].split('-')[0].strip() for p in active_portfolio]
    yf_tickers = [f"{t}.SA" for t in tickers]
    
    latest_prices = {}
    if yf_tickers:
        try:
            download_df = yf.download(yf_tickers, period='1d', progress=False)['Close']
            if not download_df.empty:
                last_row = download_df.iloc[-1]
                for t, yft in zip(tickers, yf_tickers):
                    try:
                        val = last_row[yft]
                        if not pd.isna(val) and float(val) > 0:
                            latest_prices[t] = float(val)
                    except Exception:
                        pass
        except Exception as e:
            print(f"Aviso ao buscar cotações: {e}")
            
    ativos_list = []
    for p in active_portfolio:
        ticker = p['produto'].split('-')[0].strip()
        nome_prod = p['produto']
        qty = p['qty']
        pm = p['pm']
        
        # Determine current quote
        cotacao = latest_prices.get(ticker, pm)
        
        # Determine Asset Type
        if ticker.endswith(('11', '11B')):
            tipo = "FII / ETF"
        elif ticker.endswith(('34', '33')):
            tipo = "BDR"
        else:
            tipo = "Ação"
            
        valor_investido = qty * pm
        valor_atual = qty * cotacao
        lucro_rs = valor_atual - valor_investido
        rent_pct = ((cotacao - pm) / pm * 100.0) if pm > 0 else 0.0
        
        ativos_list.append((
            versao_id, ticker, nome_prod, tipo, qty, round(pm, 2), round(cotacao, 2),
            round(valor_investido, 2), round(valor_atual, 2), round(lucro_rs, 2), round(rent_pct, 2)
        ))
        
    cursor.executemany("""
        INSERT INTO ativos (versao_id, ticker, nome_produto, tipo_ativo, quantidade_atual, preco_medio, cotacao_atual, valor_investido, valor_atual, lucro_prejuizo_rs, rentabilidade_pct)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, ativos_list)
    
    conn.commit()
    conn.close()
    print(f"ETL Concluído com Sucesso! Versão #{versao_id} gravada no SQLite ({DB_NAME}).")

if __name__ == "__main__":
    process_and_load_data()
