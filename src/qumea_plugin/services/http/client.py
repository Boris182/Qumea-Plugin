import httpx

def create_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=10.0)