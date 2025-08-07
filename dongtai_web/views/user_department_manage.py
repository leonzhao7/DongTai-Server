#!/usr/bin/env python

import logging

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
        key = request.query_params.get("keyword", "")
        if key and len(key) > 0:
            q = Q(name__icontains=key)
        else:
            q = Q()
        if request.user.is_super_admin():
            departs = UserDepartment.objects.filter(q).order_by("id").all()
        else:
            departs = UserDepartment.objects.filter(q & Q(tenant=request.user.tenant)).order_by("id").all()

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
            })
        return R.success(data=data, page=summary)

    def add(self, request:Request):
        if "name" not in request.data:
            return R.failure(msg="参数无效")
        name = request.data.get("name")

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
            try:
                UserDepartment.objects.create(name=name, parent=parent, tenant_id=tenant_id)
                return R.success()
            except Exception as e:
                logger.exception("exception: ", exc_info=e)
                return R.failure()
        if request.user.is_tenant_admin():
            if parent and parent.tenant != request.user.tenant:
                return R.failure(msg="没有权限")
            try:
                UserDepartment.objects.create(name=name, parent=parent, tenant=request.user.tenant)
                return R.success()
            except Exception as e:
                logger.exception("exception: ", exc_info=e)
                return R.failure()

        return R.failure(msg="没有权限")

    def delete(self, request: Request):
        did = request.data.get("id", -1)
        depart = UserDepartment.objects.filter(id=did).first()
        if not depart:
            return R.failure(msg="部门不存在")

        if request.user.is_normal():
            return R.failure(msg="没有权限")
        if request.user.is_tenant_admin() and request.user.tenant != depart.tenant:
            return R.failure(msg="没有权限")

        try:
            depart.delete()
        except Exception as e:
            logger.exception("exception: ", exc_info=e)
            return R.failure()

        return R.success()

    def update(self, request:Request):
        if request.user.is_normal():
            return R.failure(msg="没有权限")

        did = request.data.get("id", -1)
        depart = UserDepartment.objects.filter(id=did).first()
        if not depart:
            return R.failure(msg="部门不存在")

        if request.user.is_tenant_admin() and depart.tenant != request.user.tenant:
            return R.failure(msg="没有权限")

        if "name" in request.data:
            depart.name = request.data.get("name")
        if "parent_id" in request.data:
            parent_id = request.data.get("parent_id")
            parent = UserDepartment.objects.filter(id=parent_id).first()
            if parent is None:
                return R.failure(msg="部门不存在")
            if request.user.is_tenant_admin() and request.user.tenant != parent.tenant:
                return R.failure(msg="没有权限")
            if depart.tenant != parent.tenant:
                return R.failure(msg="参数错误")
            depart.parent = parent

        try:
            depart.save()
        except Exception as e:
            logger.exception("exception: ", exc_info=e)
            return R.failure()

        return R.success()