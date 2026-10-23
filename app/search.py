import os

from google import genai
from google.genai import types
from dotenv import load_dotenv

from app.database import get_connection


# ==========================================
# LOAD ENVIRONMENT VARIABLES
# ==========================================

load_dotenv()


# ==========================================
# GEMINI EMBEDDING CLIENT
# ==========================================

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


# ==========================================
# CREATE QUERY EMBEDDING
# ==========================================

def create_query_embedding(query):
    """
    Create a Gemini embedding for the user's query.
    """

    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=query,
        config=types.EmbedContentConfig(
            output_dimensionality=EMBEDDING_DIMENSION
        )
    )

    return result.embeddings[0].values


# ==========================================
# SEARCH FUNCTION
# ==========================================

def search_policies(query, top_k=3):

    # --------------------------------------
    # Create Gemini embedding for query
    # --------------------------------------

    query_embedding = create_query_embedding(query)


    # --------------------------------------
    # Connect to PostgreSQL
    # --------------------------------------

    conn = get_connection()
    cursor = conn.cursor()


    # --------------------------------------
    # pgvector similarity search
    # --------------------------------------

    cursor.execute(
        """
        SELECT
            policy_id,
            category,
            title,
            content,
            1 - (embedding <=> %s::vector) AS similarity
        FROM hr_policies
        ORDER BY embedding <=> %s::vector
        LIMIT %s;
        """,
        (
            query_embedding,
            query_embedding,
            top_k
        )
    )


    results = cursor.fetchall()
    print("DEBUG: Raw results:", results[:1])
print("DEBUG: Cursor column names:", [col[0] for col in cursor.description])

    cursor.close()
    conn.close()


    # --------------------------------------
    # Convert results into dictionaries
    # --------------------------------------

    policies = []

    for result in results:

        policy_id, category, title, content, similarity = result

        policies.append({
            "policy_id": policy_id,
            "category": category,
            "title": title,
            "content": content,
            "score": float(similarity)
        })


    return policies


# ==========================================
# TEST SEARCH
# ==========================================

if __name__ == "__main__":

    question = input(
        "\nAsk an HR policy question: "
    )


    results = search_policies(question)


    print("\n==========================================")
    print("SEARCH RESULTS")
    print("==========================================\n")


    for i, result in enumerate(results):

        print(f"Result {i + 1}")
        print("------------------------------------------")

        print("Policy ID:", result["policy_id"])
        print("Category:", result["category"])
        print("Title:", result["title"])

        print(
            "Similarity Score:",
            round(result["score"], 4)
        )

        print("Content:", result["content"])

        print()