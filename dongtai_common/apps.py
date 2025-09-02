import sys

from django.apps import AppConfig

from dongtai_common.common.utils import DongTaiAppConfigPatch
from dongtai_common.global_data import global_data


class DongTaiConfig(DongTaiAppConfigPatch, AppConfig):
    name = "dongtai_common"

    def ready(self):
        print(f"common ready le")
        if len(sys.argv) > 1 and sys.argv[1] in ("runserver", "runserver_plus"):
            global_data.load_data()