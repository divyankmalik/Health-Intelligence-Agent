# 🩺 HIA (Health Insights Agent)

AI Agent to analyze blood reports and provide detailed health insights.

<p align="center">
  <a href="https://github.com/harshhh28/hia/issues"><img src="https://img.shields.io/github/issues/harshhh28/hia"></a> 
  <a href="https://github.com/harshhh28/hia/stargazers"><img src="https://img.shields.io/github/stars/harshhh28/hia"></a>
  <a href="https://github.com/harshhh28/hia/network/members"><img src="https://img.shields.io/github/forks/harshhh28/hia"></a>
  <a href="https://github.com/harshhh28/hia/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-blue.svg">
  </a>
</p>

<p align="center">
  <a href="#-features">Features</a> |
  <a href="#%EF%B8%8F-tech-stack">Tech Stack</a> |
  <a href="#-installation">Installation</a> |
  <a href="#-project-structure">Project Structure</a> |
  <a href="#-contributing">Contributing</a> |
  <a href="#%EF%B8%8F-author">Author</a>
</p>



## 🌟 Features

- **Agent-based architecture**
  - **Analysis Agent**: Report analysis with in-context learning from previous analyses and a built-in knowledge base
  - **Chat Agent**: RAG-powered follow-up Q&A over your report (FAISS + HuggingFace embeddings)
- **Multi-model cascade** via Groq with automatic fallback (primary → secondary → tertiary → fallback)
- **Chat sessions**: Create multiple analysis sessions; each session stores report, analysis, and follow-up messages in Supabase
- **Report sources**: Upload your own PDF or use the built-in sample report for quick testing
- **PDF handling**: Upload up to 20MB, max 50 pages; validation for file type and medical-report content
- **Daily analysis limit**: Configurable cap (default 15/day) with countdown in the sidebar
- **Secure auth**: Supabase Auth (sign up / sign in), session validation, and configurable session timeout
- **Session history**: View, switch, and delete past sessions; report text persisted for follow-up chat across reloads
- **Modern UI**: Responsive Streamlit app with sidebar session list, user greeting, and real-time feedback

## 🛠️ Tech Stack

- **Frontend**: Streamlit (1.42+)
- **AI / LLM**
  - **Report analysis**: Groq with multi-model fallback via `ModelManager`
    - Primary: `meta-llama/llama-4-maverick-17b-128e-instruct`
    - Secondary: `llama-3.3-70b-versatile`
    - Tertiary: `llama-3.1-8b-instant`
    - Fallback: `llama3-70b-8192`
  - **Follow-up chat**: RAG with LangChain, HuggingFace embeddings (`all-MiniLM-L6-v2`), FAISS vector store, and Groq (`llama-3.3-70b-versatile`)
- **Database**: Supabase (PostgreSQL)
  - Tables: `users`, `chat_sessions`, `chat_messages`
- **Auth**: Supabase Auth, Gotrue
- **PDF**: PDFPlumber (text extraction), filetype (file validation)
- **Libraries**: LangChain, LangChain Community, LangChain HuggingFace, LangChain Text Splitters, sentence-transformers, FAISS (CPU)

## 🚀 Installation

#### Requirements 📋

- Python 3.8+
- Streamlit 1.42+
- Supabase account
- Groq API key
- PDFPlumber, filetype

#### Getting Started 📝

1. Clone the repository:

```bash
git clone [https://github.com/harshhh28/hia.git](https://github.com/divyankmalik/Health-Intelligence-Agent)
cd hia
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Required environment variables (in `.streamlit/secrets.toml`):

```toml
SUPABASE_URL = "your-supabase-url"
SUPABASE_KEY = "your-supabase-key"
GROQ_API_KEY = "your-groq-api-key"
```

4. Set up Supabase database schema:

The application uses three tables: `users`, `chat_sessions`, and `chat_messages`. Use the SQL script at `public/db/script.sql` to create them.

![database schema](https://raw.githubusercontent.com/harshhh28/hia/main/public/db/schema.png)

(You can turn off email confirmation on signup in Supabase: **Authentication → Providers → Email → Confirm email**.)

5. Run the application:

```bash
streamlit run src\main.py
```

## 📁 Project Structure

```
hia/
├── requirements.txt
├── README.md
├── src/
│   ├── main.py                 # Application entry point; chat UI and session flow
│   ├── auth/
│   │   ├── auth_service.py     # Supabase auth, sessions, chat message persistence
│   │   └── session_manager.py # Session init, timeout, create/delete chat sessions
│   ├── components/
│   │   ├── analysis_form.py    # Report source (upload/sample), patient form, analysis trigger
│   │   ├── auth_pages.py       # Login / signup pages
│   │   ├── footer.py           # Footer component
│   │   ├── header.py           # User greeting
│   │   └── sidebar.py          # Session list, new session, daily limit, logout
│   ├── config/
│   │   ├── app_config.py       # App name, limits (upload, pages, analysis, timeout)
│   │   ├── prompts.py          # Specialist prompts for report analysis
│   │   └── sample_data.py      # Sample blood report for "Use Sample PDF"
│   ├── services/
│   │   └── ai_service.py       # Analysis + chat entry points; vector store caching
│   ├── agents/
│   │   ├── analysis_agent.py   # Report analysis, rate limits, knowledge base, in-context learning
│   │   ├── chat_agent.py       # RAG pipeline (embeddings, FAISS, query contextualization)
│   │   └── model_manager.py   # Groq multi-model cascade and fallback
│   └── utils/
│       ├── validators.py       # Email, password, PDF file and content validation
│       └── pdf_extractor.py   # PDF text extraction and validation
├── public/
│   └── db/
│       ├── script.sql          # Supabase schema (users, chat_sessions, chat_messages)
│       └── schema.png          # Schema diagram
```

## 👥 Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) for details on how to submit pull requests, the development workflow, coding standards, and more.

We appreciate all contributions, from reporting bugs and improving documentation to implementing new features.






