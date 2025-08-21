#!/usr/bin/env python

import logging

from django.db import transaction
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets

from dongtai_common.endpoint import R, UserEndPoint
from dongtai_common.models import User
from dongtai_common.models.user_department import UserDepartment
from dongtai_common.models.user_role import UserRole
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
        try:
            key = request.query_params.get("keyword", "")
            if key and len(key) > 0:
                users = request.user.get_users().filter(username__icontains=key).order_by("id").all()
            else:
                users = request.user.get_users().order_by("id").all()

            summary = None
            if "page" in request.query_params and "pageSize" in request.query_params:
                page: int = request.query_params.get("page")
                page_size: int = request.query_params.get("pageSize")
                summary, users = self.get_paginator(users, page, page_size)
            data = list()
            for user in users:
                data.append({
                    "id": user.id,
                    "deleted": user.deleted,
                    "is_active": user.is_active,
                    "name": user.username,
                    "email": user.email,
                    "phone": user.phone,
                    "role_id": user.role.id,
                    "role": user.role.name,
                    "tenant_id": user.tenant.id if user.tenant else 0,
                    "tenant": user.tenant.name if user.tenant else "",
                    "department_id": list(user.departments.values_list("id", flat=True)),
                    "department": list(user.departments.values_list("name", flat=True)),
                })
            return R.success(data=data, page=summary)
        except Exception as e:
            logger.exception("uncatched exception: ", exc_info=e)
            return R.failure(status=202, msg=_("Operation Failed"))

    @transaction.atomic
    def lock(self, request:Request):
        try:
            user_id = request.data.get("id", -1)
            user = request.user.get_users().filter(id=user_id).first()
            if user is None:
                return R.failure(msg="用户不存在")

            user.deleted = True
            user.is_active = False
            user.save()
            return R.success()
        except Exception as e:
            logger.exception("uncatched exception: ", exc_info=e)
            return R.failure(status=202, msg=_("Operation Failed"))

    @transaction.atomic
    def unlock(self, request: Request):
        try:
            user_id = request.data.get("id", -1)
            user = request.user.get_users().filter(id=user_id).first()
            if user is None:
                return R.failure(msg="用户不存在")

            user.deleted = False
            user.is_active = True
            user.save()
            return R.success()
        except Exception as e:
            logger.exception("uncatched exception: ", exc_info=e)
            return R.failure(status=202, msg=_("Operation Failed"))

    @transaction.atomic
    def delete(self, request: Request):
        try:
            user_id = request.data.get("id", -1)
            user = request.user.get_users().filter(id=user_id).first()
            if user is None:
                return R.failure(msg="用户不存在")

            user.delete()
            return R.success()
        except Exception as e:
            logger.exception("uncatched exception: ", exc_info=e)
            return R.failure(status=202, msg=_("Operation Failed"))

    @transaction.atomic
    def reset(self, request:Request):
        try:
            user_id = request.data.get("id", -1)
            user = request.user.get_users().filter(id=user_id).first()
            if user is None:
                return R.failure(msg="用户不存在")

            user.set_password(user.username + "@123")
            user.save()
            return R.success()
        except Exception as e:
            logger.exception("uncatched exception: ", exc_info=e)
            return R.failure(status=202, msg=_("Operation Failed"))

    @transaction.atomic
    def update(self, request:Request):
        try:
            user_id = request.data.get("id", -1)
            user = request.user.get_users().filter(id=user_id).first()
            if user is None:
                return R.failure(msg="用户不存在")

            if "email" in request.data:
                user.email = request.data.get("email")
            if "phone" in request.data:
                user.phone = request.data.get("phone")
            if "default_language" in request.data:
                user.default_language = request.data.get("default_language")

            role_id = request.data.get("role", 0)
            if role_id:
                role = UserRole.objects.filter(id=role_id).first()
                if role is None:
                    return R.failure(msg="参数错误")
                user.role = role

            if not request.user.has_privilege(user.role.level, user.tenant.id):
                return R.failure(msg="没有权限")

            depart_ids = request.data.get("department")
            if depart_ids:
                departments = request.user.get_departments().filter(id__in=depart_ids).all()
                user.departments.set(departments)

            user.save()
            return R.success()
        except Exception as e:
            logger.exception("uncatched exception: ", exc_info=e)
            return R.failure(status=202, msg=_("Operation Failed"))

    @transaction.atomic
    def create(self, request:Request):
        try:
            username = request.data.get("name", "")
            if username == "":
                return R.failure(msg="请输入用户名")

            role_id = request.data.get("role", 0)
            role = UserRole.objects.filter(id=role_id).first()
            if role is None:
                return R.failure(msg="参数错误")

            tenant_id = request.data.get("tenant", 0)
            tenant = UserTenant.objects.filter(id=tenant_id).first()
            if tenant is None:
                return R.failure(msg="参数错误")

            if not request.user.has_privilege(role.level, tenant_id):
                return R.failure(msg="没有权限")

            user = User.objects.create_user(username=username,
                                     password=username+"@123",
                                     email=request.data.get("email", ""),
                                     phone=request.data.get("phone", ""),
                                     default_language=request.data.get("default_language", "zh"),
                                     role=role,
                                     tenant=tenant)

            depart_ids = request.data.get("department")
            if depart_ids:
                departments = request.user.get_departments().filter(id__in=depart_ids).all()
                if departments is None:
                    return R.failure(msg="参数错误")
                user.departments.set(departments)

            return R.success()
        except Exception as e:
            logger.exception("uncatched exception: ", exc_info=e)
            return R.failure(status=202, msg=_("Operation Failed"))
