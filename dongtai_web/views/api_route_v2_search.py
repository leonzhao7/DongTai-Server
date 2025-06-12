######################################################################
# @author      : zhaoliang
# @file        : api_route_v2_search
# @created     : 2025-05-22
#
# @description :
######################################################################

from django.db.models import Q
from rest_framework import serializers

from django.utils.translation import gettext_lazy as _
from dongtai_common.endpoint import R, UserEndPoint
from dongtai_common.models.api_route_v2 import IastApiRouteV2
from dongtai_web.base.project_version import get_project_version, get_project_version_by_id
from dongtai_web.utils import extend_schema_with_envcheck

import logging


logger = logging.getLogger('dongtai-webapi')


class ApiRouteSearchRequestBodySerializer(serializers.Serializer):
    page_size = serializers.IntegerField(help_text=_("number per page"), required=False, default=1)
    page_index = serializers.IntegerField(help_text=_("page index"), required=False, default=0)
    uri = serializers.CharField(help_text=_("The uri of the api route"), required=False)
    method = serializers.CharField(help_text=_("The http method of the api route"), required=False)
    project_id = serializers.IntegerField(help_text=_("The id of the project"), )
    version_id = serializers.IntegerField(help_text=_("The version id of the project"), required=False)


class ApiRouteV2Search(UserEndPoint):
    @extend_schema_with_envcheck(
        request=ApiRouteSearchRequestBodySerializer,
        tags=[_('API Route v2')],
        summary=_('API Route v2 Search'),
        description=_("Get the v2 API list corresponding to the project according to the following parameters. By default, there is no sorting. Please use the exclude_ids field for pagination."
                      ),
    )
    def post(self, request):
        try:
            page_size = int(request.data.get('page_size', 1))
            page_index = int(request.data.get('page_index', 0))
            method = request.data.get('method', None)
            uri = request.data.get('uri', None)
            project_id = int(request.data.get('project_id')) if 'project_id' in request.data else None
            version_id = int(request.data.get('version_id')) if 'version_id' in request.data else None
        except Exception as e:
            logger.error(e)
            return R.failure(_("Parameter error"))

        if not version_id:
            current_project_version = get_project_version(project_id)
        else:
            current_project_version = get_project_version_by_id(version_id)
        q = Q(project_version_id=current_project_version.get("version_id", 0), project_id=project_id)
        q = q & Q(path__icontains=uri) if uri else q
        q = q & Q(method=method) if method else q
        api_routes = IastApiRouteV2.objects.filter(q).order_by('id').all()
        if page_index:
            no_used, api_routes = self.get_paginator(api_routes, page_index, page_size)
        return R.success(data=serialize(api_routes))

def serialize(api_route:list) -> dict:
    schema_version = dict()
    route_version = dict()
    for route in api_route:
        if route.project_version.version_name not in route_version:
            route_version[route.project_version.version_name] = dict()
            route_version[route.project_version.version_name]['paths'] = dict()
            route_version[route.project_version.version_name]['tags'] = list()
            route_version[route.project_version.version_name]['controller'] = set()
        if route.path not in route_version[route.project_version.version_name]['paths']:
            route_version[route.project_version.version_name]['paths'][route.path] = dict()
        route_version[route.project_version.version_name]['paths'][route.path][route.method] = route.info
        route_version[route.project_version.version_name]['controller'].add(route.controller)
        # route_version[route.project_version.version_name]['tags'].append({'name': route.controller, 'description': route.controller})
        schema_version[route.schema.project_version.version_name] = route.schema

    for version, schema in schema_version.items():
        if version in route_version:
            route_version[version][schema.name] = schema.info
    for version, route in route_version.items():
        route['tags'] = list()
        for controller in route.get('controller', set()):
            route['tags'].append({'name': controller, 'description': controller})
        del route['controller']
    data = {'info': {'description': 'Api Documentation','version': '1.0'}, 'api': route_version}
    return data
