import logging

from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets

from dongtai_common.endpoint import R, UserEndPoint
from dongtai_common.models.user_role import UserRole
from dongtai_common.utils.request_type import Request

logger = logging.getLogger("django")


class RoleManage(UserEndPoint, viewsets.ViewSet):
    name = "api-v2-role-manager"
    description = _("Role Manager")

    @extend_schema(
        summary=_("Role Manage"),
        tags=[_("RoleManage")],
    )

    def list(self, request:Request):
        roles = UserRole.objects.all()
        data = list()
        for role in roles:
            data.append({
                "id": role.id,
                "name": role.name,
            })
        return R.success(data=data)