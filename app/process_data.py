import pandas as pd
from embedding import EmbeddingModel
from milvus_client import insert_embeddings
from utils import make_embedding_text
from config import *

df = pd.read_csv("data/festivals.csv")
embedding_model = EmbeddingModel(EMBEDDING_MODEL)

cnt = 0
data = []   
for _, row in df.iterrows():
    text = make_embedding_text(row)
    embedding = embedding_model.get_embedding(text)
    data.append({
        "embedding": embedding,
        "embedding_text": text[:1024],
        "address": row['RDNMADR_NM'] if pd.notna(row['RDNMADR_NM']) else '',
        "festival_name": row['FCLTY_NM'] if pd.notna(row['FCLTY_NM']) else '',
        "lon": row['FCLTY_LO'] if pd.notna(row['FCLTY_LO']) else '',
        "lat": row['FCLTY_LA'] if pd.notna(row['FCLTY_LA']) else ''
    })
    cnt += 1
    print(cnt)
insert_embeddings(MILVUS_COLLECTION, data)
