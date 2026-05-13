"""
NL2SQL Banking Data Assistant
LangChain + Claude + SQLite banking schema
"""
import os, json, re, time, sqlite3, uuid
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

app = Flask(__name__, static_folder='public', static_url_path='')
CORS(app)
DB = 'banking.db'


# ── Database seed ──────────────────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.executescript("""
    PRAGMA foreign_keys = ON;

    CREATE TABLE IF NOT EXISTS customers (
        id            INTEGER PRIMARY KEY,
        first_name    TEXT NOT NULL,
        last_name     TEXT NOT NULL,
        age           INTEGER,
        segment       TEXT CHECK(segment IN ('Retail','Premium','Private','SME')),
        risk_score    REAL,
        country       TEXT,
        joined_date   TEXT
    );

    CREATE TABLE IF NOT EXISTS accounts (
        id            INTEGER PRIMARY KEY,
        customer_id   INTEGER REFERENCES customers(id),
        account_type  TEXT CHECK(account_type IN ('Checking','Savings','Investment','Business')),
        balance       REAL DEFAULT 0,
        currency      TEXT DEFAULT 'PLN',
        status        TEXT DEFAULT 'Active',
        opened_date   TEXT
    );

    CREATE TABLE IF NOT EXISTS transactions (
        id            INTEGER PRIMARY KEY,
        account_id    INTEGER REFERENCES accounts(id),
        amount        REAL NOT NULL,
        direction     TEXT CHECK(direction IN ('Credit','Debit')),
        category      TEXT,
        description   TEXT,
        tx_date       TEXT,
        status        TEXT DEFAULT 'Completed'
    );

    CREATE TABLE IF NOT EXISTS loans (
        id            INTEGER PRIMARY KEY,
        customer_id   INTEGER REFERENCES customers(id),
        loan_type     TEXT CHECK(loan_type IN ('Mortgage','Personal','Auto','Business')),
        amount        REAL NOT NULL,
        outstanding   REAL NOT NULL,
        interest_rate REAL,
        monthly_payment REAL,
        status        TEXT CHECK(status IN ('Active','Paid','Overdue','Default')),
        start_date    TEXT,
        due_date      TEXT
    );

    CREATE TABLE IF NOT EXISTS cards (
        id            INTEGER PRIMARY KEY,
        customer_id   INTEGER REFERENCES customers(id),
        card_type     TEXT CHECK(card_type IN ('Debit','Credit','Prepaid')),
        card_limit    REAL DEFAULT 0,
        balance_used  REAL DEFAULT 0,
        status        TEXT CHECK(status IN ('Active','Blocked','Expired','Cancelled')),
        last_used     TEXT,
        issued_date   TEXT
    );

    CREATE TABLE IF NOT EXISTS branches (
        id            INTEGER PRIMARY KEY,
        name          TEXT NOT NULL,
        city          TEXT,
        country       TEXT,
        manager       TEXT
    );
    """)

    if c.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 0:
        _seed(c)

    conn.commit()
    conn.close()
    print("✅ Banking database ready")


def _seed(c):
    customers = [
        (1,'James','Wilson',45,'Premium',72.5,'Poland','2018-03-12'),
        (2,'Anna','Kowalska',32,'Retail',85.1,'Poland','2020-07-04'),
        (3,'Michael','Schmidt',58,'Private',91.3,'Germany','2015-01-20'),
        (4,'Sophie','Dubois',29,'Retail',62.4,'France','2022-11-08'),
        (5,'Carlos','Garcia',41,'SME',55.7,'Spain','2019-05-17'),
        (6,'Emma','Johnson',36,'Premium',78.9,'UK','2017-09-30'),
        (7,'Lars','Andersen',52,'Private',94.2,'Denmark','2014-06-14'),
        (8,'Maria','Ferrari',27,'Retail',48.3,'Italy','2023-02-28'),
        (9,'Hans','Mueller',63,'Premium',83.6,'Germany','2016-04-09'),
        (10,'Eva','Novak',34,'Retail',67.8,'Czech Republic','2021-08-15'),
        (11,'David','Brown',47,'SME',59.1,'UK','2018-12-01'),
        (12,'Isabelle','Martin',39,'Premium',76.4,'France','2019-03-22'),
        (13,'Piotr','Wiśniewski',55,'Private',88.7,'Poland','2013-10-05'),
        (14,'Sara','Nielsen',31,'Retail',71.2,'Denmark','2021-01-19'),
        (15,'Roberto','Rossi',44,'SME',53.8,'Italy','2020-06-27'),
    ]
    c.executemany("INSERT OR IGNORE INTO customers VALUES (?,?,?,?,?,?,?,?)", customers)

    accounts = [
        (1,1,'Checking',12450.00,'PLN','Active','2018-03-12'),
        (2,1,'Savings',87300.00,'PLN','Active','2018-03-12'),
        (3,1,'Investment',245000.00,'PLN','Active','2019-06-01'),
        (4,2,'Checking',3210.50,'PLN','Active','2020-07-04'),
        (5,2,'Savings',15600.00,'PLN','Active','2020-07-04'),
        (6,3,'Checking',28900.00,'EUR','Active','2015-01-20'),
        (7,3,'Investment',890000.00,'EUR','Active','2015-01-20'),
        (8,4,'Checking',1820.75,'EUR','Active','2022-11-08'),
        (9,5,'Business',45600.00,'EUR','Active','2019-05-17'),
        (10,5,'Checking',8900.00,'EUR','Active','2019-05-17'),
        (11,6,'Checking',19200.00,'GBP','Active','2017-09-30'),
        (12,6,'Savings',62000.00,'GBP','Active','2017-09-30'),
        (13,7,'Investment',1250000.00,'DKK','Active','2014-06-14'),
        (14,8,'Checking',980.25,'EUR','Active','2023-02-28'),
        (15,9,'Checking',34500.00,'EUR','Active','2016-04-09'),
        (16,9,'Savings',120000.00,'EUR','Active','2016-04-09'),
        (17,10,'Checking',5670.00,'CZK','Active','2021-08-15'),
        (18,11,'Business',78900.00,'GBP','Active','2018-12-01'),
        (19,12,'Checking',22100.00,'EUR','Active','2019-03-22'),
        (20,13,'Investment',560000.00,'PLN','Active','2013-10-05'),
    ]
    c.executemany("INSERT OR IGNORE INTO accounts VALUES (?,?,?,?,?,?,?)", accounts)

    transactions = [
        (1,1,-2500.00,'Debit','Mortgage Payment','Monthly mortgage','2025-04-01','Completed'),
        (2,1,-450.00,'Debit','Utilities','Electricity & gas','2025-04-03','Completed'),
        (3,1,8500.00,'Credit','Salary','April salary','2025-04-05','Completed'),
        (4,2,5000.00,'Credit','Transfer','Savings deposit','2025-04-06','Completed'),
        (5,4,-120.50,'Debit','Groceries','Biedronka','2025-04-02','Completed'),
        (6,4,-89.99,'Debit','Entertainment','Netflix + Spotify','2025-04-04','Completed'),
        (7,4,3200.00,'Credit','Salary','April salary','2025-04-05','Completed'),
        (8,6,-1200.00,'Debit','Rent','April rent','2025-04-01','Completed'),
        (9,9,-3500.00,'Debit','Supplier Payment','Office supplies','2025-04-02','Completed'),
        (10,9,12000.00,'Credit','Invoice','Client payment','2025-04-08','Completed'),
        (11,11,-850.00,'Debit','Mortgage Payment','Monthly mortgage','2025-04-01','Completed'),
        (12,11,6800.00,'Credit','Salary','April salary','2025-04-05','Completed'),
        (13,14,-210.00,'Debit','Groceries','Weekly shopping','2025-04-03','Completed'),
        (14,15,-890.00,'Debit','Equipment','Server hardware','2025-04-04','Completed'),
        (15,19,-340.00,'Debit','Travel','Business flight','2025-04-06','Completed'),
        (16,1,-3200.00,'Debit','Tax','Quarterly VAT','2025-03-31','Completed'),
        (17,4,-55.00,'Debit','Transport','Monthly pass','2025-04-01','Completed'),
        (18,8,-620.00,'Debit','Rent','April rent','2025-04-01','Completed'),
        (19,10,2100.00,'Credit','Freelance','Consulting invoice','2025-04-07','Completed'),
        (20,17,-180.00,'Debit','Healthcare','Medical visit','2025-04-05','Completed'),
    ]
    c.executemany("INSERT OR IGNORE INTO transactions VALUES (?,?,?,?,?,?,?,?)", transactions)

    loans = [
        (1,1,'Mortgage',320000.00,285000.00,3.5,1850.00,'Active','2018-06-01','2048-06-01'),
        (2,2,'Personal',15000.00,9200.00,7.9,320.00,'Active','2022-01-15','2027-01-15'),
        (3,3,'Mortgage',650000.00,580000.00,2.8,2900.00,'Active','2016-03-01','2046-03-01'),
        (4,5,'Business',120000.00,95000.00,5.2,2200.00,'Active','2020-08-01','2028-08-01'),
        (5,6,'Mortgage',285000.00,241000.00,3.1,1640.00,'Active','2018-11-01','2043-11-01'),
        (6,7,'Mortgage',890000.00,720000.00,2.5,4200.00,'Active','2015-04-01','2045-04-01'),
        (7,9,'Personal',25000.00,18500.00,6.8,520.00,'Active','2021-03-01','2026-03-01'),
        (8,11,'Business',200000.00,165000.00,4.9,3800.00,'Active','2019-01-01','2029-01-01'),
        (9,12,'Auto',28000.00,19400.00,4.2,580.00,'Active','2020-09-01','2026-09-01'),
        (10,13,'Mortgage',750000.00,690000.00,2.2,3600.00,'Active','2014-12-01','2044-12-01'),
        (11,15,'Business',85000.00,72000.00,5.8,1620.00,'Active','2021-06-01','2028-06-01'),
        (12,4,'Personal',8000.00,6100.00,9.5,185.00,'Active','2023-01-01','2027-01-01'),
        (13,8,'Personal',5000.00,4800.00,11.2,130.00,'Overdue','2023-06-01','2026-06-01'),
        (14,10,'Auto',18000.00,14200.00,5.5,340.00,'Active','2022-04-01','2027-04-01'),
        (15,14,'Personal',12000.00,11500.00,8.9,260.00,'Active','2024-01-01','2028-01-01'),
    ]
    c.executemany("INSERT OR IGNORE INTO loans VALUES (?,?,?,?,?,?,?,?,?,?)", loans)

    cards = [
        (1,1,'Credit',10000.00,2340.00,'Active','2025-04-08','2018-03-12'),
        (2,1,'Debit',0,0,'Active','2025-04-09','2018-03-12'),
        (3,2,'Debit',0,0,'Active','2025-04-07','2020-07-04'),
        (4,2,'Credit',5000.00,890.00,'Active','2025-03-15','2021-01-10'),
        (5,3,'Credit',50000.00,12400.00,'Active','2025-04-08','2015-01-20'),
        (6,4,'Debit',0,0,'Active','2025-04-06','2022-11-08'),
        (7,5,'Credit',20000.00,8900.00,'Active','2025-04-05','2019-05-17'),
        (8,5,'Debit',0,0,'Active','2025-04-05','2019-05-17'),
        (9,6,'Credit',15000.00,3200.00,'Active','2025-04-04','2018-01-15'),
        (10,7,'Credit',100000.00,28500.00,'Active','2025-04-09','2014-06-14'),
        (11,8,'Debit',0,0,'Active','2025-04-03','2023-02-28'),
        (12,9,'Credit',30000.00,15600.00,'Active','2025-04-07','2019-05-17'),
        (13,10,'Debit',0,0,'Active','2025-04-02','2021-08-15'),
        (14,11,'Credit',25000.00,9800.00,'Active','2025-04-06','2019-01-20'),
        (15,12,'Credit',12000.00,4500.00,'Active','2025-04-08','2019-09-01'),
        (16,13,'Credit',75000.00,18900.00,'Active','2025-04-09','2014-06-14'),
        (17,14,'Debit',0,0,'Active','2025-04-01','2021-01-19'),
        (18,15,'Credit',18000.00,7200.00,'Active','2025-04-05','2020-06-27'),
    ]
    c.executemany("INSERT OR IGNORE INTO cards VALUES (?,?,?,?,?,?,?,?)", cards)

    branches = [
        (1,'Warsaw Central','Warsaw','Poland','Katarzyna Nowak'),
        (2,'Warsaw Mokotów','Warsaw','Poland','Marek Wiśniewski'),
        (3,'Kraków Main','Kraków','Poland','Anna Kowalczyk'),
        (4,'Berlin HQ','Berlin','Germany','Klaus Bauer'),
        (5,'Paris Centre','Paris','France','Élodie Moreau'),
    ]
    c.executemany("INSERT OR IGNORE INTO branches VALUES (?,?,?,?,?)", branches)


# ── Schema helper ──────────────────────────────────────────────────────────

def get_schema() -> str:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [r[0] for r in c.fetchall()]
    parts = []
    for t in tables:
        c.execute(f"PRAGMA table_info({t})")
        cols = c.fetchall()
        col_str = ", ".join(f"{col[1]} {col[2]}" for col in cols)
        c.execute(f"SELECT COUNT(*) FROM {t}")
        n = c.fetchone()[0]
        parts.append(f"TABLE {t} ({col_str})  -- {n} rows")
    conn.close()
    return "\n".join(parts)


def execute_sql(query: str) -> dict:
    query = query.strip().rstrip(';')
    if not re.match(r'^\s*SELECT\b', query, re.IGNORECASE):
        return {'error': 'Only SELECT queries are permitted.'}
    bad = ['DROP','DELETE','UPDATE','INSERT','ALTER','CREATE','TRUNCATE','EXEC']
    if any(k in query.upper() for k in bad):
        return {'error': 'Destructive SQL is not allowed.'}
    try:
        conn = sqlite3.connect(DB)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        t0 = time.time()
        c.execute(query)
        rows = c.fetchmany(500)
        elapsed = round((time.time() - t0) * 1000, 1)
        columns = [d[0] for d in c.description] if c.description else []
        data    = [dict(r) for r in rows]
        conn.close()
        return {'columns': columns, 'rows': data, 'count': len(data), 'elapsed': elapsed}
    except Exception as e:
        return {'error': str(e)}


# ── LangChain NL2SQL pipeline ──────────────────────────────────────────────

def build_chain(api_key: str):
    llm = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        anthropic_api_key=api_key,
        max_tokens=600,
    )

    sql_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert SQL engineer for a banking data platform.
Convert the user's natural language question into a precise SQLite SELECT query.

DATABASE SCHEMA:
{schema}

RULES:
- Output ONLY the raw SQL query — no explanation, no markdown, no backticks
- Use only SELECT statements
- Use proper JOINs when data spans multiple tables
- Use table aliases for clarity
- Add ORDER BY where it makes the result more useful
- Add LIMIT 100 unless the user asks for all data
- Dates are stored as TEXT in YYYY-MM-DD format
- For monetary amounts, round to 2 decimal places using ROUND()
- Column names are case-sensitive — use exactly as shown in the schema"""),
        ("human", "{question}")
    ])

    interpret_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a senior banking data analyst. 
