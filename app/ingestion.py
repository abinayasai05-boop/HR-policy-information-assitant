import os
import pandas as pd
from google import genai
from google.genai import types
from dotenv import load_dotenv

from app.database import get_connection

load_dotenv()

print("Initializing Gemini Embedding 2...")

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

EMBEDDING_MODEL = os.getenv(
    "GEMINI_EMBEDDING_MODEL",
    "gemini-embedding-2"
)

EMBEDDING_DIMENSION = int(
    os.getenv(
        "EMBEDDING_DIMENSION",
        "768"
    )
)

print("Gemini Embedding 2 initialized successfully!")
print(f"Embedding model: {EMBEDDING_MODEL}")
print(f"Embedding dimension: {EMBEDDING_DIMENSION}")


def create_embedding(text):

    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            output_dimensionality=EMBEDDING_DIMENSION
        )
    )

    return result.embeddings[0].values


df = pd.read_csv("data/hr_policies.csv")

print("\nHR Policy Dataset Loaded Successfully!")
print(f"Number of policies: {len(df)}")

conn = get_connection()
cursor = conn.cursor()

for _, row in df.iterrows():

    text = (
        f"title: {row['title']} | "
        f"text: {row['content']}"
    )

    print(
        f"Creating Gemini embedding for "
        f"{row['policy_id']} - {row['title']}"
    )

    embedding = create_embedding(text)

    print(f"Embedding dimension: {len(embedding)}")

    cursor.execute(
        """
        INSERT INTO hr_policies
        (policy_id, category, title, content, embedding)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            row["policy_id"],
            row["category"],
            row["title"],
            row["content"],
            embedding
        )
    )

conn.commit()

cursor.close()
conn.close()

print("\nAll HR policies inserted successfully!")
print("Gemini embeddings stored in PostgreSQL + pgvector.")
print(f"Embedding dimension: {EMBEDDING_DIMENSION}")