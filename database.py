import os
from supabase import create_client

def get_db():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SECRET_KEY")
    return create_client(url, key)
