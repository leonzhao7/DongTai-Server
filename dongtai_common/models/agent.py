#!/usr/bin/env python
# datetime:2020/11/30 下午5:29

from django.db import models
from django.db.models import QuerySet
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from dongtai_common import generate_token
from dongtai_common.models import User
from dongtai_common.models.server import IastServer
from dongtai_common.models.project import IastProject
from dongtai_common.models.project_version import IastProjectVersion
from dongtai_common.utils.db import default_json
from dongtai_common.utils.settings import get_managed


class IastAgent(models.Model):
    STATUS_RUNNING = 1
    STATUS_PAUSED = 2
    STATUS_OFFLINE = 3

    token = models.CharField(max_length=128, default=generate_token)
    version = models.CharField(max_length=128, blank=True, null=True)
    user = models.ForeignKey(User, models.DO_NOTHING, related_name="agents")
    project = models.ForeignKey(IastProject, on_delete=models.DO_NOTHING, blank=True, null=True, related_name="agents")
    project_version = models.ForeignKey(IastProjectVersion, on_delete=models.DO_NOTHING, blank=True, null=True)
    latest_time = models.IntegerField()
    language = models.CharField(max_length=10, blank=True, null=True)
    filepathsimhash = models.CharField(max_length=255, blank=True, null=True)
    alias = models.CharField(max_length=255, blank=True, null=True)
    startup_time = models.DateTimeField(default=timezone.now)
    register_time = models.DateTimeField(default=timezone.now)
    update_time = models.DateTimeField(default=timezone.now)
    actual_status = models.IntegerField(default=STATUS_RUNNING)
    expect_status = models.IntegerField(default=STATUS_RUNNING)
    ip = models.CharField(max_length=128, blank=True, null=True)
    port = models.IntegerField(default=0)
    path = models.CharField(max_length=255, blank=True, null=True)
    pid = models.IntegerField(blank=True, null=True)
    hostname = models.CharField(max_length=255, blank=True, null=True, default="")
    cmdline = models.CharField(max_length=1024, blank=True, null=True, default="")
    env = models.JSONField(default=default_json)
    ipaddresslist = models.JSONField(null=False, default=list)
    protocol = models.CharField(max_length=255, blank=True, null=True)
    server = models.ForeignKey(
        to=IastServer,
        on_delete=models.DO_NOTHING,
        related_name="agents",
        null=True,
        related_query_name="agent",
        verbose_name=_("server"),
    )


    class Meta:
        managed = get_managed()
        db_table = "iast_agent"

    @staticmethod
    def get_online_agents() -> QuerySet:
        return IastAgent.objects.exclude(actual_status=IastAgent.STATUS_OFFLINE).all()


def delete_agent(agent: IastAgent):
    agent.heartbeats.all().delete()
    agent.delete()
