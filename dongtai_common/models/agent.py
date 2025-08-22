#!/usr/bin/env python
# datetime:2020/11/30 下午5:29

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from dongtai_common import generate_token
from dongtai_common.models import User
from dongtai_common.models.user_department import UserDepartment
from dongtai_common.models.project import IastProject
from dongtai_common.models.project_version import IastProjectVersion
from dongtai_common.models.server import IastServer
from dongtai_common.utils.db import get_timestamp, default_json
from dongtai_common.utils.settings import get_managed


def get_events():
    return ["注册成功"]


class IastAgent(models.Model):
    STATUS_RUNNING = 1
    STATUS_PAUSED = 2
    STATUS_OFFLINE = 3

    token = models.CharField(max_length=128, default=generate_token)
    version = models.CharField(max_length=128, blank=True)
    latest_time = models.IntegerField()
    user = models.ForeignKey(User, models.DO_NOTHING, related_name="agents")
    server = models.ForeignKey(
        to=IastServer,
        on_delete=models.DO_NOTHING,
        related_name="agents",
        null=True,
        related_query_name="agent",
        verbose_name=_("server"),
    )
    project = models.ForeignKey(IastProject, on_delete=models.CASCADE, default=-1)
    project_version = models.ForeignKey(IastProjectVersion, on_delete=models.CASCADE, default=-1)
    project_name = models.CharField(max_length=255, blank=True)
    language = models.CharField(max_length=10, blank=True)
    filepathsimhash = models.CharField(max_length=255, blank=True)
    alias = models.CharField(max_length=255, blank=True)
    startup_time = models.DateTimeField(default=timezone.now)
    register_time = models.DateTimeField(default=timezone.now)
    actual_status = models.IntegerField(default=STATUS_RUNNING)
    expect_status = models.IntegerField(default=STATUS_RUNNING)
    events = models.JSONField(default=get_events)

    ip = models.CharField(max_length=255, blank=True)
    hostname = models.CharField(max_length=255, blank=True, null=True, default="")
    cmdline = models.CharField(max_length=1024, blank=True, null=True, default="")
    env = models.JSONField(default=default_json)


    class Meta:
        managed = get_managed()
        db_table = "iast_agent"

    def append_events(self, event: str):
        self.update_events_if_need()
        events_list = self.events if self.events else ["注册成功"]
        events_list.append(event)
        self.events = events_list
        self.save()
        IastAgentEvent.objects.create(agent_id=self.id, name=event)

    def only_register(self):
        events_list = self.events if self.events else ["注册成功"]
        return events_list == ["注册成功"]

    def update_events(self):
        for event in self.events:
            IastAgentEvent.objects.create(agent_id=self.id, name=event, time=None)

    def is_need_to_update(self):
        if self.events and len(self.events) <= self.new_events.count():
            return False
        return True

    def update_events_if_need(self):
        if self.is_need_to_update():
            self.update_events()


class IastAgentEvent(models.Model):
    agent = models.ForeignKey(IastAgent, on_delete=models.CASCADE, related_name="new_events")
    name = models.CharField(max_length=255, blank=True)
    time = models.IntegerField(default=get_timestamp, blank=True, null=True)

    class Meta:
        managed = get_managed()
        db_table = "iast_agent_event"


# class IastAgent(models.Model):
#
#    class Meta:
