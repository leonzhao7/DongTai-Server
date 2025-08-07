#!/usr/bin/env python
# datetime:2021/1/18 下午12:54
from django.db import models
from django.utils import timezone

from dongtai_common.utils.settings import get_managed


class UserTenant(models.Model):
    STATUS_OK = 1
    STATUS_TRIAL = 2
    STATUS_SUSPEND = 3
    STATUS_LOCK = 4
    STATUS_DELETE = 5

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

    @staticmethod
    def get_status_list():
        return [{"code": UserTenant.STATUS_OK, "name": "正常"},
                {"code": UserTenant.STATUS_TRIAL, "name": "试用"},
                {"code": UserTenant.STATUS_SUSPEND, "name": "暂停"},
                {"code": UserTenant.STATUS_LOCK, "name": "锁定"},
                {"code": UserTenant.STATUS_DELETE, "name": "删除"}]
