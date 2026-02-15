DEFAULT_MQTT_CONFIG = {
    "host": "127.0.0.1",
    "port": 1883,
    "subscribe_topic": "qumea/events",
    "keepalive_in_topic": "qumea/broker/keepalive",
    "keepalive_out_topic": "qumea/plugin/keepalive",
}

DEFAULT_SSH_CONFIG = {
    "host": "127.0.0.1",
    "port": 22,
    "command": "tail -f /var/log/syslog",
}

DEFAULT_HTTP_CONFIG = {
    "timeout": 10.0,
    "base_url": None,
    "verify_ssl": True,
}


def merge_with_defaults(saved: dict | None, default: dict) -> dict:
    data = default.copy()
    if saved:
        data.update(saved)
    return data
