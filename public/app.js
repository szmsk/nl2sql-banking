'use strict';

let isAsking = false;

const EXAMPLES = [
  "Which customers have loans over 100,000 with an active status?",
  "Show total transaction volume by category",
  "Which Premium segment customers have the highest credit card utilisation?",
  "Compare average loan amounts across different customer segments",
  "List all overdue or defaulted loans with customer names",
  "Show customers with both a mortgage and a credit card",
  "What is the average account balance by account type?",
  "Which customers have made more than 2 transactions this month?",
  "Show top 5 customers by total loan outstanding amount",
  "List all customers from Poland with their total balance across all accounts",
];

window.addEventListener('DOMContentLoaded', () => {
  loadSchema();
  renderExamples();
});

function toggleKey() {
  const i = document.getElementById('apiKey');
  i.type = i.type === 'password' ? 'text' : 'password';
}

// ── Schema ─────────────────────────────────────────────────────────────────
async function loadSchema() {
  try {
    const res  = await fetch('/api/schema');
    const data = await res.json();
    renderSchema(data.tables);
  } catch {
    document.getElementById('schemaTree').innerHTML =
      '<div style="color:var(--text3);font-size:11px">Could not load schema</div>';
  }
}

function renderSchema(tables) {
  const tree = document.getElementById('schemaTree');
  tree.innerHTML = Object.entries(tables).map(([name, info]) => `
    <div class="schema-table">
      <div class="schema-table-hdr" onclick="this.nextElementSibling.classList.toggle('open')">
        <span>${name}</span>
        <span class="row-count">${info.rows} rows</span>
      </div>
      <div class="schema-cols">
        ${info.columns.map(c => `
          <div class="schema-col">
            <span class="col-name">${c.name}</span>
            <span class="col-type">${c.type}</span>
          </div>`).join('')}
      </div>
    </div>`
  ).join('');
}

// ── Examples ───────────────────────────────────────────────────────────────
function renderExamples() {
  document.getElementById('exampleList').innerHTML = EXAMPLES.map(q =>
    `<button class="ex-btn" onclick="fillQ(${JSON.stringify(q)})">${q}</button>`
  ).join('');
}

function fillQ(q) {
  document.getElementById('qInput').value = q;
  autoResize(document.getElementById('qInput'));
  document.getElementById('qInput').focus();
  ask();
}

// ── Ask ────────────────────────────────────────────────────────────────────
async function ask() {
  if (isAsking) return;
  const apiKey = document.getElementById('apiKey').value.trim();
  const q      = document.getElementById('qInput').value.trim();
  if (!apiKey) return alert('Please enter your Anthropic API key.');
  if (!q)      return;

  document.getElementById('qInput').value = '';
  autoResize(document.getElementById('qInput'));
  clearWelcome();
  addUserMsg(q);
  const thinkId = addThinking();

  isAsking = true;
  document.getElementById('sendBtn').disabled = true;
  document.getElementById('sendBtn').innerHTML = '<span class="spin"></span>';

  try {
    const res  = await fetch('/api/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ apiKey, question: q }),
    });
    const data = await res.json();
    removeEl(thinkId);

    if (!res.ok) addErrMsg(data.error, data.sql);
    else         addResultMsg(data);

  } catch (err) {
    removeEl(thinkId);
    addErrMsg(err.message);
  }

  isAsking = false;
  document.getElementById('sendBtn').disabled = false;
  document.getElementById('sendBtn').innerHTML = '↑';
}

// ── Render ─────────────────────────────────────────────────────────────────
function clearWelcome() {
  document.getElementById('welcomeMsg')?.remove();
}

function addUserMsg(text) {
  const id = uid();
  append(`<div class="msg user" id="${id}">
    <div class="msg-av">SK</div>
    <div class="msg-body"><div class="bubble">${esc(text)}</div></div>
  </div>`);
}

function addThinking() {
  const id = uid();
  append(`<div class="msg bot" id="${id}">
    <div class="msg-av">🏦</div>
    <div class="msg-body">
      <div class="thinking">
        <span class="tdots"><span></span><span></span><span></span></span>
        Generating SQL with LangChain…
      </div>
    </div>
  </div>`);
  return id;
}

function addResultMsg(data) {
  const id = uid();
  let parts = '';

  // SQL block
  if (data.sql) {
    const cid = uid();
    parts += `
      <div class="sql-block">
        <div class="sql-hdr">
          <div class="sql-hdr-left">
            <span class="sql-dot"></span>
            <span>LangChain · Generated SQL</span>
          </div>
          <button class="sql-copy" onclick="copySql('${cid}')">copy</button>
        </div>
        <div class="sql-body" id="${cid}">${esc(data.sql)}</div>
      </div>`;
  }

  // Result table
  if (data.rows && data.columns) {
    parts += `
      <div class="result-wrap">
        <div class="result-hdr">
          <span class="result-meta">${data.count} row${data.count !== 1 ? 's' : ''} · ${data.elapsed_db}ms query</span>
          <span class="result-meta">${data.elapsed_total}ms total</span>
        </div>
        ${data.count > 0 ? `
        <div class="tbl-scroll">
          <table>
            <thead><tr>${data.columns.map(c => `<th>${esc(c)}</th>`).join('')}</tr></thead>
            <tbody>${data.rows.map(row =>
              `<tr>${data.columns.map(col => {
                const v = row[col];
                return v == null
                  ? `<td><span class="null-val">NULL</span></td>`
                  : `<td title="${esc(String(v))}">${esc(String(v))}</td>`;
              }).join('')}</tr>`
            ).join('')}</tbody>
          </table>
        </div>` : '<div style="padding:14px;color:var(--text3);font-size:12px">No rows returned.</div>'}
      </div>`;
  }

  // Interpretation
  if (data.interpretation) {
    parts += `
      <div class="interp-box">
        <div class="interp-label">💡 Business Insight</div>
        ${esc(data.interpretation)}
      </div>`;
  }

  append(`<div class="msg bot" id="${id}">
    <div class="msg-av">🏦</div>
    <div class="msg-body">${parts}</div>
  </div>`);
}

function addErrMsg(msg, sql) {
  const id = uid();
  let parts = `<div class="err-box">⚠ ${esc(msg)}</div>`;
  if (sql) parts += `<div class="sql-block"><div class="sql-hdr"><div class="sql-hdr-left"><span class="sql-dot" style="background:var(--red)"></span><span>Failed SQL</span></div></div><div class="sql-body">${esc(sql)}</div></div>`;
  append(`<div class="msg bot" id="${id}">
    <div class="msg-av">🏦</div>
    <div class="msg-body">${parts}</div>
  </div>`);
}

function append(html) {
  const el   = document.createElement('div');
  el.innerHTML = html;
  const msgs = document.getElementById('messages');
  msgs.appendChild(el.firstElementChild);
  msgs.scrollTop = msgs.scrollHeight;
}

function removeEl(id) { document.getElementById(id)?.remove(); }

function copySql(id) {
  navigator.clipboard.writeText(document.getElementById(id)?.innerText || '');
}

// ── Utils ──────────────────────────────────────────────────────────────────
function uid() { return 'm' + Math.random().toString(36).slice(2, 9); }
function esc(s) {
  return String(s||'')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;')
    .replace(/\n/g,'<br>');
}
function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 100) + 'px';
}
function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); ask(); }
}
