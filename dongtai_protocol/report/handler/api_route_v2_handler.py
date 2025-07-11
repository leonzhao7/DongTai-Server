######################################################################
# @author      : zhaoliang
# @file        : api_route_v2_handler
# @created     : 2025-05-20
#
# @description :
######################################################################
import logging

from django.utils.translation import gettext_lazy as _
from celery import shared_task

from dongtai_common.utils import const
from dongtai_common.models.agent import IastAgent
from dongtai_common.models.api_route_v2 import IastApiRouteV2Schema, IastApiRouteV2
from dongtai_protocol.report.handler.report_handler_interface import IReportHandler
from dongtai_protocol.report.report_handler_factory import ReportHandler
import json

logger = logging.getLogger('dongtai.openapi')


@ReportHandler.register(const.REPORT_API_ROUTE_V2)
class ApiRouteV2Handler(IReportHandler):

    def parse(self):
        self.api_data = self.detail.get('apiData')
        print(f"{json.dumps(self.api_data)}")

    def save(self):
        api_route_v2_gather.delay(self.agent_id, self.api_data)


@shared_task(queue='dongtai-api-route-v2-handler')
def api_route_v2_gather(agent_id, api_data):
    try:
        agent = IastAgent.objects.filter(pk=agent_id)[0:1]
        if not agent:
            raise ValueError(_("No such agent"))
        agent = agent[0]
        components = api_data.get('components')
        schema = None
        if len(components) > 0 and len(components.get('schemas', {})) > 0:
            schema, created = IastApiRouteV2Schema.objects.update_or_create(
                name="components", 
                project=agent.bind_project, 
                project_version=agent.project_version,
                defaults={'info':components}
            )
        paths = api_data.get('paths')
        _parse_paths(paths, schema, agent)
    except Exception as e:
        logger.info(_('API V2 navigation log failed, why: {}').format(e), exc_info=e)

def _parse_schemas(components:dict) -> dict:
    result = dict()
    idx = 1
    schemas = components.get("schemas", {})
    for schema_name, schema_info in schemas.items():
        schema_object_list = _parse_schema_object(schema_name, schema_name, 0, idx, schemas, [])
        result[schema_name] = schema_object_list
        idx += len(schema_object_list)
    return result

def _parse_schema_object(alias_name, schema_name, parent_id, object_id, schema_dict, ref_set) -> list:
    schema_object = schema_dict.get(schema_name)
    if schema_object is None:
        return []

    is_leaf = True
    child_object_list = []
    (schema_type, schema_format) = _get_type_format(schema_object)
    if schema_name in ref_set:
        schema_type = schema_name
        schema_format = ""
    elif "properties" in schema_object:
        is_leaf = False
        child_object_list = _parse_schema_properties(schema_object, object_id, schema_dict, ref_set+[schema_name])

    object_list = [{
        "name": alias_name,
        "parameter_type": schema_type,
        "parameter_type_shortcut": schema_type,
        "format": schema_format,
        "is_leaf": is_leaf,
        "parent": parent_id,
        "id": object_id,
    }]
    object_list.extend(child_object_list)

    return object_list

def _parse_schema_properties(schema_object, parent_id, schema_dict, ref_set) -> list:
    result_list = []
    self_id = parent_id + 1
    for prop_name, prop_dict in schema_object.get("properties").items():
        ref_result = []
        is_leaf = True
        if "$ref" in prop_dict:
            ref = prop_dict.get("$ref")
            ref_name = ref.split("/")[-1]
            if ref_name in ref_set:
                prop_type = f"#/{ref_name}"
                prop_format = ""
            else:
                result = _parse_schema_object(prop_name, ref_name, parent_id, self_id, schema_dict, ref_set)
                result_list.extend(result)
                self_id += len(result)
                continue
        else:
            (prop_type, prop_format) = _get_type_format(prop_dict)
            if prop_type in ["array", "map"] and prop_format[0:2] == "#/":
                if prop_format[2:] not in ref_set:
                    prop_format = prop_format[2:]
                    ref_result = _parse_schema_object(prop_name, prop_format, self_id, self_id, schema_dict, ref_set)
                    ref_result.pop(0)
                    is_leaf = False

        result_list.append({
            "name": prop_name,
            "parameter_type": prop_type,
            "parameter_type_shortcut": prop_type,
            "format": prop_format,
            "is_leaf": is_leaf,
            "parent": parent_id,
            "id": self_id,
        })
        result_list.extend(ref_result)
        self_id += len(ref_result)+1
    return result_list

