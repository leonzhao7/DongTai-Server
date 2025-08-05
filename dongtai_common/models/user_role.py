from django.db import models

from dongtai_common.utils.settings import get_managed


class RoleStatus(models.IntegerChoices):
    DISABLE = 0, "禁用"
    ENABLE = 1, "启用"

class RoleLevel(models.IntegerChoices):
    NORMAL = 0, "普通用户"
    TENANT_ADMIN = 100, "租户管理员"
    SUPER_ADMIN = 200, "超级管理员"

class UserRole(models.Model):
    LEVEL_NORMAL = 0
    LEVEL_TENANT = 100
    LEVEL_SUPER = 200

    STATUS_OK = 0
    STATUS_DISABLE = 1

    name = models.CharField(max_length=32, unique=True)
    status = models.IntegerField(blank=False, default=STATUS_OK)
    level = models.IntegerField(blank=False, default=LEVEL_NORMAL)
    permission = models.JSONField()

    class Meta:
        managed = get_managed()
        db_table = "user_role"

    def __str__(self):
        return self.name
