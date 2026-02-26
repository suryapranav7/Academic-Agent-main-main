import os
from supabase import create_client, Client
from dotenv import load_dotenv
import httpx

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_ANON_KEY")

if not url or not key:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_ANON_KEY in environment variables.")

# --- MONKEY PATCH: FORCE HTTP/1.1 ---
# Fixes 'httpcore.RemoteProtocolError: Server disconnected' on Windows/Threaded envs.
# Supabase-py enables HTTP/2 by default, which can be unstable in this setup.
_original_client_init = httpx.Client.__init__

def _patched_client_init(self, *args, **kwargs):
    # Force disable http2
    kwargs["http2"] = False
    _original_client_init(self, *args, **kwargs)

httpx.Client.__init__ = _patched_client_init
# -----------------------------------

# Singleton instance
supabase: Client = create_client(url, key)

def get_supabase() -> Client:
    return supabase
