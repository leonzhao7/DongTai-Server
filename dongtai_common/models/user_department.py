#!/usr/bin/env python
# datetime:2020/11/27 下午4:31
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from dongtai_common import generate_token
from dongtai_common.models.user_tenant import UserTenant
from dongtai_common.utils.settings import get_managed


class UserDepartment(models.Model):
    name = models.CharField(_("name"),blank=False,max_length=128)
    create_at = models.DateTimeField(default=timezone.now)
    update_at = models.DateTimeField(auto_now=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        default=None,
    )
    token = models.CharField(max_length=32, default=generate_token)
    tenant = models.ForeignKey(UserTenant, on_delete=models.DO_NOTHING, related_name='departments',)

    class Meta:
        managed = get_managed()
        db_table = "user_department"

    def __str__(self):
        return self.name
