import psycopg2
import sys

# User provided credentials in the recent edit
# Host 5432 (Standard Local Port), NOT 5433 (Docker)
DB_URL = "postgresql://postgres:deb172006@localhost:5432/teamchat"

try:
    print(f"Attempting connection to: {DB_URL}")
    conn = psycopg2.connect(DB_URL)
    conn.close()
    print("SUCCESS: Connected to Local Postgres on 5432 with provided credentials.")
    sys.exit(0)
except psycopg2.OperationalError as e:
    print(f"FAILED: Could not connect to Local Postgres. Error: {e}")
    # try 5433 just in case
    try:
        DB_URL_DOCKER = "postgresql://postgres:deb172006@localhost:5433/teamchat"
        print(f"Attempting connection to: {DB_URL_DOCKER}")
        conn = psycopg2.connect(DB_URL_DOCKER)
        conn.close()
        print("SUCCESS: Connected to Postgres on 5433.")
        sys.exit(0)
    except Exception as e2:
        print(f"FAILED: Also failed on 5433. Error: {e2}")
        sys.exit(1)
