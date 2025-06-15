from pymilvus import MilvusClient

uri = "https://in03-6bcec74b22350c4.serverless.gcp-us-west1.cloud.zilliz.com"
token = "07d8e7ef9ae8a93a1148e1f4797ab2ffdd7b4cbba8bde8e1b2adb7c1912d01db24017df69b5608323433bdbdb4cb51ca490c3d81"

client = MilvusClient(
    uri=uri,
    token=token,
)
def search_festivals(collection, query_embedding, top_k=5):
    results = client.search(
        collection_name=collection,
        data=[query_embedding],
        limit=top_k,
        output_fields=["primary_key", "embedding_text", "address", "festival_name", "lon", "lat"]
    )
    return results