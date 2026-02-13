# docrag
A basic Retrieval-Augmented Generation (RAG) implementation that answers 
questions using data fetched from specified web pages.


## Run with python

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python app/server.py --reload
```

## Run with Docker

```bash
docker compose up --build
```

