import time

from django.db import transaction
from django.db.models import Q
from django.db.models.query import QuerySet
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from dongtai_common.models.project import IastProject
from dongtai_common.models.project_version import IastProjectVersion


class VersionModifySerializer(serializers.Serializer):
    version_id = serializers.CharField(help_text=_("The version id of the project"))
    version_name = serializers.CharField(help_text=_("The version name of the project"))
    description = serializers.CharField(help_text=_("Description of the project versoin"))
    project_id = serializers.IntegerField(help_text=_("The id of the project"))


def get_project_version(project_id, auth_users=None):
    project = IastProject.objects.filter(id=project_id).first()
    if project and project.current_version:
        version = project.current_version
        current_project_version = {
            "version_id": version.id,
            "version_name": version.version_name,
            "description": version.description,
        }

    else:
        current_project_version = {
            "version_id": 0,
            "version_name": "",
            "description": "",
        }
    return current_project_version


def get_project_version_by_id(version_id):
    versionInfo = IastProjectVersion.objects.filter(pk=version_id).first()
    if versionInfo:
        current_project_version = {
            "version_id": versionInfo.id,
            "version_name": versionInfo.version_name,
            "description": versionInfo.description,
        }
    else:
        current_project_version = {
            "version_id": 0,
            "version_name": "",
            "description": "",
        }
    return current_project_version


class ProjectsVersionDataSerializer(serializers.Serializer):
    description = serializers.CharField(help_text=_("Description of the project"))
    version_id = serializers.CharField(help_text=_("The version id of the project"))
    version_name = serializers.CharField(help_text=_("The version name of the project"))
