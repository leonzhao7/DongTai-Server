#!/usr/bin/env python

import logging

from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets

from dongtai_common.endpoint import R, UserEndPoint
from dongtai_common.models import User
from dongtai_common.models.user_role import RoleLevel, UserRole
from dongtai_common.models.user_tenant import UserTenant
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
        if request.user.is_normal():
            return R.failure(msg="没有权限")
        data = list()
        if request.user.is_super_admin():
            users = User.objects.order_by("id").all()
        else:
            users = User.objects.filter(tenant=request.user.tenant).order_by("id").all()
        summary = None
        if "page" in request.query_params and "pageSize" in request.query_params:
            page: int = request.query_params.get("page")
            page_size: int = request.query_params.get("pageSize")
            summary, users = self.get_paginator(users, page, page_size)
        for user in users:
            data.append({
                "id": user.id,
                "name": user.username,
                "email": user.email,
                "phone": user.phone,
                "role_id": user.role.id,
                "role": user.role.name,
                "tenant_id": user.tenant.id if user.tenant else 0,
                "tenant": user.tenant.name if user.tenant else "",
                # "lastlogin": user.last_login,
                # "department": str(user.department),
                "deleted": user.deleted,
            })
        return R.success(data=data, page=summary)

    def stop(self, request:Request):
        user_id = request.data.get("id", -1)
        user = User.objects.filter(id=user_id).first()
        if user is None:
            return R.failure(msg="用户不存在")

        if not request.user.has_privilege(user.role_level, user.tenant.id):
            return R.failure(msg="没有权限")

        user.deleted = True
        user.save()
        return R.success()

    def reset(self, request:Request):
        user_id = request.data.get("id", -1)
        user = User.objects.filter(id=user_id).first()
        if user is None:
            return R.failure(msg="用户不存在")

        if not request.user.has_privilege(user.role_level, user.tenant.id):
            return R.failure(msg="没有权限")

        user.password = user.username + "@123"
        user.save()
        return R.success()

    def update(self, request:Request):
        user_id = request.data.get("id", -1)
        user = User.objects.filter(id=user_id).first()
        if user is None:
            return R.failure(msg="用户不存在")

        role_id = request.data.get("role", -1)
        role = UserRole.objects.filter(id=role_id).first()
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
        role = UserRole.objects.filter(id=role_id).first()
        if role is None:
            return R.failure(msg="参数错误")

        tenant_id = request.data.get("tenant", 0)
        tenant = UserTenant.objects.filter(id=tenant_id).first()
        if tenant is None:
            return R.failure(msg="参数错误")

        username = request.data.get("name", "")
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
