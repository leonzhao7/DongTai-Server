######################################################################
# @author      : bidaya0 (bidaya0@$HOSTNAME)
# @file        : api_route_search
# @created     : Wednesday Aug 18, 2021 14:31:17 CST
#
# @description :
######################################################################
import logging

from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from dongtai_common.models.api_route_v2 import IastApiRouteV2, IastApiRouteV2Schema
from dongtai_common.models.vulnerablity import IastVulnerabilityModel
from dongtai_common.endpoint import R, UserEndPoint
from dongtai_web.base.project_version import get_project_version, get_project_version_by_id
from dongtai_web.utils import extend_schema_with_envcheck, get_response_serializer


logger = logging.getLogger('dongtai-webapi')


class ApiRouteSearchRequestBodySerializer(serializers.Serializer):
    page_size = serializers.IntegerField(
        help_text=_("number per page"),
        required=False,
        default=1)
    uri = serializers.CharField(help_text=_("The uri of the api route"),
                                required=False)
    http_method = serializers.CharField(
        help_text=_("The http method of the api route"), required=False)
    project_id = serializers.IntegerField(help_text=_("The id of the project"), )
    version_id = serializers.IntegerField(
        help_text=_("The version id of the project"), required=False)
    exclude_ids = serializers.CharField(help_text=_(
        "Exclude the api route entry with the following id, this field is used to obtain the data of the entire project in batches."
    ),
        required=False)
    is_cover = serializers.ChoiceField(
        (1, 0),
        help_text=_("Whether the api is covered by detection, that is, there is associated request data in the record."
                    ),
        required=False,
    )


class ApiRouteHttpMethodSerialier(serializers.Serializer):
    httpmethod = serializers.CharField()


class ApiRouteMethodSerialier(serializers.Serializer):
    apimethod = serializers.CharField(
        help_text=_("The method bound to this API"))
    httpmethods = ApiRouteHttpMethodSerialier(
        help_text=_("The method bound to this API, in array form"), many=True)


class ApiRouteParameterSerialier(serializers.Serializer):
    id = serializers.IntegerField(help_text=_("The id of api route"))
    name = serializers.CharField(help_text=_("The name of api route"))
    parameter_type = serializers.CharField(
        help_text=_("The type of the parameter"))
    parameter_type_shortcut = serializers.CharField(help_text=_(
        "The shortcut of the parameter_type,e.g. java.lang.String -> String"))
    annotaion = serializers.CharField(
        help_text=_("The annotaion of the parameter"))
    route = serializers.IntegerField(help_text=_("The route id of parameter"))


class ApiRouteResponseSerialier(serializers.Serializer):
    id = serializers.IntegerField(help_text=_("The id of api response"))
    return_type = serializers.CharField(
        help_text=_("The return type of api route"))
    route = serializers.IntegerField(
        help_text=_("The route id of api response"))
    return_type_shortcut = serializers.CharField(
        help_text=_("The shortcut of return_type"))


class ApiRouteVulnerabitySerialier(serializers.Serializer):
    level_id = serializers.IntegerField(
        help_text=_("The vulnerablity level id "))
    hook_type_name = serializers.CharField(
        help_text=_("The vulnerablity type name"))


class ApiRouteSearchResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text=_("The id of api route"))
    path = serializers.CharField(help_text=_("The uri of api route"))
    code_class = serializers.CharField(help_text=_("The class of api route"))
    description = serializers.CharField(
        help_text=_("The description of the api route"))
    code_file = serializers.CharField(
        help_text=_("The code file of the api route"))
    controller = serializers.CharField(
        help_text=_("The controller of the api route"))
    agent = serializers.IntegerField(
        help_text=_("The id of the agent reported the api route"))
    is_cover = serializers.ChoiceField(
        (1, 0),
        help_text=_("Whether the api is covered by detection, that is, there is associated request data in the record."
                    ),
        required=False,
    )
    responses = ApiRouteResponseSerialier(many=True)
    parameters = ApiRouteParameterSerialier(many=True)
    vulnerablities = ApiRouteVulnerabitySerialier(many=True)
    method = ApiRouteMethodSerialier()


_GetResponseSerializer = get_response_serializer(
    ApiRouteSearchResponseSerializer())


