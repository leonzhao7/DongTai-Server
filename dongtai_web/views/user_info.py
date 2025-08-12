#!/usr/bin/env python

import logging

from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema

from dongtai_common.endpoint import R, UserEndPoint
from dongtai_common.models.user_role import UserRole
from dongtai_common.utils.request_type import Request
from dongtai_conf.settings import SCA_SETUP

logger = logging.getLogger("django")


class UserInfoEndpoint(UserEndPoint):
    name = "api-v1-user-info"
    description = _("User Info")

    @extend_schema(
        summary=_("User Info"),
        tags=[_("User")],
    )
    def get(self, request: Request):
        user = request.user
        return R.success(
            data={
                "userid": user.id,
                "username": user.get_username(),
                "role": 3 if user.is_normal() else
                        2 if user.is_tenant_admin() else
                        1 if user.is_super_admin() else
                        0,
                "role_name": user.role.name,
                "role_id": user.role.id,
            }
        )
