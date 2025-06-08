from flask import Flask, request, jsonify
from app.embedding import EmbeddingModel
from app.retriever import search_festivals
from app.prompt import build_system_message, build_assistant_message
import openai
from app.config import *

embedding_model = EmbeddingModel(EMBEDDING_MODEL)
openai.api_key = OPENAI_API_KEY
print(OPENAI_API_KEY)

def search():
    user_query = "서울에서 먹거리 축제 알려줘"
    query_embedding = embedding_model.get_embedding(user_query)
    results = search_festivals(MILVUS_COLLECTION, query_embedding, 150)
    print(results)
    festivals = [r.get('entity') for r in results[0]]
    system_msg = build_system_message()
    assistant_msg = build_assistant_message(festivals, user_query)
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "assistant", "content": assistant_msg}
    ]
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=messages
    )
    answer = response["choices"][0]["message"]["content"]
    result_part = answer.split("결과:")[-1].strip()
    print(result_part)
    
    

if __name__ == "__main__":
    search()