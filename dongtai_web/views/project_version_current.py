#!/usr/bin/env python

import logging

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from dongtai_common.endpoint import R, UserEndPoint
from dongtai_common.models import IastProjectVersion
from dongtai_common.models.project import IastProject
from dongtai_web.utils import extend_schema_with_envcheck, get_response_serializer

logger = logging.getLogger("django")


class _ProjectVersionCurrentSerializer(serializers.Serializer):
    version_id = serializers.CharField(help_text=_("The version id of the project"))
    project_id = serializers.IntegerField(help_text=_("The id of the project"))


_ResponseSerializer = get_response_serializer(
    status_msg_keypair=(
        ((202, _("Version does not exist")), ""),
        ((202, _("Version setting failed")), ""),
        ((201, _("Version setting success")), ""),
    )
)


class ProjectVersionCurrent(UserEndPoint):
    name = "api-v1-project-version-current"
    description = _("Set to the current application version")

    @extend_schema_with_envcheck(
        request=_ProjectVersionCurrentSerializer,
        tags=[_("Project")],
        summary=_("Projects Version Current"),
        description=_(
            "Specify the selected version as the current version of the project according to the given conditions."
        ),
        response_schema=_ResponseSerializer,
    )
    def post(self, request):
        try:
            project_id = request.data.get("project_id", 0)
            project = request.user.get_projects().filter(id=project_id).first()
            if not project:
                return R.failure(status=202, msg=_("Parameter error"))

            version_id = request.data.get("version_id", 0)
            version = project.versions.filter(id=version_id).first()
            if not version:
                return R.failure(status=202, msg=_("Parameter error"))

            project.current_version = version
            project.save()

            return R.success(msg=_("Version setting success"))

        except Exception as e:
            logger.exception("uncatched exception: ", exc_info=e)
            return R.failure(status=202, msg=_("Version setting failed"))
