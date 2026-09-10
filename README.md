# AI E-Commerce Customer Support Agent

An agentic AI customer support system for e-commerce. Instead of a rule-based
FAQ bot, this project uses Claude's tool-calling ability to let the model
**reason about a customer's request, retrieve grounded policy information,
and take real backend actions** (order lookup, return initiation, inventory
checks, human escalation) autonomously.

## Architecture

```
frontend/            Static chat widget (HTML/CSS/JS) — talks to the API
backend/
  main.py            FastAPI app — /chat and /reset endpoints
  agent.py           Agent core: Claude tool-calling loop + session memory
  tools.py           Tool implementations + JSON-schema tool definitions
  rag.py             Lightweight TF-IDF retrieval over the knowledge base
  data/
    orders.json          Mock order database
    inventory.json       Mock product/stock database
    knowledge_base/       Return/shipping policy + FAQ markdown docs (RAG source)
tests/
  test_agent.py       Unit tests for tools + RAG (no API key needed)
```

**Flow per message:** Perceive (user message) → Reason (Claude decides which
tool(s) to call) → Retrieve (RAG over policy docs) / Act (call order,
return, or inventory tools) → Respond, or Escalate to a human ticket if the
agent can't resolve it confidently.

## Prerequisites

- Python 3.10+
- An [Anthropic API key](https://console.anthropic.com/)

## Setup

```bash
git clone <your-repo-url>
cd ai-ecommerce-support-agent

# 1. Configure your API key
cp .env.example backend/.env
# edit backend/.env and paste your ANTHROPIC_API_KEY

# 2. Install backend dependencies
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Run the API server
python main.py
# Server runs at http://localhost:8000
```

## Run the frontend

The frontend is static — no build step required. In a separate terminal:

```bash
cd frontend
python -m http.server 5500
# Open http://localhost:5500 in your browser
```

## Try it

Example things to type into the chat widget:

- "Where is my order ORD-10234?"
- "I want to return order ORD-10236, the pan set arrived scratched."
- "Is the Smart Fitness Watch in stock?"
- "What's your return policy?"
- "I want to speak to a human agent."

## Running tests

```bash
cd backend
pip install pytest
pytest ../tests/
```

These tests exercise the tools and RAG retrieval directly and don't require
an API key.

## API

### `POST /chat`

```json
{
  "session_id": "abc-123",
  "message": "Where is my order ORD-10234?"
}
```

Response:

```json
{
  "session_id": "abc-123",
  "reply": "Your order ORD-10234 has shipped via BlueDart...",
  "escalated": false,
  "tool_calls": [{ "tool_name": "get_order_status", "tool_input": { "order_id": "ORD-10234" } }]
}
```

### `POST /reset`

Clears a session's conversation memory.

## Notes on production hardening

This is a reference/demo implementation. Before deploying to production:

- Replace the JSON files in `backend/data/` with real order/inventory/ticketing
  system integrations (REST/GraphQL calls, not local file reads).
- Replace the TF-IDF `KnowledgeBase` in `rag.py` with a real embeddings model
  and a vector database (e.g. Pinecone, Chroma, pgvector) for better recall
  at scale.
- Replace in-memory session storage in `agent.py` with Redis or a database,
  and add authentication so `session_id` can't be spoofed.
- Add rate limiting, logging/observability, and PII redaction before logging
  conversations.
- Add a real ticketing system integration (Zendesk, Freshdesk, etc.) in place
  of `tickets.json` for `escalate_to_human`.

## License

MIT — use freely for learning or as a starting point for your own project.

---

## VS Code + Ollama la run panni, GitHub-ku push panna Guide (Tanglish)

Idhu step-by-step guide — VS Code la open panni, **Ollama (local LLM, free, no API
key)** use panni run panniddu, appuram GitHub repo-ku push panradhu eppadi nu.

### Step 1 — Ollama install pannunga

1. https://ollama.com ku poi, un OS (Windows/Mac/Linux) ku ஏத்த installer download panni run pannunga.
2. Install aana apparam, terminal la இதை run pannunga, server start aagum:
   ```bash
   ollama serve
   ```
   (Mac/Windows la ithu background la automatic aa already run aayirukum — separate terminal open pannitu run panna check pannunga.)
3. Vera oru terminal la, tool-calling support panra model ஒண்ணு pull pannunga:
   ```bash
   ollama pull llama3.1
   ```
   (Idhu ~4.7GB download aagum. Konjam weak system na `ollama pull qwen2.5:7b` nu smaller model try pannunga.)

### Step 2 — Project-ah VS Code la open pannunga

1. Zip-ah extract pannunga, appram VS Code open pannitu **File → Open Folder** → `ai-ecommerce-support-agent` folder select pannunga.
2. VS Code la **Python extension** (Microsoft official) install pannunga, illa na irundha — Extensions tab (Ctrl+Shift+X) la "Python" search pannunga.
3. VS Code Terminal open pannunga: **Terminal → New Terminal** (or `` Ctrl+` ``).

### Step 3 — `.env` file setup (Ollama mode ku switch pannunga)

VS Code terminal la:

```bash
cp .env.example backend/.env
```

Appuram `backend/.env` file-ah VS Code la open panni (left sidebar la double-click), idha maathunga:

```
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.1
```

(`ANTHROPIC_API_KEY` line-ah touch pannaadheenga — Ollama mode use pannumbodhu adhu vேண்டாம், unmodified irundhalum problem illa.)

### Step 4 — Python virtual environment + dependencies

VS Code terminal la (backend folder ku poganum):

```bash
cd backend
python -m venv venv
```

Terminal-ah activate pannunga:
- **Windows:** `venv\Scripts\activate`
- **Mac/Linux:** `source venv/bin/activate`

Activate aana apparam terminal prompt front la `(venv)` nu varum. Appuram:

```bash
pip install -r requirements.txt
```

VS Code oru popup kaatum "Select interpreter" nu — antha `venv` folder interpreter-ah select pannunga (bottom-right corner la kuda click panni select pannalaam).

### Step 5 — Server run pannunga

Same terminal la (venv activate aana state la):

```bash
python main.py
```

Idhu output la `Uvicorn running on http://0.0.0.0:8000` nu varum. Adhukku apparam
browser la `http://localhost:8000/health` open pannitu check pannunga — response la
`"llm_provider": "ollama"` nu kaatanum.

> **VS Code shortcut:** Run/Debug ku F5 kuda use pannalam — `backend/main.py` file open pannitu F5 press pannunga, VS Code automatic aa run pannidum (`launch.json` venum na kekungo).

### Step 6 — Frontend run pannunga

VS Code la **oru puthu terminal split pannunga** (terminal panel top-right la "+" button):

```bash
cd frontend
python -m http.server 5500
```

Browser la `http://localhost:5500` open pannunga — chat widget varum. "Where is my
order ORD-10234?" nu type pannitu try pannunga — Ollama local model-ah use panni
agent reply pannum, tool calls (order lookup etc.) console la `tool-tag` aa kaatum.

**Note:** Local models (especially chinna size ones) tool-calling la Claude/GPT
mathiri consistent aa irukaadhu sila times — model correct-ah tool call panala na,
`llama3.1` ku badhilaa `qwen2.5:14b` mathiri periya model try pannunga (`ollama pull
qwen2.5:14b`), adhu tool-calling la better perform pannum.

### Step 7 — GitHub-ku push pannunga (VS Code UI use panni)

1. VS Code left sidebar la **Source Control icon** (branch icon, 3rd from top) click pannunga.
2. "Initialize Repository" button irundha click pannunga (git init pannidum).
3. `.gitignore` already `.env` ah ignore pannuduchu — so key/secret accidental aa push aagadhu, worry venaam.
4. Changes list la irukra files ellaam "+" click panni stage pannunga (illa "Stage All Changes" button use pannunga).
5. Top la commit message box la type pannunga: `Initial commit: AI e-commerce support agent`, appuram ✓ (Commit) click pannunga.
6. Appuram **"Publish Branch"** button varum (or "..." menu → "Push") — adha click pannunga.
7. VS Code GitHub login kekkum first time na — browser open aagi authorize pannachu solli, appuram repo name kekkum, type pannitu create pannunga (public/private select pannalam).

Command line vaenumna:

```bash
git init
git add .
git commit -m "Initial commit: AI e-commerce support agent"
git branch -M main
git remote add origin https://github.com/<your-username>/ai-ecommerce-support-agent.git
git push -u origin main
```

Ready! Ippo un repo GitHub la irukku, `LLM_PROVIDER=ollama` set panni free-ah local
la run pannalam, or `LLM_PROVIDER=anthropic` set panni Claude API kooda use
pannalam — code same-ah irukkum, `.env` la oru line maathradhu than vithyasam.
