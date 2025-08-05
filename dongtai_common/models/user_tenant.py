#!/usr/bin/env python
# datetime:2021/1/18 下午12:54
from django.db import models
from django.utils import timezone

from dongtai_common.utils.settings import get_managed


class UserTenant(models.Model):
    STATUS_OK = 0
    STATUS_TRIAL = 1
    STATUS_SUSPEND = 2
    STATUS_LOCK = 3
    STATUS_DELETE = 4

    name = models.CharField(unique=True,max_length=255,blank=False)
    create_at = models.DateTimeField(default=timezone.now)
    update_at = models.DateTimeField(auto_now=True)
    status = models.IntegerField(blank=False, default=STATUS_OK)

    class Meta:
        managed = get_managed()
        db_table = "user_tenant"

    def __str__(self):
        return self.name

    def is_active(self):
        return self.status == self.STATUS_OK