class ApiRouteSearch(UserEndPoint):
    @extend_schema_with_envcheck(
        request=ApiRouteSearchRequestBodySerializer,
        tags=[_('API Route')],
        summary=_('API Route Search'),
        description=_("Get the API list corresponding to the project according to the following parameters. By default, there is no sorting. Please use the exclude_ids field for pagination."
                      ),
        response_schema=_GetResponseSerializer,
    )
    def post(self, request):
        try:
            page_size = int(request.data.get('page_size', 1))
            page_index = int(request.data.get('page_index', 0))
            uri = request.data.get('uri', None)
            method = request.data.get('http_method', None)
            project_id = request.data.get('project_id', None)
            project_id = int(project_id) if project_id else None
            version_id = request.data.get('version_id', None)
            version_id = int(version_id) if version_id else None
            exclude_id = request.data.get('exclude_ids', None)
            exclude_id = [int(i) for i in exclude_id.split(',')] if exclude_id else None
            is_cover = request.data.get('is_cover', None)
            is_cover_dict = {1: True, 0: False}
            is_cover = is_cover_dict[int(is_cover)] if is_cover is not None and is_cover != '' else None
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
        q = q & ~Q(pk__in=exclude_id) if exclude_id  else q
        q = q & Q(is_cover=is_cover) if is_cover is not None else q
        api_routes = IastApiRouteV2.objects.filter(q).order_by('id').all()
        if page_index:
            no_used, api_routes = self.get_paginator(api_routes, page_index, page_size)
        return R.success(data=convert_to_v1(api_routes))

def _parse_schema(schema):
    schema_type = schema.get("type", "")
    schema_format = ""

    if "format" in schema:
        schema_format = schema.get("format", "")
    elif "enums" in schema:
        schema_format = "enum"
    elif schema_type == "array":
        items = schema.get("items")
        if "type" in items:
            schema_format = items.get("type", "")
        elif "$ref" in items:
            ref = items.get("$ref", "")
            schema_format = f"#/{ref.split('/')[-1]}"
    elif "additionalProperties" in schema:
        schema_type = "map"
        items = schema.get("additionalProperties")
        if "type" in items:
            schema_format = items.get("type", "")
        elif "$ref" in items:
            ref = items.get("$ref", "")
            schema_format = f"#/{ref.split('/')[-1]}"
    return (schema_type, schema_format)

def _get_response(route) -> list:
    responses = route.info.get("responses", {})
    new_responses = list()
    idx = 1
    for code, res in responses.items():
        schema = res.get("schema", {})
        if "$ref" in schema:
            ref = schema.get("$ref")
            resp_type = ref.split("/")[-1]
        else:
            resp_type = schema.get("type", "")
        # (resp_type, resp_format) = _parse_schema(schema)
        new_responses.append({
            "id": idx,
            "return_type": resp_type,
            "return_type_shortcut": resp_type,
        })
        idx += 1
    return new_responses

def _get_parameters(route) -> list:
    parameters = route.info.get("parameters")
    new_parameters = list()
    for para in parameters:
        para_schema = para.get("schema", {})
        if "$ref" in para_schema:
            ref = para_schema.get("$ref")
            para_type = ref.split("/")[-1]
            paras = route.schema.dst_info.get(para_type, [])
            # 替换为真正的参数名称，in字段也只对第一层参数有意义
            if paras:
                paras[0]["name"] = para.get("name")
                paras[0]["parameter_type"] = para_type
                paras[0]["parameter_type_shortcut"] = para_type
                paras[0]["in"] = para.get("in")
            new_parameters.extend(paras)
    idx = len(new_parameters) + 1
    for para in parameters:
        if "$ref" not in para_schema:
            (para_type, para_format) = _parse_schema(para.get("schema", {}))
            new_parameters.append({
                "name": para.get("name"),
                "parameter_type": para_type,
                "parameter_type_shortcut": para_type,
                "format": para_format,
                "in": para.get("in"),
                "is_leaf": True,
                "parent": 0,
                "id": idx,
            })
            if para_format[0:2] == "#/":
                schema = route.schema.dst_info.get(para_type, [])
                para_format = para_format[2:]
            idx += 1
    return new_parameters

def convert_to_v1(api_route:list) -> list:
    route_list = list()
    for route in api_route:
        new_responses = _get_response(route)
        new_parameters = _get_parameters(route)
        api = {
            "id": route.id,
            "path": route.path,
            "code_class": route.controller,
            "description": "",
            "method": {"apimethod": route.method, "httpmethods": [route.method]},
            "controller": route.controller,
            "agent": route.agent_id,
            "from_where": route.from_where,
            "project": route.project_id,
            "project_version": route.project_version_id,
            "is_cover": route.is_cover,
            "parameters": new_parameters,
            "responses": new_responses,
            "vulnerablities": _get_vuls(route.path, route.agent_id),
        }
        route_list.append(api)
    return route_list

def _get_vuls(uri, agent_id):
    vuls = IastVulnerabilityModel.objects.filter(
        uri=uri, agent_id=agent_id,
        is_del=0).values('hook_type_id', 'level_id', 'strategy_id',
                         'strategy__vul_name').distinct().all()
    return [_get_hook_type(vul) for vul in vuls]

def _get_hook_type(vul: dict) -> dict:
    return {
        'hook_type_name': vul['strategy__vul_name'],
        'level_id': vul['level_id']
    }
