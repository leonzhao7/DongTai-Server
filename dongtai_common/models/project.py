#!/usr/bin/env python
# datetime:2020/11/30 下午5:32
import os.path
import string
import time

from django.db import models, transaction
from django.utils import timezone

from dongtai_common.models import User
from dongtai_common.models.user_department import UserDepartment
from dongtai_common.models.strategy_user import IastStrategyUser
from dongtai_common.models.user_tenant import UserTenant
from dongtai_common.utils.db import get_timestamp
from dongtai_common.utils.settings import get_managed
from dongtai_conf.settings import DOMAIN_VUL


class VulValidation(models.IntegerChoices):
    FOLLOW_GLOBAL = 0
    ENABLE = 1
    DISABLE = 2
    __empty__ = 0


class ProjectStatus(models.IntegerChoices):
    NORMAL = 0, "正常"
    ERROR = 1, "错误"
    OFFLINE = 2, "离线"
    __empty__ = 0


class IastProjectTemplate(models.Model):
    template_name = models.CharField(max_length=255)
    latest_time = models.IntegerField(default=get_timestamp)
    user = models.ForeignKey(User, models.DO_NOTHING)
    scan = models.ForeignKey(IastStrategyUser, models.DO_NOTHING)
    vul_validation = models.IntegerField(default=0, choices=VulValidation.choices)
    is_system = models.IntegerField(default=0)
    tenant = models.ForeignKey(UserTenant, models.SET_NULL, null=True, blank=True)

    class Meta:
        managed = get_managed()
        db_table = "project_template"
        unique_together = ['template_name', 'tenant_id']

    def to_full_template(self):
        pass

    def to_full_project_args(self):
        return {
            "scan_id": self.scan_id,  # type: ignore
            "vul_validation": self.vul_validation,
        }


class IastProject(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255, blank=True)
    mode = models.CharField(default="插桩模式", max_length=255, blank=True)
    vul_count = models.PositiveIntegerField(blank=True, null=True)
    agent_count = models.IntegerField(blank=True, null=True)
    latest_time = models.IntegerField(default=get_timestamp)
    # openapi服务不必使用该字段
    scan = models.ForeignKey(IastStrategyUser, models.DO_NOTHING, blank=True, null=True)

    vul_validation = models.IntegerField(default=0, choices=VulValidation.choices)
    base_url = models.CharField(max_length=255, blank=True)
    test_req_header_key = models.CharField(max_length=511, blank=True)
    test_req_header_value = models.CharField(max_length=511, blank=True)
    departments = models.ManyToManyField(UserDepartment, related_name='projects')
    tenant = models.ForeignKey(UserTenant, on_delete=models.CASCADE, related_name="projects")
    template = models.ForeignKey(IastProjectTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    current_version = models.ForeignKey("IastProjectVersion", on_delete=models.SET_NULL, null=True, blank=True)
    enable_log = models.BooleanField(null=True)
    log_level = models.CharField(max_length=16, null=True, blank=True)
    last_has_online_agent_time = models.IntegerField(default=get_timestamp)
    status = models.IntegerField(default=0, choices=ProjectStatus.choices)

    class Meta:
        managed = get_managed()
        db_table = "project"
        unique_together = ["name", "tenant_id"]

    def update_latest(self):
        self.latest_time = int(time.time())
        self.save(update_fields=["latest_time"])

    def get_url(self):
        return os.path.join(DOMAIN_VUL, "project/projectDetail", str(self.id))
