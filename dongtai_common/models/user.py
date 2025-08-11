#!/usr/bin/env python
# datetime:2021/1/25 下午6:43

from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.db.models import Q, QuerySet
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from dongtai_common.models.user_department import UserDepartment
from dongtai_common.models.user_role import UserRole
from dongtai_common.models.user_tenant import UserTenant
from dongtai_conf.patch import patch_point, to_patch


class User(AbstractUser):
    phone = models.CharField(blank=True, max_length=32)
    role = models.ForeignKey(UserRole, models.DO_NOTHING, blank=False)
    tenant = models.ForeignKey(UserTenant, models.CASCADE, related_name="users", blank=True, null=True)
    department = models.ForeignKey(UserDepartment, models.SET_NULL, related_name="users", blank=True, null=True)
    default_language = models.CharField(max_length=15, blank=True)
    deleted = models.BooleanField(default=False)
    failed_login_count = models.IntegerField(default=0)
    failed_login_time = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "user"
        unique_together = ("username", "tenant")

    @property
    def role_level(self):
        return self.role.level

    def is_super_admin(self):
        return self.role.level == UserRole.LEVEL_SUPER

    def is_normal(self):
        return self.role.level == UserRole.LEVEL_NORMAL

    def is_tenant_admin(self):
        return self.role.level == UserRole.LEVEL_TENANT

    def is_system_admin(self):
        return self.role.level == UserRole.LEVEL_SUPER

    def is_talent_admin(self):
        return self.role.level == UserRole.LEVEL_TENANT

    def get_talent(self):
        return self.tenant

    def get_my_departments(self) -> QuerySet:
        if self.is_super_admin():
            return UserDepartment.objects.filter(id=-1).all()
        else:
            return UserDepartment.objects.filter(id=self.department.id).all()

    # 过滤当前用户可见的project
    def get_projects(self) -> QuerySet:
        from dongtai_common.models.project import IastProject

        if self.is_super_admin():
            return IastProject.objects.all()
        if self.is_tenant_admin():
            return IastProject.objects.filter(department__in=UserDepartment.objects.filter(tenant=self.tenant)).all()
        return IastProject.objects.filter(department__in=UserDepartment.objects.filter(id=self.department.id).all())

    def has_privilege(self, role_level, tenant_id) -> bool:
        if self.role_level == UserRole.LEVEL_SUPER:
            return True

        if self.role_level == UserRole.LEVEL_TENANT and self.tenant.id == tenant_id and role_level <= self.role_level:
            return True

        return False

    def has_project_perm(self, project) -> bool:
        if self.is_tenant_admin():
            return self.tenant == project.department.tenant
        if self.is_normal():
            return self.department == project.department
        return False