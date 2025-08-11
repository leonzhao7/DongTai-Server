#!/usr/bin/env python
# datetime:2020/11/27 下午4:31
import string

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from shortuuid.django_fields import ShortUUIDField

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
    token = models.CharField(max_length=1024, blank=True)
    tenant = models.ForeignKey(UserTenant, on_delete=models.DO_NOTHING, related_name='departments',)
    token = ShortUUIDField(max_length=22, alphabet=string.ascii_letters + string.digits)

    class Meta:
        managed = get_managed()
        db_table = "user_department"

    def __str__(self):
        return self.name
