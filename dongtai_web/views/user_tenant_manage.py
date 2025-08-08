#!/usr/bin/env python

import logging

from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets

from dongtai_common.endpoint import R, UserEndPoint
from dongtai_common.models.user_tenant import UserTenant
from dongtai_common.utils.request_type import Request

logger = logging.getLogger("django")


class TenantManage(UserEndPoint, viewsets.ViewSet):
    name = "api-v2-tenant-manager"
    description = _("Tenant Manager")

    @extend_schema(
        summary=_("Tenant Manage"),
        tags=[_("TenantManage")],
    )

    def list(self, request: Request):
        if request.user.is_super_admin():
            key = request.query_params.get("keyword", "")
            if key and len(key) > 0:
                tenants = UserTenant.objects.filter(name__icontains=key).order_by("id").all()
            else:
                tenants = UserTenant.objects.order_by("id").all()
        else:
            tenants = [request.user.tenant]

        summary = None
        if "page" in request.query_params and "pageSize" in request.query_params:
            page: int = request.query_params.get("page")
            page_size: int = request.query_params.get("pageSize")
            summary, tenants = self.get_paginator(tenants, page, page_size)
        data = list()
        for tenant in tenants:
            data.append({
                "id": tenant.id,
                "name": tenant.name,
                "status": tenant.status,
                "user_count": tenant.users.count(),
                "users": list(tenant.users.values_list("username", flat=True)),
                "department_count": tenant.departments.count(),
                "departments": list(tenant.departments.values_list("name", flat=True)),
            })
        return R.success(data=data, page=summary)

    def add(self, request:Request):
        if not request.user.is_super_admin():
            return R.failure(msg="没有权限")
        try:
            UserTenant.objects.create(
                name=request.data.get("name"),
            )
        except Exception as e:
            logger.exception("exception: ", exc_info=e)
            return R.failure()

        return R.success()

    def delete(self, request: Request):
        if not request.user.is_super_admin():
            return R.failure(msg="没有权限")

        tid = request.data.get("id", -1)
        tenant = UserTenant.objects.filter(id=tid).first()
        if not tenant:
            return R.failure(msg="公司不存在")

        if tenant.departments.count() > 0:
            return R.failure(msg="公司不为空，请先删除所有部门")

        try:
            tenant.delete()
        except Exception as e:
            logger.exception("exception: ", exc_info=e)
            return R.failure()

        return R.success()

    def update(self, request:Request):
        if not request.user.is_super_admin():
            return R.failure(msg="没有权限")

        tid = request.data.get("id", -1)
        tenant = UserTenant.objects.filter(id=tid).first()
        if not tenant:
            return R.failure(msg="公司不存在")

        if "name" in request.data:
            tenant.name = request.data.get("name")
        if "status" in request.data:
            tenant.status = request.data.get("status")

        try:
            tenant.save()
        except Exception as e:
            logger.exception("exception: ", exc_info=e)
            return R.failure()

        return R.success()

    def status_list(self, request:Request):
        return R.success(data=UserTenant.get_status_list())