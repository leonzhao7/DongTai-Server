#!/usr/bin/env python
import ipaddress
import logging
import time
from urllib.parse import urlparse, urlunparse

from django.db import transaction
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from dongtai_common.common.utils import disable_cache
from dongtai_common.endpoint import R, UserEndPoint
from dongtai_common.models.project import IastProject
from dongtai_common.models.project_version import IastProjectVersion
from dongtai_common.models.strategy_user import IastStrategyUser
from dongtai_common.utils.request_type import Request
from dongtai_engine.common.queryset import get_scan_id
from dongtai_web.utils import extend_schema_with_envcheck, get_response_serializer

logger = logging.getLogger("django")


class _ProjectsAddBodyArgsSerializer(serializers.Serializer):
    name = serializers.CharField(help_text=_("The name of project"))
    template_id = serializers.IntegerField(
        help_text=_("The id corresponding to the project template. required to specfic, use 1 as default.")
    )
    version_name = serializers.CharField(required=False, help_text=_("The version name of the project"))
    pid = serializers.IntegerField(
        required=False,
        help_text=_("The id of the project, use it when try to modify existed project."),
    )
    description = serializers.CharField(required=False, help_text=_("Description of the project"))
    vul_validation = serializers.IntegerField(
        help_text="vul validation switch",
    )
    base_url = serializers.CharField(
        required=False,
    )
    test_req_header_key = serializers.CharField(
        required=False,
    )
    test_req_header_value = serializers.CharField(
        required=False,
    )


_ResponseSerializer = get_response_serializer(
    status_msg_keypair=(
        ((202, _("Parameter error")), ""),
        ((201, _("Created success")), ""),
        ((202, _("Agent has been bound by other application")), ""),
        ((203, _("Failed to create, the application name already exists")), ""),
    )
)


class ProjectAdd(UserEndPoint):
    name = "api-v1-project-add"
    description = _("New application")

    @extend_schema_with_envcheck(
        request=_ProjectsAddBodyArgsSerializer,
        tags=[_("Project")],
        summary=_("Projects Add"),
        description=_(
            """Create a new project according to the given conditions;
            when specifying the project id, update the item corresponding to the id according to the given condition."""
        ),
        response_schema=_ResponseSerializer,
    )
    def post(self, request:Request):
        try:
            with transaction.atomic():
                name = str(request.data.get("name"))
                mode = "插桩模式"
                scan_id = int(request.data.get("scan_id", 5))
                template_id = int(request.data.get("template_id", 1))
                scan = IastStrategyUser.objects.filter(id=scan_id).first()
                base_url = request.data.get("base_url", None)
                test_req_header_key = request.data.get("test_req_header_key", None)
                test_req_header_value = request.data.get("test_req_header_value", None)
                vul_validation = request.data.get("vul_validation", None)
                pid = request.data.get("pid", 0)
                enable_log = request.data.get("enable_log", None)
                log_level = request.data.get("log_level", None)
                if len(name) > 64:
                    return R.failure(msg="项目名长度需在64个字符以内")
                if base_url and not url_validate(base_url):
                    return R.failure(status=202, msg=_("base_url validate failed"))
                if not scan_id or not name or not mode:
                    logger.error("require base scan_id and name")
                    return R.failure(status=202, msg=_("Required scan strategy and name"))

                if pid:
                    project = request.user.get_projects().filter(id=pid).first()
                else:
                    project = request.user.get_projects().filter(name=name).first()
                    if not project:
                        project = IastProject.objects.create(name=name, tenant=request.user.tenant)
                    else:
                        return R.failure(status=203, msg=_("Failed to create, the application name already exists"))
                if not project:
                    return R.failure(status=203, msg="操作失败")

                vid = request.data.get("vid")
                version_name = request.data.get("version_name", "V1.0")
                description = request.data.get("description", "")
                if vid:
                    version = IastProjectVersion.objects.filter(Q(id=vid) & Q(project=project)).update(
                        version_name=version_name, description=description)
                else:
                    version = IastProjectVersion.objects.create(
                        version_name=version_name, description=description, project=project)
                    project.current_version = version
                if not version:
                    return R.failure(status=203, msg="操作失败",)

                project.name = name
                project.scan = scan
                project.mode = mode
                project.template_id = template_id
                project.latest_time = int(time.time())
                project.log_level = project.generate_log_level(enable_log, log_level)
                if vul_validation is not None:
                    project.vul_validation = vul_validation
                if base_url:
                    project.base_url = remove_ending_slash(base_url)
                if test_req_header_key:
                    project.test_req_header_key = test_req_header_key
                if test_req_header_value:
                    project.test_req_header_value = test_req_header_value
                project.save(
                    update_fields=[
                        "name",
                        "scan_id",
                        "mode",
                        "latest_time",
                        "vul_validation",
                        "base_url",
                        "test_req_header_key",
                        "test_req_header_value",
                        "template_id",
                        "log_level",
                        "current_version_id",
                    ]
                )
                project.departments.set(request.user.departments.all())
                disable_cache(get_scan_id, (project.id))
                return R.success(
                    data={
                        "project_id": project.id,
                        "project_version_id": 1,
                    },
                    msg="操作成功",
                )
        except Exception as e:
            logger.exception("uncatched exception: ", exc_info=e)
            return R.failure(status=202, msg=_("Parameter error"))


def url_validate(url):
    parse_re = urlparse(url)
    if parse_re.scheme not in ("http", "https") or parse_re.hostname in ("127.0.0.1", "localhost"):
        return False
    return ip_validate(parse_re.hostname) if is_ip(parse_re.hostname) else True


def ip_validate(ip):
    try:
        ipadrs = ipaddress.IPv4Address(ip)
        if int(ipaddress.IPv4Address("127.0.0.1")) < int(ipadrs) < int(ipaddress.IPv4Address("127.255.255.255")):
            logger.error("127.x.x.x address not allowed")
            return False
        if int(ipaddress.IPv4Address("10.0.0.1")) < int(ipadrs) < int(ipaddress.IPv4Address("10.255.255.255")):
            logger.error("10.x.x.x address not allowed")
            return False
    except ipaddress.AddressValueError:
        pass
    return True


def is_ip(address):
    return not address.split(".")[-1].isalpha()


def remove_ending_slash(sentence):
    while sentence.endswith("/"):
        sentence = sentence[: -1]
    return sentence
