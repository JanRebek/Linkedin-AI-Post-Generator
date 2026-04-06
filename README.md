# 💼 LinkedIn AI Post Generator

**Turn AI trends into ready-to-publish LinkedIn posts in seconds** — powered by a 4-stage multi-agent pipeline built on Claude claude-sonnet-4-6.

---

## What it does

The app runs a sequential AI pipeline every time you hit Generate:

1. **🔍 Discovery** — Claude searches YouTube, GitHub, Reddit, HackerNews, Twitter/X, and the broader web for the freshest content on your chosen topic.
2. **📄 Summarization** — Extracts the key insight, supporting facts, and the most compelling narrative angle.
3. **✓ Fact-check** — Runs the top 3 claims back through web search to verify accuracy before you publish.
4. **✍️ Writing** — Crafts a polished LinkedIn post in your chosen voice (Thought Leader, Educator, Practitioner, or Contrarian), with 3 alternative opening hooks and suggested hashtags.

Results are shown in four tabs: **Post Draft**, **Alternatives**, **Fact Check**, and **Sources**.

---

## UI Overview

```
┌─────────────────────────────────────────────────────────┐
│ Sidebar                    │ Main area                   │
│ ─ App title + tagline      │ ─ Card 1: Topic             │
│ ─ Anthropic API Key        │ ─ Card 2: Sources           │
│ ─ YouTube API Key          │ ─ Card 3: Writing Style     │
│ ─ About section            │ ─ Card 4: Creator style     │
│                            │ ─ Generate button           │
│                            │ ─ Live progress (st.status) │
│                            │ ─ Result tabs               │
└─────────────────────────────────────────────────────────┘
```

---

## Setup

### 1. Clone / download

```bash
git clone https://github.com/YOUR_USERNAME/linkedin-post-generator.git
cd linkedin-post-generator
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Get your Anthropic API key

Go to [console.anthropic.com](https://console.anthropic.com), create an account, and generate an API key.
You'll be asked to enter it directly in the app's sidebar (it's never stored anywhere).

Alternatively, set it as an environment variable:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

The app will automatically pick it up.

### 4. Run

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`.

---

## YouTube API Key (optional)

For direct YouTube search:
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project → Enable the **YouTube Data API v3**
3. Create an API key under **Credentials**
4. Enter it in the app sidebar

Without a YouTube key, Claude still searches YouTube via general web search — the key just enables more targeted video discovery.

---

## Deploy to Streamlit Community Cloud

1. Push this repo to GitHub (public or private).
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. Click **New app** → select your repo → set `app.py` as the main file.
4. Under **Advanced settings → Secrets**, add:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   ```
5. Click **Deploy**. Your app will be live at `https://YOUR_APP.streamlit.app`.

The app reads `ANTHROPIC_API_KEY` from environment variables automatically, so users of your deployed app can just start generating without entering a key (if you pre-configure it as a secret).

---

## Project structure

```
linkedin_post_app/
├── app.py              # Streamlit UI
├── pipeline.py         # 4-stage multi-agent pipeline
├── requirements.txt    # Python dependencies
├── README.md           # This file
└── .streamlit/
    └── config.toml     # LinkedIn blue theme
```

---

## Model & tools used

- **Model:** `claude-sonnet-4-6`
- **Web search:** Native `web_search_20250305` tool (built into claude-sonnet-4-6 — no external search API needed)
- **Framework:** Streamlit 1.32+

---

## License

MIT — use freely, modify, deploy, share.
