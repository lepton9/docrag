import os


def _int(name: str, default: int) -> int:
    val = os.getenv(name)
    if val is None or val == "":
        return default
    return int(val)


# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
OPENAI_EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")

# Dir for saving data
DATA_DIR = os.getenv("DATA_DIR", "data")
USER_AGENT = os.getenv("USER_AGENT", "tim-rag/0.1")

# Max amount of pages to search from
MAX_PAGES = _int("MAX_PAGES", 50)
# Max depth for the pages
MAX_DEPTH = _int("MAX_DEPTH", 2)

# Chunk size for the embeds
CHUNK_SIZE = _int("CHUNK_SIZE", 1200)
# Overlap amount for chunks
CHUNK_OVERLAP = _int("CHUNK_OVERLAP", 200)
# Number of best hits to return from the index
TOP_K = _int("TOP_K", 6)
