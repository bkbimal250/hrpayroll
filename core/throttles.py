from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class AuthLoginThrottle(AnonRateThrottle):
    scope = "auth_login"


class AuthRefreshThrottle(AnonRateThrottle):
    scope = "auth_refresh"


class AuthLogoutThrottle(UserRateThrottle):
    scope = "auth_logout"
