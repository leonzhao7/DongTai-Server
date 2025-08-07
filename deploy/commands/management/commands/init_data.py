from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from dongtai_common.models.user_role import UserRole, RoleLevel
from dongtai_common.models.user import User
from dongtai_common.models.user_department import UserDepartment
from dongtai_common.models.user_tenant import UserTenant
from dongtai_common.models.program_language import IastProgramLanguage
from dongtai_common.models.deploy import IastDeployDesc
from dongtai_common.models.vul_level import IastVulLevel
from dongtai_common.models.message import IastMessageType
from dongtai_common.models.project import IastProjectTemplate
from dongtai_common.models.strategy_user import IastStrategyUser
from dongtai_common.models.profile import IastProfile
from dongtai_common.models.vulnerablity import IastVulnerabilityStatus


class Command(BaseCommand):
    help = "load init_data"
    functions = []

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        # 必须要在数据库中创建很多内容才能运行系统，这里只考虑在一个空白数据库的环境运行，如果数据库中已经有数据，要先清空
        IastProjectTemplate.objects.all().delete()
        IastStrategyUser.objects.all().delete()
        User.objects.all().delete()
        UserDepartment.objects.all().delete()

        # 创建用户
        UserRole.objects.get_or_create(level=UserRole.LEVEL_NORMAL,
                                       defaults={"name": "项目用户", "status": 1, "permission": {}})
        UserRole.objects.get_or_create(level=UserRole.LEVEL_TENANT,
                                       defaults={"name": "租户管理员", "status": 1, "permission": {}})
        role, _ = UserRole.objects.get_or_create(level=UserRole.LEVEL_SUPER,
                                                       defaults={"name": "超级管理员", "status": 1, "permission": {}})
        # tenant, _ = UserTenant.objects.get_or_create(name='公司')
        # kwargs = {'name': '全部门', 'parent': None, 'tenant': tenant}
        # depart, created = UserDepartment.objects.get_or_create(name='默认部门', tenant=tenant, defaults=kwargs)
        kwargs = {'role': role,
                  'phone': '13912345678',
                  'default_language': 'zh',}
        admin = User.objects.create_superuser(username='admin', password='admin', email='admin@e-sscard.com', **kwargs)

        vul_level_list = [
            {'name': 'high', 'name_value': '高危', 'name_type': '高危漏洞', 'name_type_en': 'HIGH', 'name_value_en': 'HIGH'},
            {'name': 'medium', 'name_value': '中危', 'name_type': '中危漏洞', 'name_type_en': 'MEDIUM', 'name_value_en': 'MEDIUM'},
            {'name': 'low', 'name_value': '低危', 'name_type': '低危漏洞', 'name_type_en': 'LOW', 'name_value_en': 'LOW'},
            {'name': 'info', 'name_value': '无风险', 'name_type': '无风险', 'name_type_en': 'INFO', 'name_value_en': 'INFO'},
            {'name': 'note', 'name_value': '提示', 'name_type': '提示信息', 'name_type_en': 'NOTE', 'name_value_en': 'NOTE'}
        ]
        for level in vul_level_list:
            IastVulLevel.objects.get_or_create(name=level["name"], defaults=level)

        program_language_list = [{'name': 'Java'}, {'name': 'Python'}, {'name': 'PHP'}, {'name': 'Go'}]
        for language in program_language_list:
            IastProgramLanguage.objects.get_or_create(name=language["name"])

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
            IastDeployDesc.objects.get_or_create(middleware=deploy["middleware"], defaults=deploy)

        IastMessageType.objects.get_or_create(name="report")

        strategy, created = IastStrategyUser.objects.get_or_create(name="全部漏洞策略", defaults={
            'name': '全部漏洞策略',
            'user': admin,
            'status': True,
            'content': '2,8,9,14,15,17,18,19,20,23,24,25,26,28,30,33,37,22,34,1,10,11,12,13,16,21,27,29,31,32,3,4,5,6,7,35,36,38,41,45,44,43,40,39,42'})
        IastProjectTemplate.objects.get_or_create(template_name="全面扫描模板", defaults={
            'template_name': '全面扫描模板',
            'user': admin,
            'scan': strategy})

        profile_list = [
            {'key': 'enable_update', 'value': 'FALSE'},
            {'key': 'cpu_limit', 'value': '100'},
            {'key': 'vul_verify', 'value': '1'},
            {'key': 'auto_audit', 'value': '0'},
            {'key': 'circuit_break', 'value': '0'},
            {'key': 'data_clean', 'value': '{"clean_time": "00:00:00", "days_before": 7, "enable": true}'},
            {'key': 'dast_validation_settings', 'value': '{"strategy_id": [2, 8, 9, 14, 15, 17, 18, 19, 20, 23, 24, 25, 26, 28, 30, 33, 37, 22, 34, 1, 10, 11, 12, 13, 16, 21, 27, 29, 31, 32, 4, 5, 6, 7, 36, 38, 41, 45, 42, 3, 35, 39, 40, 43, 44], "validation_status": true}'}
        ]
        for profile in profile_list:
            IastProfile.objects.get_or_create(key=profile['key'], defaults=profile)

        vul_status_list = [
            {"name": "待验证", "name_zh": "待验证", "name_en": "Pending"},
            {"name": "验证中", "name_zh": "验证中", "name_en": "Verifying"},
            {"name": "已确认", "name_zh": "已确认", "name_en": "Confirmed"},
            {"name": "已忽略", "name_zh": "已忽略", "name_en": "Ignore"},
            {"name": "已处理", "name_zh": "已处理", "name_en": "Solved"},
            {"name": "已修复", "name_zh": "已修复", "name_en": "Fixed"},
            {"name": "验证失败", "name_zh": "验证失败", "name_en": "Verify failed"},
        ]
        for vul_status in vul_status_list:
            IastVulnerabilityStatus.objects.get_or_create(name=vul_status["name"], defaults=vul_status)