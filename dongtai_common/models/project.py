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
    LOG_LEVEL_NONE = 0
    LOG_LEVEL_ERROR = 1
    LOG_LEVEL_WARN = 2
    LOG_LEVEL_INFO = 3
    LOG_LEVEL_DEBUG = 4
    LOG_LEVEL_TRACE = 5

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
    log_level = models.IntegerField(default=LOG_LEVEL_ERROR)
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

    def generate_log_level(self, enable, level_str):
        if enable:
            if level_str.upper() == "ERROR":
                return self.LOG_LEVEL_ERROR
            elif level_str.upper() == "WARN":
                return self.LOG_LEVEL_WARN
            elif level_str.upper() == "INFO":
                return self.LOG_LEVEL_INFO
            elif level_str.upper() == "DEBUG":
                return self.LOG_LEVEL_DEBUG
            elif level_str.upper() == "TRACE":
                return self.LOG_LEVEL_INFO

        return self.LOG_LEVEL_NONE

    def get_log_level(self):
        if self.log_level == self.LOG_LEVEL_NONE:
            return False, ""
        else:
            if self.log_level == self.LOG_LEVEL_ERROR:
                level = "ERROR"
            elif self.log_level == self.LOG_LEVEL_WARN:
                level = "WARN"
            elif self.log_level == self.LOG_LEVEL_INFO:
                level = "INFO"
            elif self.log_level == self.LOG_LEVEL_DEBUG:
                level = "DEBUG"
            elif self.log_level == self.LOG_LEVEL_TRACE:
                level = "TRACE"
            else:
                level = ""
            return True, level

    def get_current_version_data(self):
        if self.current_version:
            return {
                "version_id": self.current_version.id,
                "version_name": self.current_version.version_name,
                "description": self.current_version.description,
            }
        else:
            return {
                "version_id": 0,
                "version_name": "",
                "description": "",
            }