#!/usr/local/env python
import logging
import time

from captcha.models import CaptchaStore
from django.contrib.auth import authenticate, login
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework.authtoken.models import Token

from dongtai_common.endpoint import R, UserEndPoint
from dongtai_common.models.user import User
from dongtai_common.utils.request_type import Request
from dongtai_conf.patch import patch_point, to_patch
from dongtai_conf.settings import TOKEN_LOGIN

logger = logging.getLogger("dongtai-webapi")


class UserLogin(UserEndPoint):
    permission_classes = []
    authentication_classes = []
    name = "user_views_login"
    description = _("User login")

    @extend_schema(
        summary=_("User login"),
        tags=[_("User")],
    )
    @to_patch
    def post(self, request: Request):
        """{
        'username': "",
        'password': "",
        'captcha_hash_key': "",
        'captcha': ""
        }
        """
        try:
            captcha_hash_key = request.data.get("captcha_hash_key")
            captcha = request.data.get("captcha")
            if not captcha or not captcha_hash_key:
                return R.failure(status=204, msg=_("verification code should not be empty"))

            captcha_obj = CaptchaStore.objects.get(hashkey=captcha_hash_key)
            if int(captcha_obj.expiration.timestamp()) < int(time.time()):
                return R.failure(status=203, msg=_("Captcha timed out"))

            if captcha_obj.response != captcha.lower():
                return R.failure(status=203, msg=_("Verification code error"))

            username = request.data.get("username")
            password = request.data.get("password")
            user: User | None = authenticate(username=username, password=password)  # type: ignore
            if user is None:
                user_login: User | None = User.objects.filter(username=username).first()
                if user_login:
                    if user_login.is_active:
                        user_login.failed_login_count += 1
                        user_login.failed_login_time = timezone.now()
                        user_login.save()
                        return R.failure(status=202, msg=_("Login failed"))
                    else:
                        return R.failure(status=205, msg="用户已被禁用")
                else:
                    return R.failure(status=202, msg=_("Login failed"))

            user.failed_login_count = 0
            user.save()
            login(request, user)
            return R.success(
                msg=_("Login successful"),
                data={
                    "default_language": user.default_language,
                    "is_active": user.is_active,
                },
            )
        except Exception as e:
            logger.exception("uncatched exception: ", exc_info=e)
            return R.failure(status=202, msg=_("Login failed"))

    if TOKEN_LOGIN:

        def get(self, request: Request):
            url = request.GET.get("url", "/")
            token = request.GET.get("token")
            token_obj = Token.objects.filter(key=token).first()
            if not url.startswith("/"):
                url = "/"
            if token_obj is not None:
                login(request, token_obj.user)
                return HttpResponseRedirect(url)
            return HttpResponseRedirect("/login")
