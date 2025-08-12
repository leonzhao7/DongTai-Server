#!/usr/bin/env python
import logging

from django.utils.translation import gettext_lazy as _

from dongtai_common.endpoint import R, UserEndPoint
from dongtai_web.base.project_version import VersionModifySerializer
from dongtai_web.utils import extend_schema_with_envcheck, get_response_serializer

logger = logging.getLogger("django")

_ResponseSerializer = get_response_serializer(
    status_msg_keypair=(
        ((202, _("Parameter error")), ""),
        ((201, _("Update completed")), ""),
    )
)


class ProjectVersionUpdate(UserEndPoint):
    name = "api-v1-project-version-update"
    description = _("Update application version information")

    @extend_schema_with_envcheck(
        request=VersionModifySerializer,
        tags=[_("Project")],
        summary=_("Projects Version Update"),
        description=_("Update the version information of the corresponding version id."),
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

            version.version_name = request.data.get("version_name", "")
            version.description = request.data.get("description", "")
            version.save()

            return R.success(msg=_("Update completed"))

        except Exception as e:
            logger.exception("uncatched exception: ", exc_info=e)
            return R.failure(status=202, msg=_("Parameter error"))
