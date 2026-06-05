import logging

logger = logging.getLogger("auth")


def get_client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_auth_event(event, request=None, user=None, **extra):
    payload = {
        "event": event,
        "user_id": str(getattr(user, "id", "")) if user else "",
        "username": getattr(user, "username", "") if user else "",
        "ip": get_client_ip(request) if request else "",
        "path": getattr(request, "path", "") if request else "",
        **extra,
    }
    logger.info("%s %s", event, payload)
