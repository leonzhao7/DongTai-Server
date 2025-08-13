#!/usr/bin/env python
# datetime: 2021/7/16 下午4:45
import json
import logging
from functools import reduce
from operator import ior
from typing import TYPE_CHECKING

from django.core.paginator import EmptyPage, Paginator
from django.db.models import Count
from django.http import JsonResponse
from django.http.request import HttpRequest
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework import exceptions, status
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.views import APIView

from dongtai_common.models import User
from dongtai_common.models.agent import IastAgent
from dongtai_common.models.asset import Asset
from dongtai_common.models.asset_vul import IastVulAssetRelation
from dongtai_common.models.access_log import AccessLog
from dongtai_common.models.project import IastProject
from dongtai_common.permissions import (
    UserPermission,
)
from dongtai_common.utils import const
from dongtai_common.utils.init_schema import VIEW_CLASS_TO_SCHEMA

if TYPE_CHECKING:
    from django.core.paginator import _SupportsPagination
    from django.db.models.query import QuerySet, ValuesQuerySet

logger = logging.getLogger("dongtai-core")


class EndPoint(APIView):
    """
    基于APIView封装的API入口处理类,需要针对请求进行统一处理的都通过该类实现
    """

    name = "api-v1"
    description = "ApiServer接口"
    permission_classes_by_action = {}

    def __init__(self, **kwargs):
        """
        Constructor. Called in the URLconf; can contain helpful extra
        keyword arguments, and other things.
        """
        # Go through keyword arguments, and either save their values to our
        # instance, or raise an error.
        super().__init__(**kwargs)

    def load_json_body(self, request):
        """
        Attempts to load the request body when it's JSON.

        The end result is ``request.json_body`` having a value. When it can't
        load the body as JSON, for any reason, ``request.json_body`` is None.

        The request flow is unaffected and no exceptions are ever raised.
        """

        request.json_body = None

        if not request.META.get("CONTENT_TYPE", "").startswith("application/json"):
            return

        if not len(request.body):
            return

        try:
            request.json_body = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        """
        处理HTTP请求的入口方法
        :param request: HTTP请求
        :param args: 请求参数
        :param kwargs:
        :return: HTTP响应体
        """
        start_time = timezone.now()
        user_id = request.user.id
        self.args = args
        self.kwargs = kwargs
        request = self.initialize_request(request, *args, **kwargs)
        self.request = request
        self.headers = self.default_response_headers  # deprecate?

        try:
            self.initial(request, *args, **kwargs)
            content_length_str = request.META.get("CONTENT_LENGTH", "")
            content_length = int(content_length_str) if content_length_str.strip().isdigit() else 0

            # Get the appropriate handler method
            if request.method.lower() in self.http_method_names:
                handler = getattr(self, request.method.lower(), self.http_method_not_allowed)
            else:
                handler = self.http_method_not_allowed
            response = handler(request, *args, **kwargs)
        except AuthenticationFailed as exc:
            logger.debug(f"url: {self.request.path},exc:{exc}")
            response = self.handle_exception(exc)
        except Exception as exc:
            logger.warning(f"url: {self.request.path},exc:{exc}", exc_info=True)
            response = self.handle_exception(exc)

        self.response = self.finalize_response(request, response, *args, **kwargs)
        if self.request.user is not None:
            try:
                method = self.request.method
                if method is None:
                    raise ValueError("can not get request method")
                _, _, _, filepath = VIEW_CLASS_TO_SCHEMA.get(self.__class__, {}).get(method, (None, None, None, ""))
                if "dongtai" not in filepath or "dongtai_protocol" in filepath:
                    return self.response

                reply = json.loads(response.content)
                if user_id is None:
                    user_id = self.request.user.id
                AccessLog.objects.create(
                    start_time=start_time,
                    exec_time=(timezone.now()-start_time).total_seconds(),
                    user_id=user_id,
                    client_ip=get_client_ip(self.request),
                    method=self.request.method,
                    url=self.request.get_full_path(),
                    user_agent=self.request.META.get("HTTP_USER_AGENT", ""),
                    # status_code=reply.get("status", 0),
                    req_body_length=content_length,
                    reply_msg=reply.get("msg", "")
                )
            except Exception as e:
                logger.warning(f"get log info failed: {e}", exc_info=True)
        return self.response

    def handle_exception(self, exc):
        """
        Handle any exception that occurs, by returning an appropriate response,
        or re-raising the error.
        """
        if isinstance(exc, exceptions.Throttled):
            exc.status_code = status.HTTP_429_TOO_MANY_REQUESTS
        elif isinstance(exc, (exceptions.NotAuthenticated, exceptions.AuthenticationFailed)):
            # WWW-Authenticate header for 401 responses, else coerce to 403
            auth_header = self.get_authenticate_header(self.request)

            if auth_header:
                exc.auth_header = auth_header
            else:
                exc.status_code = status.HTTP_403_FORBIDDEN

        exception_handler = self.get_exception_handler()

        context = self.get_exception_handler_context()
        response = exception_handler(exc, context)

        if response is None:
            self.raise_uncaught_exception(exc)

        response.exception = True
        return response

    def parse_args(self, request):
        pass

    @staticmethod
    def get_paginator(
        queryset: "QuerySet | ValuesQuerySet", page: int = 1, page_size: int = 20, max_page_size: int = 50
    ) -> tuple[dict, "QuerySet | _SupportsPagination"]:
        """
        根据模型集合、页号、每页大小获取分页数据
        :param queryset:
        :param page:
            It is recommended to set the pagesize below 50,
            if it exceeds 50, it will be changed to 50
        :param page_size:
        :return:
        """
        page_size = min(max_page_size, int(page_size))
        page = int(page)
        try:
            page_info = Paginator(queryset, per_page=page_size)
            page_summary = {
                "alltotal": page_info.count,
                "num_pages": page_info.num_pages,
                "page_size": page_size,
            }
        except BaseException:
            page_summary = {"alltotal": 0, "num_pages": 0, "page_size": page_size}
        try:
            page_info.validate_number(page)
            page_list = page_info.get_page(page).object_list
        except EmptyPage:
            return page_summary, queryset.none()
        except BaseException as e:
            logger.info(e, exc_info=e)
            return page_summary, queryset.none()
        return page_summary, page_list

    @staticmethod
    def get_auth_users(user):
        """
        通过用户查询有访问权限的用户列表
        :param user:
        :return:
        """
        if user.is_anonymous:
            users = User.objects.filter(username=const.USER_BUGENV)
        elif user.is_system_admin():
            users = User.objects.all()
        elif user.is_talent_admin():
            talent = user.get_talent()
            users = talent.users
        else:
            users = User.objects.filter(id=user.id).all()
        return users

    @staticmethod
    def get_auth_agents_with_user(user):
        """
        通过用户查询有访问权限的agent列表
        :param user:
        :return:
        """
        return EndPoint.get_auth_agents(EndPoint.get_auth_users(user))

    @staticmethod
    def get_auth_agents(users):
        """
        通过用户列表查询有访问权限的agent列表
        :param users:
        :return:
        """
        qs = IastProject.objects.none()
        qss = [user.get_projects() for user in users]
        projects = reduce(ior, qss, qs)
        return IastAgent.objects.filter(project__in=projects)

    @staticmethod
    def get_auth_assets(users):
        """
        通过用户列表查询有访问权限的asset列表
        :param users:
        :return:
        """
        qs = IastProject.objects.none()
        qss = [user.get_projects() for user in users]
        projects = reduce(ior, qss, qs)
        return Asset.objects.filter(project__in=projects, is_del=0)

    @staticmethod
    def get_auth_asset_vuls(assets):
        """
        通过用户列表查询有访问权限的asset vul列表
        :param users:
        :return:
        """
        permission_assets = assets.filter(dependency_level__gt=0).values("id").all()
        auth_assets = [_i["id"] for _i in permission_assets]

        vul_asset_ids = (
            IastVulAssetRelation.objects.filter(asset_id__in=auth_assets, is_del=0).values("asset_vul_id").all()
        )
        perm_vul_ids = []
        if vul_asset_ids:
            perm_vul_ids = [_i["asset_vul_id"] for _i in vul_asset_ids]

        return perm_vul_ids

    @staticmethod
    def get_auth_and_anonymous_agents(user):
        #        if user.is_active:
        #
        #        if query_user == []:
        #            if dt_range_user:
        return EndPoint.get_auth_agents_with_user(user)


