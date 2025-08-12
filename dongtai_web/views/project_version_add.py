#!/usr/bin/env python
import logging

from django.utils.translation import gettext_lazy as _

from dongtai_common.endpoint import R, UserEndPoint
from dongtai_common.models import IastProjectVersion
from dongtai_web.base.project_version import VersionModifySerializer
from dongtai_web.utils import extend_schema_with_envcheck, get_response_serializer

logger = logging.getLogger("django")

_ResponseSerializer = get_response_serializer(
    status_msg_keypair=(
        ((202, _("Parameter error")), ""),
        ((201, _("Created success")), ""),
    )
)


class ProjectVersionAdd(UserEndPoint):
    name = "api-v1-project-version-add"
    description = _("New application version information")

    @extend_schema_with_envcheck(
        request=VersionModifySerializer,
        tags=[_("Project")],
        summary=_("Projects Version Add"),
        description=_(
            """Add project version information according to the given conditions;
            if the version id is specified, the corresponding version information is updated according to the given conditions."""
        ),
        response_schema=_ResponseSerializer,
    )
    def post(self, request):
        version_id = request.data.get("version_id", 0)
        project_id = request.data.get("project_id", 0)
        version_name = request.data.get("version_name", "")
        description = request.data.get("description", "")
        projects = request.user.get_projects()
        project = projects.filter(id=project_id).first()
        if project is None:
            return R.failure(msg="参数错误")

        try:
            version = project.versions.filter(id=version_id).first()
            if version is None:
                version = IastProjectVersion.objects.create(version_name=version_name, description=description, project=project)

            return R.success(msg=_("Created success"), data={
                "version_id": version.id,
                "version_name": version.version_name,
                "description": version.description,
            })

        except Exception as e:
            logger.error(e, exc_info=True)
            return R.failure(status=202, msg=_("Parameter error"))
