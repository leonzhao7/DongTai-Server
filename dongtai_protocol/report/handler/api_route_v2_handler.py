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
                name="api_data", 
                project=agent.bind_project, 
                project_version=agent.project_version,
                defaults={'info':api_data}
            )
        schemas_obj = replace_ref(components)
        paths = api_data.get('paths')
        parse_paths(paths, schemas_obj, schema, agent)
    except Exception as e:
        logger.info(_('API V2 navigation log failed, why: {}').format(e), exc_info=e)


def parse_paths(paths, schemas_obj, schema, agent):
    for path_name, path_data in paths.items():
        for method_name, method_data in path_data.items():
            tags = method_data.get('tags', [])
            # swagger = convert_to_swagger(path_name, method_name, method_data)
            para_list = _build_path_parameter(method_data, schemas_obj)
            resp_list = _build_path_response(method_data, schemas_obj)
            IastApiRouteV2.objects.update_or_create(
                path=path_name,
                method=method_name.upper(),
                project=agent.bind_project,
                project_version=agent.project_version,
                defaults={'agent': agent, 'schema':schema, 'controller':tags[0], 'parameters':para_list, 'response':resp_list, 'info':method_data}
            )

def replace_ref(components:dict) -> dict:
    new_schemas = dict()
    schemas = components.get("schemas")
    for schema_name, schema_info in schemas.items():
        new_schemas[schema_name] = _replace_ref_item(schema_name, schema_info, schemas, set())
    return new_schemas

def _replace_ref_item(schema_name:str, schema_info:dict, schemas:dict, ref_set:set) -> dict:
    if "$ref" in schema_info:
        new_ref_name = schema_info.get("$ref", "").split("/")[-1]
        if new_ref_name in ref_set:
            return {"name": new_ref_name, "type": "#/" + new_ref_name,}
        ref_set.add(new_ref_name)
        new_schema_info = schemas.get(new_ref_name)
        ref_item = _replace_ref_item(new_ref_name, new_schema_info, schemas, ref_set)
        if "properties" not in ref_item:
            ref_item["format"] = ref_item.get("type", "")
        ref_item["type"] = "#/" + new_ref_name
        return ref_item

    schema_type = schema_info.get("type", "")
    schema_format = schema_info.get("format", "")
    if "properties" in schema_info:
        ref_set.add(schema_name)
        new_prop = dict()
        for prop_name, prop_info in schema_info.get("properties", {}).items():
            new_prop[prop_name] = _replace_ref_item(prop_name, prop_info, schemas, ref_set)
        return {"name": schema_name, "type": schema_type, "properties": new_prop}

    if schema_type == "array":
        items = schema_info.get("items", {})
        return _replace_collection_item(schema_name, schema_type, items, schema_info, schemas, ref_set)
    if "additionalProperties" in schema_info:
        schema_type = "map"
        items = schema_info.get("additionalProperties", {})
        return _replace_collection_item(schema_name, schema_type, items, schema_info, schemas, ref_set)

    if "enums" in schema_info:
        schema_format = "enums"
    if "name" in schema_info:
        return {"name": schema_info.get("name"), "type": schema_type, "format": schema_format}
    else:
        return {"type": schema_type, "format": schema_format}

def _replace_collection_item(schema_name:str, schema_type:str, items:dict, schema_info, schemas, ref_set) -> dict:
    ref_set.add(schema_name)
    collect_item = _replace_ref_item(schema_name, items, schemas, ref_set)
    schema_format = schema_info.get("format", "")
    if collect_item and len(collect_item) > 0:
        schema_format = collect_item.get("type", "")
    return {"type": schema_type, "format": schema_format, "items": collect_item}

def _build_path_parameter(method_data:dict, schemas:dict) -> list:
    para_list = list()
    parameters = method_data.get("parameters", [])
    index = 1
    for para_data in parameters:
        ori_schema = para_data.get("schema", {})
        new_schema = _replace_ref_item(para_data.get("name", ""), ori_schema, schemas, set())
        para_data["schema"] = new_schema
        para = _para_schema_to_list(para_data.get("name", ""), para_data, 0, index, schemas, True)
        para_list.extend(para)
        index += len(para)
    body = method_data.get("requestBody", {}).get("content", {})
    if body:
        body_type, body_data = next(iter(body.items()))
        ori_schema = body_data.get("schema", {})
        new_schema = _replace_ref_item("", ori_schema, schemas, set())
        body_data["schema"] = new_schema
        body_list = _para_schema_to_list("", body_data, 0, index, schemas, True)
        if body_list and len(body_list) > 0:
            body_list[0]["in"] = "Body"
        para_list.extend(body_list)
    return para_list

def _para_schema_to_list(para_name:str, para_data:dict, parent_id:int, self_id:int, schemas:dict, is_first:bool=False):
    para_schema = para_data.get("schema", {})
    para_type = para_schema.get("type", "")
    para_format = para_schema.get("format", "")
    para = {
        "name": para_name,
        "parameter_type": para_type,
        "parameter_type_shortcut": para_type,
        "format": para_format,
        "in": para_data.get("in", ""),
        "is_leaf": True,
        "parent": parent_id,
        "id": self_id,
    }

    if para_type == "array" or para_type == "map":
        para_list = [para]
        if para_format in ["boolean", "string", "integer"]:
            return para_list
        items = para_schema.get("items", {})
        para_data["schema"] = items
        collect_list = _para_schema_to_list(para_name, para_data, self_id, self_id+1, schemas)
        if collect_list and len(collect_list) == 1 and len(collect_list[0].get("format", "")) == 0:
            return para_list
        if collect_list:
            collect_list[0]["name"] = ""
        para_list.extend(collect_list)
        para_list[0]["is_leaf"] = False
        return para_list

    if "properties" in para_schema:
        if is_first:
            para["is_leaf"] = False
            para_list = [para]
            index = 1
            parent_id = self_id
        else:
            para_list = list()
            index = 0
        properties = para_schema.get("properties", {})
        for prop_name, prop_data in properties.items():
            prop_list = _para_schema_to_list(prop_name, {"schema": prop_data}, parent_id, self_id+index, schemas)
            para_list.extend(prop_list)
            index += len(prop_list)
        return para_list

    return [para]

def _build_path_response(method_data, schemas):
    res_list = list()
    responses = method_data.get("responses", [])
    index = 1
    for status_code, content in responses.items():
        for produce, schema in content.get("content", {}).items():
            ori_schema = schema.get("schema", {})
            new_schema = _replace_ref_item("", ori_schema, schemas, set())
            schema["schema"] = new_schema
            res = _para_schema_to_list(f"{status_code}", schema, 0, index, schemas, True)
            res_list.extend(res)
            index += len(res)
    return res_list

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