Interpret the SQL query results and provide a clear, professional business insight.

Keep your interpretation:
- Concise (2-4 sentences max)
- Business-focused (not technical)
- Actionable where possible
- In the same language as the original question"""),
        ("human", """Original question: {question}

SQL query used:
{sql}

Query results ({count} rows):
{results}

Provide a brief business interpretation:""")
    ])

    sql_chain = (
        {"schema": lambda _: get_schema(), "question": RunnablePassthrough()}
        | sql_prompt
        | llm
        | StrOutputParser()
    )

    return sql_chain, llm, interpret_prompt


# ── Routes ─────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory('public', 'index.html')


@app.route('/api/schema')
def schema():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = {}
    for (t,) in c.fetchall():
        c.execute(f"PRAGMA table_info({t})")
        cols = [{'name': r[1], 'type': r[2]} for r in c.fetchall()]
        c.execute(f"SELECT COUNT(*) FROM {t}")
        tables[t] = {'columns': cols, 'rows': c.fetchone()[0]}
    conn.close()
    return jsonify({'tables': tables})


@app.route('/api/ask', methods=['POST'])
def ask():
    d        = request.get_json()
    api_key  = d.get('apiKey', '').strip()
    question = d.get('question', '').strip()

    if not api_key:  return jsonify({'error': 'API key required'}), 400
    if not question: return jsonify({'error': 'Question required'}), 400

    try:
        sql_chain, llm, interpret_prompt = build_chain(api_key)

        # Step 1: Generate SQL
        t0  = time.time()
        raw_sql = sql_chain.invoke(question)

        # Clean up any stray backticks
        sql = re.sub(r'```sql|```', '', raw_sql).strip()

        # Step 2: Execute SQL
        result = execute_sql(sql)
        if 'error' in result:
            # Auto-retry with error feedback
            retry_prompt = ChatPromptTemplate.from_messages([
                ("system", f"""You are an expert SQL engineer. Fix the SQL error below.
