#!/usr/bin/env python
# datetime:2020/11/30 下午3:13
import base64
import json
import logging
import string
import time
import uuid
import os
from datetime import datetime

from django.db import transaction
from django.db.transaction import atomic
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema

from dongtai_common.endpoint import OpenApiEndPoint, R
from dongtai_common.models.agent import IastAgent
from dongtai_common.models.project import (
    IastProject,
    IastProjectTemplate,
)
from dongtai_common.models.project_version import IastProjectVersion
from dongtai_common.models.server import IastServer
from dongtai_common.utils.request_type import Request
from dongtai_protocol.api_schema import DongTaiParameter
from dongtai_protocol.decrypter import parse_data

logger = logging.getLogger("dongtai.openapi")


def get_agent_allow_report(agent_id):
    return 1


class AgentRegisterEndPoint(OpenApiEndPoint):
    """
    引擎注册接口
    """

    name = "api-v1-agent-register"
    description = "引擎注册"

    @staticmethod
    def register_project(user, param, command):
        project_name = param.get("projectName", None)
        if not project_name:
            if command:
                linux_cmd = command.replace("\\", "/")
                project_name = os.path.basename(linux_cmd).split(" ")[0]
            if not project_name:
                project_name = uuid.uuid4().hex
        default_params = {
            "latest_time": int(time.time()),
        }
        template_id = param.get("projectTemplateId", -1)
        template = user.get_project_templates().filter(id=template_id).first()
        if template:
            default_params["template_id"] = template.id
        scan = user.get_scan_templates().first()
        if scan:
            default_params["scan_id"] = scan.id
        project, created = user.get_projects().update_or_create(name=project_name,
                                                                tenant=user.tenant,
                                                                defaults=default_params)
        if user.is_tenant_admin():
            project.departments.clear()
        else:
            project.departments.set(user.departments.all())
        return project, created

    @staticmethod
    def register_project_version(user, project, created, param):
        version_name = param.get("projectVersion")
        if not created and not version_name and project.current_version:
            version = project.current_version
        else:
            if not version_name:
                version_name = datetime.now().strftime("%Y-%m-%d")
            version, _ = IastProjectVersion.objects.update_or_create(version_name=version_name,
                                                                               project=project)
        if not project.current_version:
            project.current_version = version
            project.save()
        return project, version

    @staticmethod
    def register_agent(user, project, project_version, param, env_list, command):
        token = param.get("name")
        agent_version = param.get("version")
        port = param.get("serverPort", 0)
        if not port:
            port = 0
        network = param.get("network")
        agent, agent_created = user.get_agents().update_or_create(
            token=token, project=project, project_version=project_version, version=agent_version, user=user,
            defaults={
                "hostname": param.get("hostname"),
                "language": param.get("language"),
                "latest_time": int(time.time()),
                "ip": param.get("serverAddr"),
                "port": port,
                "path": param.get("serverPath"),
                "cmdline": command,
                "env": env_list,
                "pid": param.get("pid"),
                "ipaddresslist": get_ipaddresslist(network),
            }
        )
        return agent

    @staticmethod
    def get_command(envs):
        for env in envs:
            if "sun.java.command" in env.lower():
                return "=".join(env.split("=")[1:])
        return ""

    @staticmethod
    def get_runtime(envs):
        for env in envs:
            if "java.runtime.name" in env.lower():
                return "=".join(env.split("=")[1:])
        return ""

    @staticmethod
    def register_server(
        agent,
        hostname,
        network,
        container_name,
        server_addr,
        server_port,
        cluster_name,
        cluster_version,
        server_path,
        server_env,
        pid,
        server_ipaddresslist,
    ):
        """
        注册server,并关联server至agent
        :param agent_id:
        :param hostname:
        :param network:
        :param container_name:
        :param server_addr:
        :param server_port:
        :param server_path:
        :param server_env:
        :param pid:
        :return:
        """
        # todo 需要根据不同的语言做兼容
        if server_env:
            env = base64.b64decode(server_env).decode("utf-8")
            env = env.replace("{", "").replace("}", "")
            envs = env.split(",")
            command = AgentRegisterEndPoint.get_command(envs)
        else:
            command = ""
            env = ""
            envs = []

        try:
            port = int(server_port)
        except Exception:
            logger.info(_("The server port does not exist, has been set to the default: 0"))
            port = 0

        server_id = agent.server_id

        server = IastServer.objects.filter(id=server_id).first() if server_id else None
        ipaddresslist = json.dumps(server_ipaddresslist)
        if server:
            server.hostname = hostname
            server.network = network
            server.command = command
            server.ip = server_addr
            server.port = port
            server.pid = pid
            server.env = env
            server.cluster_name = cluster_name
            server.cluster_version = cluster_version
            server.status = "online"
            server.update_time = int(time.time())
            server.ipaddresslist = ipaddresslist
            server.save(
                update_fields=[
                    "hostname",
                    "command",
                    "ip",
                    "port",
                    "env",
                    "status",
                    "update_time",
                    "cluster_name",
                    "cluster_version",
                    "ipaddresslist",
                ]
            )
        else:
            server = IastServer.objects.create(
                hostname=hostname,
                ip=server_addr,
                port=port,
                pid=pid,
                network=network,
                env=env,
                path=server_path,
                status="online",
                container=container_name,
                container_path=server_path,
                cluster_name=cluster_name,
                cluster_version=cluster_version,
                command=command,
                runtime=AgentRegisterEndPoint.get_runtime(envs),
                create_time=int(time.time()),
                update_time=int(time.time()),
                ipaddresslist=ipaddresslist,
            )
            agent.server_id = server.id
            agent.save(update_fields=["server_id"])
            logger.info(_("Server record creation success"))

    @extend_schema(
        description="Agent Register, Data is Gzip",
        parameters=[
            DongTaiParameter.AGENT_NAME,
            DongTaiParameter.LANGUAGE,
            DongTaiParameter.VERSION,
            DongTaiParameter.PROJECT_NAME,
            DongTaiParameter.HOSTNAME,
            DongTaiParameter.NETWORK,
            DongTaiParameter.CONTAINER_NAME,
            DongTaiParameter.SERVER_ADDR,
            DongTaiParameter.SERVER_PORT,
            DongTaiParameter.SERVER_PATH,
            DongTaiParameter.SERVER_ENV,
            DongTaiParameter.PID,
            DongTaiParameter.AUTO_CREATE_PROJECT,
        ],
        responses=[{204: None}],
        tags=["Agent服务端交互协议"],
        summary="agent注册",
        methods=["POST"],
    )
    def post(self, request: Request):
        try:
            param = parse_data(request.read())
            token = param.get("name")
            version = param.get("version")
            if not token or not version:
                logger.error(f"参数错误, token={token}, version={version}")
                return R.failure(msg="参数错误")
            server_env = param.get("serverEnv")
            if server_env:
                env = base64.b64decode(server_env).decode("utf-8")
                env = env.replace("{", "").replace("}", "")
                env_list = env.split(",")
            else:
                env = ""
                env_list = []
            command = AgentRegisterEndPoint.get_command(env_list)
            with (transaction.atomic()):
                project, created = self.register_project(request.user, param, command)
                project, project_version = self.register_project_version(request.user, project, created, param)
                # logger.info(_("Register project, name={}, version={}").format(project.name, project_version.version_name))
                agent = self.register_agent(request.user, project, project_version, param, env_list, command)

                hostname = param.get("hostname")
                network = param.get("network")
                container_name = param.get("containerName")
                server_addr = param.get("serverAddr")
                server_port = param.get("serverPort")
                server_path = param.get("serverPath")
                pid = param.get("pid")
                self.register_server(
                    agent=agent,
                    hostname=hostname,
                    network=network,
                    container_name=container_name,
                    server_addr=get_ipaddress(network) if get_ipaddress(network) else server_addr,
                    server_port=server_port,
                    server_path=server_path,
                    cluster_name=param.get("clusterName", ""),
                    cluster_version=param.get("clusterVersion", ""),
                    server_env=server_env,
                    pid=pid,
                    server_ipaddresslist=get_ipaddresslist(network),
                )
                return R.success(data={"id": agent.id, "coreAutoStart": 1})
        except Exception as e:
            logger.info(f"探针注册失败,原因:{e}", exc_info=True)
            return R.failure(msg="探针注册失败")

    @staticmethod
    def get_agent_id(token, project_name, user, current_project_version_id):
        project = IastProject.objects.filter(name=project_name).first()
        if project:
            queryset = IastAgent.objects.values("id").filter(
                token=token,
                project=project,
                project_version_id=current_project_version_id,
            )
        else:
            queryset = IastAgent.objects.values("id").filter(
                token=token,
                project_name=project_name,
                project_version_id=current_project_version_id,
            )
        agent = queryset.first()
        if agent:
            return agent["id"]
        return -1


def get_ipaddress(network: str):
    try:
        dic = json.loads(network)
        res = dic[0]["ip"]
        for i in dic:
            if i["name"].startswith("en"):
                res = i["ip"]
            if i.get("isAddress", 0):
                res = i["ip"]
                break
    except KeyError:
        return ""
    except Exception as e:
        logger.info(e, exc_info=True)
        return ""
    else:
        return res


def get_ipaddresslist(network: str) -> list:
    try:
        network_data = json.loads(network)
        if isinstance(network_data, list):
            return [i["ip"] for i in network_data]
        if isinstance(network_data, dict):
            return [network_data["ip"]]
    except KeyError as e:
        logger.exception(network_data, exc_info=e)
    except Exception as e:
        logger.exception("uncatched exception: ", exc_info=e)
    return []
