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
    default_language = models.CharField(max_length=15, blank=True)
    deleted = models.BooleanField(default=False)
    failed_login_count = models.IntegerField(default=0)
    failed_login_time = models.DateTimeField(default=timezone.now)
    departments = models.ManyToManyField(
        UserDepartment,
        related_name="users",
        verbose_name="所属部门"
    )

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
        try:
            department = self.department.get() if self.department else None
            talent = department.talent.get() if department else None
        except Exception:
            talent = None
        return talent

    def get_departments(self) -> QuerySet:
        if self.role.level == UserRole.LEVEL_SUPER:
            return UserDepartment.objects.all()
        return self.departments.all()

    @to_patch
    def get_projects(self) -> QuerySet:
        from dongtai_common.models.project import IastProject

        if self.role.level == UserRole.LEVEL_SUPER:
            return IastProject.objects.all()
        departs = self.get_departments()
        return IastProject.objects.filter(department__in=departs)

    def has_privilege(self, role_level, tenant_id) -> bool:
        if self.role_level <= role_level:
            return False
        if self.role_level == UserRole.LEVEL_TENANT and self.tenant != tenant_id:
            return False
        return True