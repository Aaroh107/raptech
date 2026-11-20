# Raptech: plain-English questions on a live database

Built during my SDE internship at Raptech AI (Jan to Jul 2025). Staff type a question in plain English, a local LLM turns it into SQL, and the answer comes straight from the live MariaDB data.

## How it works

1. **Streamlit UI** (`streamlitui2.py`): the user asks a question, e.g. "Which suppliers are in London?"
2. **FastAPI backend** (`apibackend2.py`, `POST /query`): reads the column names and types of the database view.
3. **LLM** (Llama 3 on Ollama): gets the question plus the schema and a strict prompt with one example, and replies with a single `SELECT` query.
4. The backend extracts the `SELECT` statement, rejects anything that isn't one, runs it on MariaDB and returns the rows.

This is a text-to-SQL pattern: the model answers from retrieved schema and live data rather than from memory.

## Run it

```bash
pip install fastapi uvicorn mariadb ollama streamlit pandas requests
cp .env.example .env      # fill in your own values, then export them in your shell
python main2.py           # starts the API on :8000 and the Streamlit UI on :8501
```

The LLM can run locally with Ollama, or on Google Colab through an ngrok tunnel (`collab notebook`, see `procedure`). The ngrok token is read from Colab secrets, never from the code.

## Safety notes

- Connect with a **read-only database user** that can only see the view.
- The backend only runs queries that start with `SELECT`.
- Ideas for a production version: block multiple statements, add a row limit and query timeout, and log every generated query.

## Stack

Python, FastAPI, Pydantic, MariaDB, Ollama (Llama 3), Streamlit
