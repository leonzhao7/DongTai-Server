from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from dongtai_common.models import User
from dongtai_common.utils.settings import get_managed


class MethodType(models.IntegerChoices):
    GET = 1, _("GET")
    ADD = 2, _("ADD")
    CHANGE = 3, _("CHANGE")
    DELETE = 4, _("DELETE")


class AccessLog(models.Model):
    id = models.BigAutoField(primary_key=True)
    start_time = models.DateTimeField(
        _("start time"),
        default=timezone.now,
        editable=False,
    )
    exec_time = models.FloatField(blank=True)
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, null=True, blank=True)
    client_ip = models.CharField(max_length=255)
    method = models.CharField(max_length=16)
    url = models.CharField(max_length=2048)
    user_agent = models.CharField(max_length=512, null=True, blank=True)
    status_code = models.IntegerField(default=0, blank=True)
    req_body_length = models.IntegerField(default=0, blank=True)
    reply_msg = models.CharField(max_length=1024, null=True, blank=True)

    class Meta:
        managed = get_managed()
        db_table = "access_log"
