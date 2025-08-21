from django.db.models import Q

from dongtai_common.models.project import (
    IastProject,
    IastProjectTemplate,
    VulValidation,
)
from rest_framework import serializers
from dongtai_common.endpoint import UserEndPoint, R, TalentAdminEndPoint
from rest_framework import viewsets
from django.utils.translation import gettext_lazy as _
from dongtai_web.utils import extend_schema_with_envcheck, get_response_serializer
from dongtai_common.permissions import UserPermission, ScopedPermission, SystemAdminPermission, TalentAdminPermission


class PaginationSerializer(serializers.Serializer):
    page_size = serializers.IntegerField(default=20,
                                         help_text=_('Number per page'))
    page = serializers.IntegerField(default=1, help_text=_('Page index'))


class ProjectTemplateCreateArgsSerializer(serializers.Serializer):
    id = serializers.IntegerField(
        min_value=1,
        help_text=_("The id corresponding to the scanning strategy."),
        required=False)
    template_name = serializers.CharField(help_text=_('The name of project'))
    scan_id = serializers.IntegerField(
        min_value=1,
        max_value=2**32,
        help_text=_("The id corresponding to the scanning strategy."))
    vul_validation = serializers.IntegerField(
        min_value=0,
        max_value=2,
        help_text="vul validation switch, 0-FOLLOW_GLOBAL, 1-ENABLE,2-DISABLE")
    blacklist = serializers.SerializerMethodField(required=False)
    is_system = serializers.IntegerField(required=False, default=0)

    def get_blacklist(self, obj):
        return []

    class Meta:
        model = IastProjectTemplate
        fields = [
            'id',
            'template_name',
            'scan_id',
            'vul_validation',
            'blacklist',
        ]


def template_create(data, user):
    if not user.is_super_admin():
        data['tenant_id'] = user.tenant.id
    data['user_id'] = user.id
    for field in ["blacklist"]:
        if field in data:
            del data[field]
    project_template = IastProjectTemplate.objects.create(**data)
    pk = project_template.id
    return pk


def template_update(pk, data, user):
    if not user.is_super_admin():
        data['tenant_id'] = user.tenant.id
    data['user_id'] = user.id
    for field in ["blacklist"]:
        if field in data:
            del data[field]
    IastProjectTemplate.objects.filter(Q(pk=pk) & Q(tenant=user.tenant)).update(**data)


class IastProjectTemplateView(TalentAdminEndPoint, viewsets.ViewSet):
    name = "api-v1-agent-project-template"
    description = _("project_template")

    permission_classes_by_action = {'list': (UserPermission, )}

    def get_permissions(self):
        try:
            return [
                permission() for permission in
                self.permission_classes_by_action[self.action]
            ]
        except KeyError:
            return [permission() for permission in self.permission_classes]

    @extend_schema_with_envcheck(request=ProjectTemplateCreateArgsSerializer,
                                 summary=_('Create project template'),
                                 description=_("Create project template"),
                                 tags=[_('projectemplate')])
    def create(self, request):
        ser = ProjectTemplateCreateArgsSerializer(data=request.data)
        ser.is_valid()
        if ser.errors:
            return R.failure(data=ser.errors)
        data = {}
        for field in ProjectTemplateCreateArgsSerializer.Meta.fields:
            if field in request.data and field != 'id':
                data[field] = request.data[field]
        template_create(data, request.user)
        return R.success()

    @extend_schema_with_envcheck(request=ProjectTemplateCreateArgsSerializer,
                                 summary=_('Update project template'),
                                 description=_("Update project template"),
                                 tags=[_('projectemplate')])
    def update(self, request, pk):
        ser = ProjectTemplateCreateArgsSerializer(data=request.data)
        ser.is_valid()
        if ser.errors:
            return R.failure(data=ser.errors)
        data = {}
        for field in ProjectTemplateCreateArgsSerializer.Meta.fields:
            if field in request.data and field != 'id':
                data[field] = request.data[field]
        template_update(pk, data, request.user)
        return R.success()

    @extend_schema_with_envcheck([PaginationSerializer],
                                 summary=_('List project template'),
                                 description=_("List project template"),
                                 tags=[_('projectemplate')])
    def list(self, request):
        ser = PaginationSerializer(data=request.GET)
        ser.is_valid()
        if ser.errors:
            return R.failure(data=ser.errors)
        page_size = ser.validated_data['page_size']
        page = ser.validated_data['page']
        summary, templates = self.get_paginator(
            IastProjectTemplate.objects.filter(Q(tenant=request.user.tenant) | Q(tenant__isnull=True)).values().order_by(
                '-latest_time').all(), page, page_size)
        return R.success(
            data=ProjectTemplateCreateArgsSerializer(templates,
                                                     many=True).data,
            page=summary,
        )

    @extend_schema_with_envcheck(summary=_('delete project template'),
                                 description=_("delete project template"),
                                 tags=[_('projectemplate')])
    def delete(self, request, pk):
        IastProjectTemplate.objects.filter(Q(pk=pk) & Q(tenant=request.user.tenant)).delete()
        return R.success()

    @extend_schema_with_envcheck(summary=_('get project template'),
                                 description=_("get project template"),
                                 tags = [_('projectemplate')])
    def retrieve(self, request, pk):
        obj = IastProjectTemplate.objects.filter(Q(pk=pk) & Q(tenant=request.user.tenant)).values().first()
        if not obj:
            return R.failure()
        return R.success(data=ProjectTemplateCreateArgsSerializer(obj).data)