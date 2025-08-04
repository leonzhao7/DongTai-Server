from django.db import models

from dongtai_common.utils.settings import get_managed


class RoleStatus(models.IntegerChoices):
    DISABLE = 0, "禁用"
    ENABLE = 1, "启用"

class RoleLevel(models.IntegerChoices):
    NORMAL = 0, "普通用户"
    TENANT_ADMIN = 100, "租户管理员"
    SUPER_ADMIN = 200, "超级管理员"

class IastRoleV2(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=30, unique=True)
    is_admin = models.BooleanField(default=False)
    is_preset = models.BooleanField(default=False)
    permission = models.JSONField()
    status = models.IntegerField(choices=RoleStatus.choices)
    level = models.IntegerField(choices=RoleLevel.choices)

    class Meta:
        managed = get_managed()
        db_table = "auth_role"
        indexes = [models.Index(fields=["name"]), models.Index(fields=["status"])]

    def __str__(self):
        return self.name
