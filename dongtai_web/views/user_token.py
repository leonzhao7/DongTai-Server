#!/usr/bin/env python
# datetime:2020/5/25 15:03
import logging

from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework.authtoken.models import Token

from dongtai_common.endpoint import R, UserEndPoint

logger = logging.getLogger("django")


class UserToken(UserEndPoint):
    name = "iast-v1-user-token"
    description = _("Get OpenAPI token")

    @extend_schema(
        summary=_("Get OpenAPI token"),
        tags=[_("User")],
    )
    def get(self, request):
        token, success = Token.objects.get_or_create(user=request.user)

        return R.success(data={"token": token.key})


class UserDepartmentToken(UserEndPoint):
    name = "iast-v1-user-department-token"
    description = _("获取部门部署 token")

    @extend_schema(summary=_("获取部门部署 token"), tags=[_("User")], deprecated=True)
    def get(self, request):
        departs = request.user.get_departments()
        data = list()
        for depart in departs:
            data.append({"id": depart.id, "name": depart.name, "token": "DEPART" + depart.token})
        return R.success(data=data)
