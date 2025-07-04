######################################################################
# @author      : zhaoliang
# @file        : api_route_v2_handler
# @created     : 2025-05-20
#
# @description :
######################################################################

from dongtai_protocol.report.handler.report_handler_interface import IReportHandler
from dongtai_protocol.report.report_handler_factory import ReportHandler
from dongtai_common.models.api_route import IastApiRoute, IastApiMethod, \
    IastApiResponse, IastApiParameter, \
    IastApiMethodHttpMethodRelation, HttpMethod
from dongtai_common.models.agent import IastAgent
from dongtai_common.utils import const
import logging
from django.utils.translation import gettext_lazy as _
from django.db import transaction
from dongtai_common.models.project import IastProject
from dongtai_common.models.api_route_v2 import IastApiRouteV2Schema, IastApiRouteV2
from dongtai_engine.plugins.project_time_update import project_time_stamp_update
from celery import shared_task

logger = logging.getLogger('dongtai.openapi')


@ReportHandler.register(const.REPORT_API_ROUTE_V2)
class ApiRouteV2Handler(IReportHandler):

    def parse(self):
        self.api_data = self.detail.get('apiData')

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
        parse_paths(paths, schema, agent)
    except Exception as e:
        logger.info(_('API V2 navigation log failed, why: {}').format(e), exc_info=e)

def parse_paths(paths, schema, agent):
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
        }
        item.update(para.get('schema', {}))
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