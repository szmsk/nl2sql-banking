# 🏦 NL2SQL Banking Data Assistant

Ask questions about a banking database in plain English. A **LangChain pipeline** generates SQL, executes it on a realistic SQLite banking schema, and Claude interprets the results as actionable business insights.

> Built specifically to demonstrate skills required for AI Engineer roles in the banking/fintech sector — LangChain, NL2SQL, data pipelines, corporate data architectures.

## Features

- **LangChain NL2SQL pipeline** — uses `langchain-anthropic` with `ChatPromptTemplate` and `RunnablePassthrough`
- **Auto-retry** — if generated SQL fails, the chain automatically fixes the error and retries
- **Business interpretation** — second Claude call interprets query results as actionable insights
- **Realistic banking schema** — 6 tables: customers, accounts, transactions, loans, cards, branches
- **10 example queries** to get started
- **Interactive schema explorer** — click to expand any table

## Tech Stack

| Layer | Technology |
|---|---|
| AI Pipeline | **LangChain** (`langchain-anthropic`) |
| LLM | Anthropic Claude API (`claude-sonnet-4-20250514`) |
| Backend | Python · Flask |
| Database | SQLite (banking demo schema) |
| Frontend | Vanilla HTML · CSS · JavaScript |

## Quick Start

```bash
git clone https://github.com/szmsk/nl2sql-banking.git
cd nl2sql-banking
pip install -r requirements.txt
python server.py
# → http://localhost:5000
```

Get API key at [console.anthropic.com](https://console.anthropic.com).

## Database Schema

```
customers     — id, first_name, last_name, age, segment, risk_score, country
accounts      — id, customer_id, account_type, balance, currency, status
transactions  — id, account_id, amount, direction, category, description, tx_date
loans         — id, customer_id, loan_type, amount, outstanding, interest_rate, status
cards         — id, customer_id, card_type, card_limit, balance_used, status, last_used
branches      — id, name, city, country, manager
```

15 customers · 20 accounts · 20 transactions · 15 loans · 18 cards · 5 branches

## Example Questions

- *"Which customers have loans over 100,000 with an overdue status?"*
- *"Show total transaction volume by category"*
- *"Which Premium segment customers have the highest credit card utilisation?"*
- *"Compare average loan amounts across different customer segments"*
- *"List all customers from Poland with their total balance across all accounts"*

## LangChain Pipeline

```python
sql_chain = (
    {"schema": lambda _: get_schema(), "question": RunnablePassthrough()}
    | sql_prompt       # ChatPromptTemplate → generates SQL
    | llm              # ChatAnthropic
    | StrOutputParser()
)
# Execute SQL → interpret with second Claude call
```

## Project Structure

```
nl2sql-banking/
├── server.py           # Flask + LangChain + SQLite + Claude
├── requirements.txt
├── public/
│   ├── index.html
│   ├── style.css
│   └── app.js
└── README.md
```

## Why This Project

This project directly targets AI Engineer roles in banking/fintech that require:
- LangChain / langchain4j experience
- NL2SQL approaches
- Corporate data architecture understanding
- LLM integration with data pipelines

## Author

**Szymon Kloskowski** — kloskowskiszymon@wp.pl
[github.com/szmsk](https://github.com/szmsk) · [linkedin.com/in/szymon-kloskowski](https://linkedin.com/in/szymon-kloskowski)

MIT License
