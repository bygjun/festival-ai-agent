from flask import Flask, request, jsonify
from embedding import EmbeddingModel
from retriever import search_festivals
from prompt import build_system_message, build_assistant_message
import openai
from config import *

app = Flask(__name__)
embedding_model = EmbeddingModel(EMBEDDING_MODEL)
openai.api_key = OPENAI_API_KEY

@app.route("/search", methods=["GET"])
def search():
    try:
        user_query = request.json.get("query", "").strip()[:512]
        query_embedding = embedding_model.get_embedding(user_query)
        results = search_festivals(MILVUS_COLLECTION, query_embedding)
        festivals = [r.entity for r in results]
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
        return jsonify({"result": result_part, "festivals": festivals})
    except Exception as e:
        return jsonify({"error": str(e)}), 500