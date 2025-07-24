######################################################################
# @author      : bidaya0 (bidaya0@$HOSTNAME)
# @file        : health_oss
# @created     : Thursday Aug 26, 2021 10:37:17 CST
#
# @description :
######################################################################

import logging

from drf_spectacular.utils import extend_schema

from dongtai_common.endpoint import R, UserEndPoint

logger = logging.getLogger("dongtai.openapi")


class OSSHealthView(UserEndPoint):
    @extend_schema(
        description="Check OSS Health",
        responses=R,
        methods=["GET"],
        summary="检查 OSS 健康",
        tags=["OSS"],
    )
    def get(self, request):
        data = {"oss": {"status": 1}}
        return R.success(data=data)
