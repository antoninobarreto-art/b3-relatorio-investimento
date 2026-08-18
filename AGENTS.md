# AGENTS.md - Diretrizes para Agentes de IA

Este repositório contém a aplicação do **Dashboard Interativo Financeiro B3**, desenvolvida em **Python** com **Pandas**, **SQLite** e **Streamlit**.

---

## 🎯 Visão Geral do Projeto

- **Objetivo:** Processamento de extratos financeiros da B3 (`extrato_09ago2024.xlsx`), cálculo de Preço Médio ponderado de ativos, acompanhamento de cotações em tempo real e controle de versionamento no SQLite.
- **Arquitetura:**
  - `database_etl.py`: Pipeline ETL (Extração, Transformação, Carga) e cálculo de Preço Médio.
  - `app.py`: Interface web interativa em Streamlit dividida em 5 abas de relatórios e análises.
  - `b3_investimentos.db`: Banco de dados SQLite relacional.

---

## 🛠️ Regras de Desenvolvimento e Padrões de Código

### 1. Manipulação de Dados & Pandas
- **Preço Médio:** Manter a regra da B3. Compras recalculam o Preço Médio ponderado; vendas reduzem a posição mantendo o Preço Médio inalterado.
- **Desdobros (Stock Splits):** Tratar eventos de desdobro ajustando a quantidade total e recalculando o Preço Médio proporcional ao custo total acumulado.
- **Fallbacks:** Sempre incluir fallback seguro na consulta de cotações via `yfinance` para evitar interrupções caso tickers de leilão ou direitos de subscrição não estejam disponíveis.

### 2. Banco de Dados SQLite
- Toda importação ou atualização de dados deve gravar uma nova versão na tabela `versoes_dados` para manter o histórico e auditabilidade.
- As chaves estrangeiras `versao_id` devem conectar as tabelas `ativos`, `rendimentos` e `transacoes` à versão correspondente.

### 3. Interface Visual & Streamlit
- Idioma padrão da interface: **Português (Brasil)**.
- Formatação monetária em padrão brasileiro: `R$ X.XXX,XX`.
- Formatação de percentual: `+X.XX%` (verde para positivo, vermelho para negativo).
- Gráficos interativos construídos via **Plotly Express / Graph Objects** com tema escuro adaptado (`plotly_dark`).

---

## 📌 Comandos de Verificação e Execução

```bash
# Rodar a carga de dados no SQLite
python database_etl.py

# Iniciar o servidor do Dashboard
python -m streamlit run app.py

# Sincronização com o GitHub
git add .
git commit -m "sua mensagem"
git push -u origin main
```