def _get_type_format(prop_dict:dict) -> (str, str):
    prop_type = prop_dict.get("type", "")
    prop_format = ""
    if "format" in prop_dict:
        prop_format = prop_dict.get("format", "")
    elif "enums" in prop_dict:
        prop_format = "enum"
    elif prop_type == "array":
        items = prop_dict.get("items")
        if "type" in items:
            prop_format = items.get("type", "")
        elif "$ref" in items:
            ref = items.get("$ref", "")
            prop_format = f"#/{ref.split('/')[-1]}"
    elif "additionalProperties" in prop_dict:
        prop_type = "map"
        items = prop_dict.get("additionalProperties")
        if "type" in items:
            prop_format = items.get("type", "")
        elif "$ref" in items:
            ref = items.get("$ref", "")
            prop_format = f"#/{ref.split('/')[-1]}"
    return (prop_type, prop_format)

def _parse_paths(paths, schema, agent):
    for path_name, path_data in paths.items():
        for method_name, method_data in path_data.items():
            tags = method_data.get('tags', [])
            swagger = convert_to_swagger(path_name, method_name, method_data)
            IastApiRouteV2.objects.update_or_create(
                path=path_name,
                method=method_name.upper(),
                project=agent.bind_project,
                project_version=agent.project_version,
                defaults={'agent': agent, 'schema':schema, 'controller':tags[0], 'info':swagger}
            )

def _parse_schema_object(alias_name, schema_name, parent_id, object_id, schema_dict, ref_set) -> list:
    schema_object = schema_dict.get(schema_name)
    if schema_object is None:
        return []

    is_leaf = True
    child_object_list = []
    (schema_type, schema_format) = _get_type_format(schema_object)
    if schema_name in ref_set:
        schema_type = schema_name
        schema_format = ""
    elif "properties" in schema_object:
        is_leaf = False
        child_object_list = _parse_schema_properties(schema_object, object_id, schema_dict, ref_set+[schema_name])

    object_list = [{
        "name": alias_name,
        "parameter_type": schema_type,
        "parameter_type_shortcut": schema_type,
        "format": schema_format,
        "is_leaf": is_leaf,
        "parent": parent_id,
        "id": object_id,
    }]
    object_list.extend(child_object_list)

    return object_list

def _parse_schema_properties(schema_object, parent_id, schema_dict, ref_set) -> list:
    result_list = []
    self_id = parent_id + 1
    for prop_name, prop_dict in schema_object.get("properties").items():
        ref_result = []
        is_leaf = True
        if "$ref" in prop_dict:
            ref = prop_dict.get("$ref")
            ref_name = ref.split("/")[-1]
            if ref_name in ref_set:
                prop_type = f"#/{ref_name}"
                prop_format = ""
            else:
                result = _parse_schema_object(prop_name, ref_name, parent_id, self_id, schema_dict, ref_set)
                result_list.extend(result)
                self_id += len(result)
                continue
        else:
            (prop_type, prop_format) = _get_type_format(prop_dict)
            if prop_type in ["array", "map"] and prop_format[0:2] == "#/":
                if prop_format[2:] not in ref_set:
                    prop_format = prop_format[2:]
                    ref_result = _parse_schema_object(prop_name, prop_format, self_id, self_id, schema_dict, ref_set)
                    ref_result.pop(0)
                    is_leaf = False

        result_list.append({
            "name": prop_name,
            "parameter_type": prop_type,
            "parameter_type_shortcut": prop_type,
            "format": prop_format,
            "is_leaf": is_leaf,
            "parent": parent_id,
            "id": self_id,
        })
        result_list.extend(ref_result)
        self_id += len(ref_result)+1
    return result_list

def convert_to_swagger(path_name, method_name, path_data):
    swagger = dict()
    parameters = list()
    responses = dict()
    swagger['tags'] = path_data.get('tags', [])
    swagger['operationId'] = path_data.get('operationId', (method_name + "_" + path_name.replace("/","_")).lower())
    swagger['summary'] = method_name + " " + path_name
    body = path_data.get('requestBody', None)
    if body is not None:
        content = body.get('content', None)
        if content is not None:
            for consume, schema in content.items():
                swagger['consumes'] = consume
                schema = schema.get('schema', {})
                ref_parts = schema.get('$ref', '').split('/')
                name = next((part for part in reversed(ref_parts) if part), '')
                para = {
                    'in': 'body',
                    'name': name,
                    'description': name,
                    'required': body.get('required', True),
                    'schema': schema
                }
                parameters.append(para)
    paras = path_data.get('parameters', [])
    for para in paras:
        item = {
            'in': 'query',
            'name': para.get('name', ''),
            'description': para.get('name', ''),
            'required': para.get('required', True),
            'schema': para.get('schema', {})
        }
        # item.update(para.get('schema', {}))
        parameters.append(item)
    old_responses = path_data.get('responses', {})
    if old_responses is not None:
        for code, content_data in old_responses.items():
            content = content_data.get('content', {})
            if content is not None:
                for produce, schema in content.items():
                    swagger['produces'] = produce
                    resp = {
                        'description': content_data.get('description', f"{code}"),
                        'schema': schema.get('schema', {})
                    }
                    responses[code] = resp
    swagger['parameters'] = parameters
    swagger['responses'] = responses
    swagger['deprecated'] = False
    return swagger