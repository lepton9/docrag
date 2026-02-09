# chat-rag
A basic Retrieval-Augmented Generation (RAG) implementation that answers 
questions using data fetched from specified web pages.


## Running

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.server:app --reload
```

## Run with Docker

```bash
docker compose up --build
```

