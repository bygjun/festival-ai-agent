import pandas as pd
from embedding import EmbeddingModel
from milvus_client import insert_embeddings
from utils import make_embedding_text
from config import *

df = pd.read_csv("data/festivals.csv")
embedding_model = EmbeddingModel(EMBEDDING_MODEL)

data = []
cnt = 0
for _, row in df.iterrows():
    text = make_embedding_text(row)
    embedding = embedding_model.get_embedding(text)
    data.append({"embedding": embedding, "embedding_text": text[:1024]})
    cnt += 1
    print(cnt)

insert_embeddings(MILVUS_COLLECTION, data)