import json
import logging
from itertools import groupby
from time import time
from typing import TYPE_CHECKING

from django.db.models import IntegerChoices, Q
from django.db.models.query import QuerySet
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.serializers import ValidationError
from rest_framework.viewsets import ViewSet

from dongtai_common.endpoint import R, UserEndPoint
from dongtai_common.models import IastApiRouteV2
from dongtai_common.models.agent import IastAgent
from dongtai_common.models.api_route import FromWhereChoices
from dongtai_common.models.project import IastProject
from dongtai_common.models.vulnerablity import IastVulnerabilityModel
from dongtai_web.utils import extend_schema_with_envcheck

if TYPE_CHECKING:
    from django.db.models.query import ValuesQuerySet

logger = logging.getLogger("dongtai-webapi")


class StateType(IntegerChoices):
    ALL = 1
    RUNNING = 2
    STOP = 3
    UNINSTALL = 4
    ONLINE = 5


class AgentListv2ArgsSerializer(serializers.Serializer):
    page_size = serializers.IntegerField(default=20, help_text=_("Number per page"))
    page = serializers.IntegerField(default=1, help_text=_("Page index"))
    state = serializers.ChoiceField(choices=StateType)
    last_days = serializers.IntegerField(default=None, required=False, help_text=_("Last days"))
    project_id = serializers.IntegerField(default=None, required=False, help_text=_("project_id"))
    project_name = serializers.CharField(default=None, help_text=_("project_name"))
    version = serializers.CharField(default=None, help_text="agent 版本")


class AgentListv2(UserEndPoint, ViewSet):
    name = "api-v1-agents"
    description = _("Agent list")

    @extend_schema_with_envcheck(
        [AgentListv2ArgsSerializer],
        tags=[_("Agent")],
        summary=_("Agent List v2"),
    )
    def pagenation_list(self, request):
        ser = AgentListv2ArgsSerializer(data=request.GET)
        try:
            ser.is_valid(raise_exception=True)
        except ValidationError as e:
            return R.failure(data=e.detail)
        projects = request.user.get_projects()
        filter_condiction = generate_filter(ser.validated_data["state"]) & Q(project__in=projects)
        if ser.validated_data["project_name"]:
            filter_condiction = filter_condiction & Q(project__name__icontains=ser.validated_data["project_name"])
        if ser.validated_data["project_id"] is not None:
            filter_condiction = filter_condiction & Q(project_id=ser.validated_data["project_id"])
        if ser.validated_data["last_days"] is not None and ser.validated_data["last_days"] > 0:
            filter_condiction = filter_condiction & Q(
                heartbeat__dt__gte=int(time()) - 60 * 60 * 24 * ser.validated_data["last_days"]
            )
        if ser.validated_data["version"] is not None:
            filter_condiction = filter_condiction & Q(version=ser.validated_data["version"])

        summary, queryset = self.get_paginator(
            query_agent(filter_condiction),
            ser.validated_data["page"],
            ser.validated_data["page_size"],
        )
        queryset = list(queryset)
        for agent in queryset:
            agent["state"] = cal_state(agent)
            agent["memory_rate"] = get_memory(agent["heartbeat__memory"])
            agent["cpu_rate"] = get_cpu(agent["heartbeat__cpu"])
            agent["disk_rate"] = get_disk(agent["heartbeat__disk"])
            agent["is_control"] = get_is_control(agent["actual_status"], agent["expect_status"])
            agent["ipaddresses"] = get_service_addrs(json.loads(agent["server__ipaddresslist"]), agent["server__port"])
        data = {"agents": queryset, "summary": summary}
        return R.success(data=data)

    @extend_schema(
        tags=[_("Agent")],
        summary="获取 Agent 总结信息",
    )
    def summary(self, request):
        res = {}
        projects = request.user.get_projects()
        last_days = int(request.query_params.get("last_days", 0))
        for type_ in StateType:
            filter_condiction = generate_filter(type_)
            if last_days:
                filter_condiction = filter_condiction & Q(heartbeat__dt__gte=int(time()) - 60 * 60 * 24 * last_days)
            res[type_] = IastAgent.objects.filter(
                filter_condiction,
                project__in=projects,
            ).count()

        return R.success(data=res)

    @extend_schema(
        tags=[_("Agent")],
        summary="获取 Agent 状态",
    )
    def agent_stat(self, request):
        projects = request.user.get_projects()
        try:
            agent_id = int(request.query_params.get("id", 0))
            res = get_agent_stat(agent_id, projects)
        except Exception as e:
            logger.debug(f"agent_stat error:{e}")
            res = {}
        return R.success(data=res)

    @extend_schema(
        tags=[_("Agent")],
        summary="获取 Agent 版本信息",
    )
    def agent_versions(self, request):
        res = list(IastAgent.objects.values_list("version", flat=True).distinct())
        return R.success(data=res)


