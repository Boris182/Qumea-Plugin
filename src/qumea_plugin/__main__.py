import os
import sys
import asyncio
import uvicorn

def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload_ = os.getenv("RELOAD", "false").lower() in {"1", "true", "yes"}

    certfile = os.getenv("SSL_CERTFILE", "./data/certs/cert.pem")
    keyfile = os.getenv("SSL_KEYFILE", "./data/certs/key.pem")

    use_https = os.path.exists(certfile) and os.path.exists(keyfile)

    kwargs = {
        "app": "qumea_plugin.app:app",
        "host": host,
        "port": port,
        "reload": reload_,
    }

    if use_https:
        kwargs["ssl_certfile"] = certfile
        kwargs["ssl_keyfile"] = keyfile
        print(f"Starte HTTPS auf {host}:{port}")
    else:
        print(f"Kein Zertifikat gefunden → starte HTTP auf {host}:{port}")

    uvicorn.run(**kwargs)

if __name__ == "__main__":
    main()