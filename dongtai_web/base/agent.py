#!/usr/bin/env python

import json
import logging
import re
import time

from django.utils.translation import gettext_lazy as _

from dongtai_common.models.agent import IastAgent
from dongtai_common.models.hook_type import HookType
from dongtai_common.models.program_language import IastProgramLanguage
from dongtai_common.models.project import IastProject
from dongtai_common.models.project_version import IastProjectVersion
from dongtai_common.models.server import IastServer
from dongtai_common.models.strategy import IastStrategyModel
from dongtai_common.models.vulnerablity import IastVulnerabilityModel

logger = logging.getLogger("django")


def get_agents_with_project(project_name, users):
    """
    :param project_name:
    :param users:
    :return:
    """
    agent_ids = []
    if project_name and project_name != "":
        project_ids = (
            IastProject.objects.filter(user__in=users, name__icontains=project_name).values_list("id", flat=True).all()
        )

        if project_ids:
            agent_ids = IastAgent.objects.filter(project_id__in=project_ids).values_list("id", flat=True).all()

    return agent_ids


def get_user_project_name(auth_users):
    project_models = IastProject.objects.filter(user__in=auth_users).values("id", "name")
    projects_info = {}
    if project_models:
        for item in project_models:
            projects_info[item["id"]] = item["name"]
    return projects_info


# add by song
def get_project_vul_count(users, queryset, auth_agents, project_id=None):
    result = []
    project_queryset = IastProject.objects.filter(user__in=users)
    project_queryset = project_queryset.values("name", "id")
    if not project_queryset:
        return result
    if project_id:
        project_queryset = project_queryset.filter(id=project_id)

    versions = project_queryset.values_list("current_version_id", "project_id").all()
    versions_map = {version[1]: version[0] for version in versions}
    agentIdArr = {}
    for item in queryset:
        agentIdArr[item["agent_id"]] = item["count"]
    auth_agent_arr = auth_agents.values("project_version_id", "project_id", "id")
    agent_list = {}
    for auth in auth_agent_arr:
        version_id = versions_map.get(auth["project_id"], 0)
        if version_id == auth["project_version_id"]:
            if agent_list.get(auth["project_id"], None) is None:
                agent_list[auth["project_id"]] = []
            agent_list[auth["project_id"]].append(auth["id"])

    # 需要 查询 指定项目 当前版本 绑定的agent 所对应的漏洞数量
    for project in project_queryset:
        project_id = project["id"]
        count = 0
        for agent_id in agent_list.get(project_id, []):
            count = count + int(agentIdArr.get(agent_id, 0))
        result.append({"project_name": project["name"], "count": count, "id": project_id})

    return sorted(result, key=lambda item: item["count"], reverse=True)[:5]


def change_dict_key(dic, keypair):
    for k, v in keypair.items():
        dic[v] = dic.pop(k)
    return dic


def get_hook_type_name(obj):
    #    filter(lambda x: x is not None, [strategy_name, hook_type_name]))
    type_ = list(
        filter(
            lambda x: x is not None,
            [obj.get("strategy__vul_name", None), obj.get("hook_type__name", None)],
        )
    )
    return type_[0] if type_ else ""


def initlanguage():
    program_language_list = IastProgramLanguage.objects.values_list("name", flat=True).all()
    return {program_language.upper(): 0 for program_language in program_language_list}


# todo 默认开源许可证
# def init_license():
#         for license in license_list


def get_agent_languages(agent_items):
    default_language = initlanguage()
    language_agents = {}
    language_items = IastAgent.objects.filter().values("id", "language")
    for language_item in language_items:
        language_agents[language_item["id"]] = language_item["language"]

    for item in agent_items:
        agent_id = item["agent_id"]
        count = item["count"]
        if default_language.get(language_agents[agent_id], None):
            default_language[language_agents[agent_id]] = count + default_language[language_agents[agent_id]]
        else:
            default_language[language_agents[agent_id]] = count
    return [{"language": _key, "count": _value} for _key, _value in default_language.items()]
