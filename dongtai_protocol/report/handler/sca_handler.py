#!/usr/bin/env python
# datetime:2020/10/23 11:55
import logging


from dongtai_common.utils import const
from dongtai_protocol.report.handler.report_handler_interface import IReportHandler
from dongtai_protocol.report.report_handler_factory import ReportHandler

logger = logging.getLogger("dongtai.openapi")


@ReportHandler.register(const.REPORT_SCA)
class ScaHandler(IReportHandler):
    def parse(self):
        pass


    @staticmethod
    def send_to_engine(
        agent_id,
        package_path,
        package_signature,
        package_name,
        package_algorithm,
        package_version,
    ):
        pass

    def save(self):
        pass


@ReportHandler.register(const.REPORT_SCA + 1)
class ScaBulkHandler(IReportHandler):
    def parse(self):
        pass

    def save(self):
        pass
