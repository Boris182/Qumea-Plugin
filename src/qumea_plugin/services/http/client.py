import httpx

def create_http_client(config: dict | None = None) -> httpx.AsyncClient:
    cfg = {
        "timeout": 10.0,
        "http_base_url": None,
        "verify_ssl": True,
    }
    if config:
        cfg.update(config)

    return httpx.AsyncClient(
        timeout=cfg["timeout"],
        base_url=cfg["http_base_url"],
        verify=cfg["verify_ssl"],
    )