DATABASE SCHEMA:
{get_schema()}
Output ONLY the corrected SQL query, no explanation."""),
                ("human", f"Original question: {question}\nBroken SQL: {sql}\nError: {result['error']}\nFixed SQL:")
            ])
            fixed = (retry_prompt | llm | StrOutputParser()).invoke({})
            sql    = re.sub(r'```sql|```', '', fixed).strip()
            result = execute_sql(sql)

        if 'error' in result:
            return jsonify({'error': result['error'], 'sql': sql}), 400

        # Step 3: Interpret results
        preview = json.dumps(result['rows'][:10], indent=2) if result['rows'] else "No rows returned."
        interp_chain = interpret_prompt | llm | StrOutputParser()
        interpretation = interp_chain.invoke({
            'question': question,
            'sql':      sql,
            'count':    result['count'],
            'results':  preview,
        })

        ms = round((time.time() - t0) * 1000)

        return jsonify({
            'sql':            sql,
            'columns':        result['columns'],
            'rows':           result['rows'],
            'count':          result['count'],
            'elapsed_db':     result['elapsed'],
            'elapsed_total':  ms,
            'interpretation': interpretation,
        })

    except Exception as e:
        err = str(e)
        if 'authentication' in err.lower() or 'api_key' in err.lower():
            return jsonify({'error': 'Invalid API key'}), 401
        return jsonify({'error': err}), 500


@app.route('/api/execute', methods=['POST'])
def execute():
    """Direct SQL execution for manual queries."""
    d     = request.get_json()
    query = d.get('query', '').strip()
    if not query: return jsonify({'error': 'No query provided'}), 400
    result = execute_sql(query)
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)


@app.route('/api/status')
def status():
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    init_db()
    print("🏦 NL2SQL Banking Assistant running on http://localhost:5000")
    app.run(debug=False, port=5000)
