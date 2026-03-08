DEFAULT_MQTT_CONFIG = {
    "host": "192.168.70.40",
    "port": 1883,
    "tenant_id": "test-tenant",
    "client_id": "axelion-plugin",
    "integrationId": "axelion-integration",
    "events_to_handle": {"FALL": True, "BED": True, "NO_RETURN": True},
}

DEFAULT_SSH_CONFIG = {
    "host": "192.168.70.171",
    "port": 22,
}

DEFAULT_HTTP_CONFIG = {
    "timeout": 10.0,
    "http_base_url": "http://192.168.70.171:1880",
    "verify_ssl": False,
}

DEFAULT_SERVICE_CONFIG = {
    "run_services_on_startup": False
}


def merge_with_defaults(saved: dict | None, default: dict) -> dict:
    data = default.copy()
    if saved:
        data.update(saved)
    return data
