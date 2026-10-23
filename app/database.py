import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(override=True)

# ============================================================
# DATABASE CONFIGURATION
# ============================================================

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME", "neondb")
DB_USER = os.getenv("DB_USER", "neondb_owner")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = os.getenv("DB_PORT", "5432")


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT,
        sslmode="require"
    )


# ============================================================
# CONNECTION TEST
# ============================================================

if __name__ == "__main__":
    try:
        conn = get_connection()
        print("Neon PostgreSQL connection successful!")
        conn.close()
    except Exception as e:
        print("Database connection failed!")
        print(f"Error: {e}")