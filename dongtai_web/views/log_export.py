#!/usr/bin/env python
# -*- coding:utf-8 -*-
# author:owefsad
# software: PyCharm
# project: lingzhi-webapi
from django.http import HttpResponse
from django.utils.encoding import escape_uri_path
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from rest_framework.generics import GenericAPIView
from django.utils.translation import gettext_lazy as _
from dongtai_common.endpoint import UserEndPoint
from dongtai_common.endpoint import R
from dongtai_common.models.access_log import AccessLog
from dongtai_common.models.user import User


class LogResurce(resources.ModelResource):
    user = fields.Field(
        column_name='用户',  # 导出文件中的列名
        attribute='user',  # 模型字段
        widget=ForeignKeyWidget(User, 'username')  # 通过 username 字段获取用户名
    )

    def get_export_headers(self):
        return [
            u'时间', u'用户', u'客户端', u'请求', u'URL', u'操作结果'
        ]

    class Meta:
        model = AccessLog
        fields = ('start_time', 'user', 'client_ip', 'method', 'url', 'reply_msg')
        export_order = ('start_time', 'user', 'client_ip', 'method', 'url', 'reply_msg')


class ExportMixin(object):
    @staticmethod
    def attachment_response(export_data, filename='download.xls', content_type='application/vnd.ms-excel'):
        """
        - https://segmentfault.com/q/1010000009719860
        - https://blog.csdn.net/qq_34309753/article/details/99628474

        :param export_data:
        :param filename:
        :param content_type:
        :return:
        """
        response = HttpResponse(export_data, content_type=content_type)
        response['content_type'] = content_type
        response['Content-Disposition'] = "attachment; filename*=utf-8''{}".format(escape_uri_path(filename))
        return response

    def get(self, request):
        ids = request.query_params.get('ids')
        if ids:
            ids = [int(id.strip()) for id in ids.split(',')]
            user = request.user
            if user.is_system_admin():
                queryset = AccessLog.objects.filter(id__in=ids).filter()
            elif user.is_talent_admin():
                auth_users = UserEndPoint.get_auth_users(user)
                queryset = AccessLog.objects.filter(id__in=ids, user__in=auth_users).filter()
            else:
                return R.failure(msg=_('no permission'))
            resources = self.resource_class()
            export_data = resources.export(queryset, False)
            return ExportMixin.attachment_response(getattr(export_data, 'xls'), filename='用户操作日志.xls')
        else:
            return R.failure(status=202, msg=_('Export failed, error message: Log id should not be empty'))


class LogExport(ExportMixin, GenericAPIView):
    resource_class = LogResurce