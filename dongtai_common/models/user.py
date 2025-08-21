#!/usr/bin/env python
# datetime:2021/1/25 下午6:43

from django.contrib.auth.models import AbstractUser
from django.db import models, transaction
from django.db.models import Q, QuerySet
from django.db.transaction import atomic
from django.utils import timezone

from dongtai_common import generate_token
from dongtai_common.models.user_department import UserDepartment
from dongtai_common.models.user_role import UserRole
from dongtai_common.models.user_tenant import UserTenant


class User(AbstractUser):
    phone = models.CharField(blank=True, max_length=32)
    role = models.ForeignKey(UserRole, models.DO_NOTHING, blank=False)
    tenant = models.ForeignKey(UserTenant, models.CASCADE, related_name="users", blank=True, null=True)
    departments = models.ManyToManyField(UserDepartment, related_name='users')
    default_language = models.CharField(max_length=15, blank=True)
    deleted = models.BooleanField(default=False)
    failed_login_count = models.IntegerField(default=0)
    failed_login_time = models.DateTimeField(default=timezone.now)
    token = models.CharField(max_length=32, default=generate_token)

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

    # 过滤当前用户可见的department
    def get_departments(self) -> QuerySet:
        if self.is_super_admin():
            return UserDepartment.objects.filter(id=-1).all()
        elif self.is_tenant_admin():
            return self.tenant.departments.all()
        else:
            return self.departments.all()

    # 过滤当前用户可见的project
    def get_projects(self) -> QuerySet:
        from dongtai_common.models.project import IastProject

        if self.is_tenant_admin():
            return self.tenant.projects.all()
        else:
            departs = self.get_departments()
            return IastProject.objects.filter(departments__in=departs.values_list("id")).all()

    def get_project_templates(self) -> QuerySet:
        from dongtai_common.models.project import IastProjectTemplate

        if self.is_system_admin():
            return IastProjectTemplate.objects.filter(tenant__isnull=True).all()
        else:
            return IastProjectTemplate.objects.filter(Q(tenant__isnull=True) | Q(tenant=self.tenant)).all()

    # 过滤当前用户可见的user
    def get_users(self) -> QuerySet:
        if self.is_super_admin():
            return User.objects.all()

        if self.is_tenant_admin():
            return self.tenant.users.all()

        return User.objects.filter(id=self.id).all()

    # 过滤当前用户可见的agent
    def get_agents(self) -> QuerySet:
        return self.agents.all()

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

    @transaction.atomic
    def create_project_version(self, project_name, version_name, project_defaults, version_defaults):
        from dongtai_common.models import IastProjectVersion

        project, created =self.get_projects().update_or_create(name=project_name,
                                                               tenant=self.tenant,
                                                               defaults=project_defaults)
        version, version_created = IastProjectVersion.objects.update_or_create(version_name=version_name,
                                                                               project=project,
                                                                               defaults=version_defaults)
        if self.is_tenant_admin():
            project.departments.clear()
        else:
            project.departments.set(self.departments.all())
        if not project.current_version:
            project.current_version = version
            project.save()
        return project, version

