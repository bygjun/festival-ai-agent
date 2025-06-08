import os
from dotenv import load_dotenv
load_dotenv()

MILVUS_COLLECTION = "festival_embeddings"
EMBEDDING_MODEL = "BAAI/bge-m3"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
