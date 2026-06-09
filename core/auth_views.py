from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from .auth_logging import log_auth_event
from .throttles import AuthLogoutThrottle, AuthRefreshThrottle


REFRESH_COOKIE_NAME = "refresh_token"


def set_refresh_cookie(response, refresh_token):
    max_age = int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=max_age,
        httponly=True,
        secure=not settings.DEBUG,
        samesite=getattr(settings, "JWT_REFRESH_COOKIE_SAMESITE", "None"),
        path="/api/",
    )


def clear_refresh_cookie(response):
    response.delete_cookie(
        REFRESH_COOKIE_NAME,
        path="/api/",
        samesite=getattr(settings, "JWT_REFRESH_COOKIE_SAMESITE", "None"),
    )


class CookieTokenRefreshView(TokenRefreshView):
    throttle_classes = [AuthRefreshThrottle]

    def post(self, request, *args, **kwargs):
        mutable_data = request.data.copy()
        if not mutable_data.get("refresh"):
            cookie_refresh = request.COOKIES.get(REFRESH_COOKIE_NAME)
            if cookie_refresh:
                mutable_data["refresh"] = cookie_refresh

        serializer = self.get_serializer(data=mutable_data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            log_auth_event("TOKEN_REFRESH_FAILED", request=request, reason=str(exc))
            raise InvalidToken(exc.args[0])

        response = Response(serializer.validated_data, status=status.HTTP_200_OK)
        rotated_refresh = serializer.validated_data.get("refresh")
        if rotated_refresh:
            set_refresh_cookie(response, rotated_refresh)

        log_auth_event("TOKEN_REFRESH_SUCCESS", request=request)
        return response


class LogoutView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthLogoutThrottle]

    def post(self, request):
        refresh_token = request.data.get("refresh") or request.COOKIES.get(REFRESH_COOKIE_NAME)
        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except TokenError:
                pass

        response = Response({"detail": "Logged out successfully"}, status=status.HTTP_200_OK)
        clear_refresh_cookie(response)
        log_auth_event(
            "USER_LOGOUT",
            request=request,
            user=request.user if request.user.is_authenticated else None,
        )
        return response
