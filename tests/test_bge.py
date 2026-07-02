from app.config import settings
from app.rag.loader import EmbeddingModel

embedding_model = EmbeddingModel(model_name=settings.embedding_model)
embedding = embedding_model.embed(["我喜欢美食和慢生活"])

print("向量类型：", type(embedding))
print("向量维度：", embedding.shape)
print("前10个数：", embedding[:10])