class MixinAuthEndPoint(EndPoint):
    """
    通过Token和Sessin验证的API入口
    """

    authentication_classes = (
        SessionAuthentication,
        TokenAuthentication,
    )


class AnonymousAuthEndPoint(EndPoint):
    """
    具有匿名用户权限验证的API入口
    """

    authentication_classes = []


class AnonymousAndUserEndPoint(MixinAuthEndPoint):
    permission_classes = []


class UserEndPoint(MixinAuthEndPoint):
    permission_classes = (UserPermission,)


class OpenApiEndPoint(EndPoint):
    authentication_classes = (
        TokenAuthentication,
    )
    permission_classes = (UserPermission,)


class EngineApiEndPoint(EndPoint):
    authentication_classes = (SessionAuthentication, TokenAuthentication)
    permission_classes = (UserPermission,)


class SystemAdminEndPoint(EndPoint):
    authentication_classes = (SessionAuthentication, TokenAuthentication)
    permission_classes = (UserPermission,)


class TalentAdminEndPoint(EndPoint):
    authentication_classes = (SessionAuthentication, TokenAuthentication)
    permission_classes = (UserPermission,)


class R:
    """
    Anyway, to prevent information exposure through an exception ,don't directly return exception message in response .
    ref: https://cwe.mitre.org/data/definitions/497.html
    ref: https://cwe.mitre.org/data/definitions/209.html
    """

    @staticmethod
    def success(
        status=201,
        data=None,
        msg=_("success"),  # noqa: B008
        page=None,
        status_code=200,
        **kwargs,
    ):
        resp_data = {"status": status, "msg": msg}
        if data is not None:
            resp_data["data"] = data
        if page:
            resp_data["page"] = page

        for key, value in kwargs.items():
            resp_data[key] = value

        return JsonResponse(
            resp_data,
            status=status_code,
        )

    @staticmethod
    def failure(status=202, data=None, status_code=200, msg=_("failure")):  # noqa: B008
        resp_data = {"status": status, "msg": msg}
        if data:
            resp_data["data"] = data

        return JsonResponse(
            resp_data,
            status=status_code,
        )


def get_client_ip(request: HttpRequest) -> str | None:
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    return x_forwarded_for.split(",")[0] if x_forwarded_for else request.META.get("REMOTE_ADDR")