def get_service_addrs(ip_list: list, port: int) -> list:
    if not port:
        return ip_list
    return [x + ":" + str(port) for x in ip_list]


def get_agent_stat(agent_id: int, projects: QuerySet[IastProject]) -> dict:
    res = {}
    res["api_count"] = IastApiRouteV2.objects.filter(
        agent__id=agent_id,
        from_where=FromWhereChoices.FROM_AGENT
    ).count()
    res["vul_count"] = IastVulnerabilityModel.objects.filter(agent__id=agent_id, project__in=projects).count()
    return res


def generate_filter(state: StateType) -> Q:
    if state == StateType.RUNNING:
        return Q(actual_status=IastAgent.STATUS_RUNNING)
    if state == StateType.STOP:
        return Q(actual_status=IastAgent.STATUS_PAUSED)
    if state == StateType.UNINSTALL:
        return Q(actual_status=IastAgent.STATUS_OFFLINE)
    return Q()


def get_is_control(actual_status: int, expect_status: int) -> int:
    if actual_status != expect_status and actual_status != IastAgent.STATUS_OFFLINE:
        return 1
    return 0


def get_disk(jsonstr: str | None) -> str:
    if not jsonstr:
        return ""
    dic = json.loads(jsonstr)
    try:
        dic = json.loads(jsonstr)
        res = str(dic["rate"])
        res.replace("%", "")
    except Exception as e:
        logger.debug(e, exc_info=True)
        return "0"
    return res


def get_cpu(jsonstr: str | None) -> str:
    if not jsonstr:
        return ""
    try:
        dic = json.loads(jsonstr)
        res = str(dic["rate"])
    except Exception as e:
        logger.debug(e, exc_info=True)
        return "0"
    return res


def get_memory(jsonstr: str | None) -> str:
    if not jsonstr:
        return ""
    try:
        dic = json.loads(jsonstr)
        res = str(dic["rate"])
    except Exception as e:
        logger.debug(e, exc_info=True)
        return "0"
    dic = json.loads(jsonstr)
    return res


def cal_state(agent: dict) -> StateType:
    if agent["actual_status"] == IastAgent.STATUS_RUNNING:
        return StateType.RUNNING
    if agent["actual_status"] == IastAgent.STATUS_PAUSED:
        return StateType.STOP
    return StateType.UNINSTALL


def query_agent(filter_condiction=None) -> "ValuesQuerySet":
    if filter_condiction is None:
        filter_condiction = Q()
    return (
        IastAgent.objects.filter(filter_condiction)
        .values(
            "alias",
            "token",
            "project__name",
            "user",
            "language",
            "server__ip",
            "server__port",
            "server__path",
            "server__ipaddresslist",
            "server__hostname",
            "heartbeat__memory",
            "heartbeat__cpu",
            "heartbeat__disk",
            "register_time",
            "startup_time",
            "id",
            "project__id",
            "project_version__version_name",
            "version",
            "expect_status",
            "actual_status",
        )
        .order_by("-latest_time")
    )
