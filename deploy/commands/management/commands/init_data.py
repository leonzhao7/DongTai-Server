import json
import os
from collections import OrderedDict

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db.models import Q
from tqdm import tqdm

from dongtai_common.models.user import User
from dongtai_common.models.department import Department
from dongtai_common.models.talent import Talent

from dongtai_common.models.program_language import IastProgramLanguage
from dongtai_common.models.deploy import IastDeployDesc
from dongtai_common.models.vul_level import IastVulLevel
from dongtai_common.models.message import IastMessageType
from dongtai_common.models.project import IastProjectTemplate
from dongtai_common.models.strategy_user import IastStrategyUser
from dongtai_common.models.profile import IastProfile


class Command(BaseCommand):
    help = "load init_data"
    functions = []

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        # 必须要在数据库中创建很多内容才能运行系统，这里只考虑在一个空白数据库的环境运行，如果数据库中已经有数据，要先清空
        # 1. 创建admin用户
        Group.objects.get_or_create(name='system_admin')
        group, created = Group.objects.get_or_create(name='talent_admin')
        Group.objects.get_or_create(name='user')
        admin = User.objects.create_system_user(
            username='admin',
            password='admin',
            email='admin@e-sscard.com',
            is_global_permission = True,
            phone='13912345678',
            default_language='zh'
        )
        admin.groups.add(group)
        # principal_id, department_path, token 不知道啥意思，先不管
        kwargs = {'name': '默认部门', 'created_by': admin.id, 'parent_id': -1, 'principal_id': admin.id}
        depart,created = Department.objects.get_or_create(name='默认部门', defaults=kwargs)
        kwargs = {'talent_name': '默认部门', 'created_by': admin.id}
        talent,created = Talent.objects.get_or_create(talent_name='默认部门', defaults=kwargs)
        depart.talent.add(talent)
        admin.department.add(depart)
        
        vul_level_list = [
            {'name': 'high', 'name_value': '高危', 'name_type': '高危漏洞', 'name_type_en': 'HIGH', 'name_value_en': 'HIGH'},
            {'name': 'medium', 'name_value': '中危', 'name_type': '中危漏洞', 'name_type_en': 'MEDIUM', 'name_value_en': 'MEDIUM'},
            {'name': 'low', 'name_value': '低危', 'name_type': '低危漏洞', 'name_type_en': 'LOW', 'name_value_en': 'LOW'},
            {'name': 'info', 'name_value': '无风险', 'name_type': '无风险', 'name_type_en': 'INFO', 'name_value_en': 'INFO'},
            {'name': 'note', 'name_value': '提示', 'name_type': '提示信息', 'name_type_en': 'NOTE', 'name_value_en': 'NOTE'}
        ]
        for level in vul_level_list:
            IastVulLevel.objects.get_or_create(defaults={}, **level)

        program_language_list = [{'name': 'Java'}, {'name': 'Python'}, {'name': 'PHP'}, {'name': 'Go'}]
        for language in program_language_list:
            IastProgramLanguage.objects.get_or_create(defaults={}, **language)

        deploy_list = [
            {'middleware': 'Spring-boot/Netty/Jetty/Sofa', 'language': 'java', 'desc': '乱写的'},
            {'middleware': 'SpringBoot', 'language': 'java', 'desc': '乱写的'},
            {'middleware': 'tomcat', 'language': 'java', 'desc': '乱写的'},
            {'middleware': 'jboss', 'language': 'java', 'desc': '乱写的'},
            {'middleware': 'jetty', 'language': 'java', 'desc': '乱写的'},
            {'middleware': '东方通', 'language': 'java', 'desc': '乱写的'},
            {'middleware': 'resin', 'language': 'java', 'desc': '乱写的'},
            {'middleware': 'weblogic', 'language': 'java', 'desc': '乱写的'},
            {'middleware': 'websphere', 'language': 'java', 'desc': '乱写的'},
        ]
        for deploy in deploy_list:
            IastDeployDesc.objects.get_or_create(defaults={}, **deploy)

        kwargs = {'name': 'report'}
        IastMessageType.objects.get_or_create(defaults={}, **kwargs)

        strategy = IastStrategyUser.objects.create(
            name='全部漏洞策略', 
            user=admin, 
            status=True, 
            content='2,8,9,14,15,17,18,19,20,23,24,25,26,28,30,33,37,22,34,1,10,11,12,13,16,21,27,29,31,32,3,4,5,6,7,35,36,38,41,45,44,43,40,39,42')
        IastProjectTemplate.objects.create(
            template_name='全面扫描模板',
            user=admin,
            scan=strategy)

        profile_list = [
            {'key': 'enable_update', 'value': 'FALSE'},
            {'key': 'cpu_limit', 'value': '100'},
            {'key': 'vul_verify', 'value': '1'},
            {'key': 'auto_audit', 'value': '0'},
            {'key': 'circuit_break', 'value': '0'},
            {'key': 'data_clean', 'value': '{"clean_time": "00:00:00", "days_before": 7, "enable": true}'},
            {'key': 'dast_validation_settings', 'value': '{"{"strategy_id": [2, 8, 9, 14, 15, 17, 18, 19, 20, 23, 24, 25, 26, 28, 30, 33, 37, 22, 34, 1, 10, 11, 12, 13, 16, 21, 27, 29, 31, 32, 4, 5, 6, 7, 36, 38, 41, 45, 42, 3, 35, 39, 40, 43, 44], "validation_status": true}"'}
        ]
        for profile in profile_list:
            IastProfile.objects.get_or_create(**profile)