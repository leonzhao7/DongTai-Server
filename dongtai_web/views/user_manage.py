#!/usr/bin/env python

import logging

from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets

from dongtai_common.endpoint import R, UserEndPoint
from dongtai_common.models import User
from dongtai_common.models.iast_role import RoleLevel, IastRoleV2
from dongtai_common.models.tenant import Tenant
from dongtai_common.utils.request_type import Request

logger = logging.getLogger("django")


class UserManage(UserEndPoint, viewsets.ViewSet):
    name = "api-v2-user-manager"
    description = _("User Manager")

    @extend_schema(
        summary=_("User Manage"),
        tags=[_("UserManage")],
    )
    def list(self, request:Request):
        role = request.user.role_level
        if role == RoleLevel.NORMAL:
            return R.failure(msg="没有权限")
        data = list()
        if role == RoleLevel.SUPER_ADMIN:
            users = User.objects.all()
        else:
            users = User.objects.filter(tenant=request.user.tenant).all()
        for user in users:
            data.append({
                "userid": user.id,
                "username": user.username,
                "email": user.email,
                "phone": user.phone,
                "role": user.role.id,
                "role_level": user.role.name,
                "tenant": user.tenant.id,
                "tenant_name": user.tenant.name,
                # "lastlogin": user.last_login,
                "department": str(user.department),
                "deleted": user.deleted,
            })
        return R.success(data=data)

    def stop(self, request:Request):
        user_id = request.data.get("userid", -1)
        user = User.objects.filter(id=user_id).first()
        if user is None:
            return R.failure(msg="用户不存在")

        if not request.user.has_privilege(user.role_level, user.tenant.id):
            return R.failure(msg="没有权限")

        user.deleted = True
        user.save()
        return R.success()

    def update(self, request:Request):
        user_id = request.data.get("userid", -1)
        user = User.objects.filter(id=user_id).first()
        if user is None:
            return R.failure(msg="用户不存在")

        role_id = request.data.get("role", -1)
        role = IastRoleV2.objects.filter(id=role_id).first()
        if role is None:
            return R.failure(msg="参数错误")
        user.role = role

        if not request.user.has_privilege(role.level, user.tenant.id):
            return R.failure(msg="没有权限")

        user.email = request.data.get("email", "")
        user.phone = request.data.get("phone", "")
        user.default_language = request.data.get("default_language", "zh")
        user.save()
        return R.success()

    def create(self, request:Request):
        role_id = request.data.get("role", 0)
        role = IastRoleV2.objects.filter(id=role_id).first()
        if role is None:
            return R.failure(msg="参数错误")

        tenant_id = request.data.get("tenant", 0)
        tenant = Tenant.objects.filter(id=tenant_id).first()
        if tenant is None:
            return R.failure(msg="参数错误")

        username = request.data.get("username", "")
        if username == "":
            return R.failure(msg="请输入用户名")

        if not request.user.has_privilege(role.level, tenant_id):
            return R.failure(msg="没有权限")

        User.objects.create_user(username=username,
                                 password=username+"@123",
                                 email=request.data.get("email", ""),
                                 phone=request.data.get("phone", ""),
                                 default_language=request.data.get("default_language", "zh"),
                                 role=role,
                                 tenant=tenant)
        return R.success()
