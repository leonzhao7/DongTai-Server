#!/usr/bin/env python
# -*- coding:utf-8 -*-
# author:owefsad
# software: PyCharm
# project: lingzhi-webapi
import datetime

from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from dongtai_common.endpoint import UserEndPoint, R
from dongtai_common.models.access_log import AccessLog


class LogClear(UserEndPoint):
    name = 'api-v1-log-clear'
    description = _('Log clear')

    def get(self, request):
        user = request.user
        now = timezone.now()

        if user.is_system_admin():
            AccessLog.objects.filter(start_time__lt=now).delete()
        elif user.is_talent_admin():
            users = self.get_auth_users(user)
            AccessLog.objects.filter(start_time__lt=now, user__in=users).delete()
        else:
            return R.failure(status=203, msg=_('no permission'))
        return R.success()