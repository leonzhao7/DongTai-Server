#!/usr/bin/env python
import logging

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from dongtai_common.endpoint import R, UserEndPoint
from dongtai_common.models.project_version import IastProjectVersion
from dongtai_web.utils import extend_schema_with_envcheck, get_response_serializer

logger = logging.getLogger("django")


class _VersionListDataSerializer(serializers.ModelSerializer):
    version_id = serializers.IntegerField(source="IastProjectVersion.id", help_text=_("The version id of the project"))
    version_name = serializers.CharField(help_text=_("The version name of the project"))
    description = serializers.CharField(help_text=_("Description of the project versoin"))
    current_version = serializers.IntegerField(
        help_text=_("Whether it is the current version, 1 means yes, 0 means no.")
    )

    class Meta:
        model = IastProjectVersion
        fields = ["version_id", "version_name", "current_version", "description"]


_ProjectVersionListResponseSerializer = get_response_serializer(_VersionListDataSerializer(many=True))


class ProjectVersionList(UserEndPoint):
    name = "api-v1-project-version-list"
    description = _("View application version list")

    @extend_schema_with_envcheck(
        tags=[_("Project"), "集成"],
        summary=_("Projects Version List"),
        description=_("Get the version information list of the item corresponding to the id"),
        response_schema=_ProjectVersionListResponseSerializer,
    )
    def get(self, request, project_id):
        try:
            project = request.user.get_projects().filter(id=project_id).first()
            if not project:
                return R.failure(status=203, msg=_("no permission"))

            data = []
            if project.versions:
                data = [
                    {
                        "version_id": version.id,
                        "version_name": version.version_name,
                        "current_version": 1 if project.current_version and version.id == project.current_version.id else 0,
                        "description": version.description,
                    } for version in project.versions.all()
                ]

            return R.success(msg=_("Search successful"), data=data)
        except Exception as e:
            logger.exception("uncatched exception: ", exc_info=e)
            return R.failure(status=202, msg=_("Parameter error"))
