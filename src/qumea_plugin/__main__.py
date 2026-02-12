import os
import uvicorn

def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload_ = os.getenv("RELOAD", "false").lower() in {"1", "true", "yes"}

    uvicorn.run(
        "qumea_plugin.app:app",
        host=host,
        port=port,
        reload=reload_
    )

if __name__ == "__main__":
    main()