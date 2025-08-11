#!/usr/bin/env python
# datetime:2021/06/08 下午5:32

from django.db import models
from django.utils import timezone

from dongtai_common.models.project import IastProject
from dongtai_common.utils.settings import get_managed


class IastProjectVersion(models.Model):
    version_name = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    create_at = models.DateTimeField(default=timezone.now)
    update_at = models.DateTimeField(auto_now=True)
    project = models.ForeignKey(IastProject, on_delete=models.CASCADE, related_name="versions")
    vul_count = models.PositiveIntegerField(blank=True, null=True)
    agent_count = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = get_managed()
        db_table = "project_version"
        unique_together = ['project_id', 'version_name']
