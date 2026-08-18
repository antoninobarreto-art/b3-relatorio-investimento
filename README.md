# 📈 Dashboard Financeiro B3 (Python + Pandas + SQLite + Streamlit)

Aplicação interativa desenvolvida em **Python** para controle, análise e versionamento de carteira de investimentos baseada em extratos da B3 (`extrato_09ago2024.xlsx`).

---

## 🎯 Funcionalidades Principais

- **🗄️ Banco de Dados SQLite (`b3_investimentos.db`):** Armazenamento estruturado de **Ativos**, **Rendimentos** (Dividendos, JCP, Proventos), **Transações** e **Versões de Dados**.
- **📊 Relatório Preço Médio vs. Cotação Atual:** Apuração exata do Preço Médio ponderado via **Pandas** (considerando compras, vendas e desdobros) e cotação de mercado em tempo real via **yfinance**.
- **🚀 Top 5 Melhores Ativos:** Ranking e visualização gráfica dos ativos com maior rentabilidade percentual (%).
- **📉 Top 5 Piores Ativos:** Ranking dos ativos com menor desempenho/maior desvalorização.
- **💰 Rendimentos & Proventos:** Análise gráfica dos proventos recebidos por ativo e linha do tempo de recebimentos.
- **📜 Control de Versionamento:** Auditoria de importações no SQLite e botões para atualização ao vivo e exportação de dados em **CSV** e **Excel (.xlsx)**.

---

## 🚀 Como Executar o Projeto Localmente

### 1. Pré-requisitos

Certifique-se de ter o Python 3.9+ instalado. Instale as dependências executando:

```bash
pip install pandas openpyxl sqlite3 yfinance plotly streamlit
```

### 2. Executar o ETL (Processamento & Banco de Dados)

Execute o script `database_etl.py` para processar a planilha da B3 e gerar o banco SQLite `b3_investimentos.db`:

```bash
python database_etl.py
```

### 3. Iniciar o Dashboard Interativo

Inicie o servidor do Streamlit:

```bash
python -m streamlit run app.py
```

Acesse a aplicação no navegador em: **`http://localhost:8501`**

---

## 🛠️ Tecnologias Utilizadas

- **Linguagem:** Python
- **Manipulação de Dados:** Pandas
- **Banco de Dados:** SQLite3
- **Cotações de Mercado:** `yfinance`
- **Visualização Gráfica:** Plotly Express & Graph Objects
- **Interface Web:** Streamlit
- **Controle de Versão:** Git & GitHub

---

## 📌 Autor & Licença

Projeto desenvolvido para fins educacionais e análise financeira.
