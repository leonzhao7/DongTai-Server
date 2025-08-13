#!/usr/bin/env python

import logging

from django.db import transaction
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets

from dongtai_common.endpoint import R, UserEndPoint
from dongtai_common.models.user_department import UserDepartment
from dongtai_common.models.user_role import UserRole
from dongtai_common.utils.request_type import Request

logger = logging.getLogger("django")


class DepartmentManage(UserEndPoint, viewsets.ViewSet):
    name = "api-v2-department-manager"
    description = _("Department Manager")

    @extend_schema(
        summary=_("Department Manage"),
        tags=[_("DepartmentManage")],
    )

    def list(self, request: Request):
        try:
            key = request.query_params.get("keyword", "")
            if key and len(key) > 0:
                departs = request.user.get_departments().filter(name__icontains=key).order_by("id").all()
            else:
                departs = request.user.get_departments().order_by("id").all()

            summary = None
            if "page" in request.query_params and "pageSize" in request.query_params:
                page: int = request.query_params.get("page")
                page_size: int = request.query_params.get("pageSize")
                summary, departs = self.get_paginator(departs, page, page_size)
            data = list()
            for depart in departs:
                data.append({
                    "id": depart.id,
                    "name": depart.name,
                    "parent": depart.parent.name if depart.parent else "",
                    "parent_id": depart.parent.id if depart.parent else 0,
                    "tenant": depart.tenant.name,
                    "tenant_id": depart.tenant.id,
                    "user_count": depart.users.count(),
                    "users": list(depart.users.values_list("username", flat=True)),
                })
            return R.success(data=data, page=summary)
        except Exception as e:
            logger.exception("uncatched exception: ", exc_info=e)
            return R.failure(status=202, msg=_("Operation Failed"))

    @transaction.atomic
    def add(self, request:Request):
        if "name" not in request.data:
            return R.failure(msg="参数无效")
        name = request.data.get("name")
        try:
            parent = None
            if "parent_id" in request.data:
                parent_id = request.data.get("parent_id")
                parent = UserDepartment.objects.filter(id=parent_id).first()

            if request.user.is_super_admin():
                if "tenant_id" not in request.data:
                    return R.failure(msg="参数无效")
                tenant_id = request.data.get("tenant_id")
                if parent and parent.tenant.id != tenant_id:
                    return R.failure(msg="参数无效")
                UserDepartment.objects.create(name=name, parent=parent, tenant_id=tenant_id)
                return R.success()

            if request.user.is_tenant_admin():
                if parent and parent.tenant != request.user.tenant:
                    return R.failure(msg="没有权限")
                UserDepartment.objects.create(name=name, parent=parent, tenant=request.user.tenant)
                return R.success()

            return R.failure(msg="没有权限")
        except Exception as e:
            logger.exception("uncatched exception: ", exc_info=e)
            return R.failure(status=202, msg=_("Operation Failed"))

    @transaction.atomic
    def delete(self, request: Request):
        try:
            did = request.data.get("id", -1)
            depart = request.user.get_departments().filter(id=did).first()
            if not depart:
                return R.failure(msg="部门不存在")

            if depart.users.count() > 0:
                return R.failure(msg="部门不为空，请删除所有用户")

            depart.delete()
            return R.success()
        except Exception as e:
            logger.exception("uncatched exception: ", exc_info=e)
            return R.failure(status=202, msg=_("Operation Failed"))

    @transaction.atomic
    def update(self, request:Request):
        if request.user.is_normal():
            return R.failure(msg="没有权限")
        try:
            did = request.data.get("id", -1)
            depart = request.user.get_departments().filter(id=did).first()
            if not depart:
                return R.failure(msg="部门不存在")

            if "name" in request.data:
                depart.name = request.data.get("name")
            if "parent_id" in request.data:
                parent_id = request.data.get("parent_id")
                parent = request.user.get_departments().filter(id=parent_id).first()
                if parent is None:
                    return R.failure(msg="部门不存在")
                depart.parent = parent

            depart.save()
            return R.success()
        except Exception as e:
            logger.exception("exception: ", exc_info=e)
            return R.failure()
