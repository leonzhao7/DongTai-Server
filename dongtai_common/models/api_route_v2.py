######################################################################
# @author      : zhaoliang
# @file        : api_route_v2
# @created     : 2025-05-20
#
# @description :
######################################################################
from django.db import models

from dongtai_common.models.agent import IastAgent
from dongtai_common.models.project import IastProject
from dongtai_common.models.project_version import IastProjectVersion


class FromWhereChoices(models.IntegerChoices):
    FROM_AGENT = 1
    FROM_METHOD_POOL = 2


class IastApiRouteV2Schema(models.Model):
    name = models.CharField(max_length=128, blank=False)
    info = models.JSONField(blank=False, default=dict)
    dst_info = models.JSONField(blank=False, default=dict)
    project = models.ForeignKey(IastProject, on_delete=models.CASCADE, blank=False, null=False)
    project_version = models.ForeignKey(IastProjectVersion, on_delete=models.CASCADE, blank=False, null=False)

    class Meta:
        db_table = 'iast_api_route_v2_schema'
        unique_together = [('project', 'project_version', 'name')]


class IastApiRouteV2(models.Model):
    path = models.CharField(max_length=128, blank=True)
    method = models.CharField(max_length=32, blank=True)
    controller = models.CharField(max_length=255, blank=True)
    schema = models.ForeignKey(IastApiRouteV2Schema, on_delete=models.CASCADE, blank=True, null=True)
    agent = models.ForeignKey(IastAgent, on_delete=models.DO_NOTHING, db_constraint=False, db_index=True, blank=True, null=True)
    from_where = models.IntegerField(default=FromWhereChoices.FROM_AGENT, choices=FromWhereChoices.choices)
    project = models.ForeignKey(IastProject, on_delete=models.CASCADE, blank=True, null=True)
    project_version = models.ForeignKey(IastProjectVersion, on_delete=models.CASCADE, blank=True, null=True)
    is_cover = models.IntegerField(default=0)
    create_at = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    update_at = models.DateTimeField(blank=True, null=True, auto_now=True)
    info = models.JSONField(blank=False, default=dict)

    class Meta:
        db_table = 'iast_api_route_v2'
        unique_together = [('project', 'project_version', 'path', 'method')]