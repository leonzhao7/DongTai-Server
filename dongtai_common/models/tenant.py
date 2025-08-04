#!/usr/bin/env python
# datetime:2021/1/18 下午12:54
from typing import Any

from django.db import models
from django.utils.translation import gettext_lazy as _

from dongtai_common.utils.customfields import trans_char_field
from dongtai_common.utils.settings import get_managed
from dongtai_common.utils.db import get_timestamp


class Tenant(models.Model):
    name = models.CharField(
        unique=True,
        verbose_name=_("tenant"),
        max_length=255,
        blank=True,
        error_messages={
            "unique": _("A tenant with that tenant name already exists."),
        },
    )
    create_time = models.IntegerField(default=get_timestamp)
    update_time = models.IntegerField(default=get_timestamp)
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_(
            "Designates whether this user should be treated as active. Unselect this instead of deleting accounts."
        ),
    )

    class Meta:
        verbose_name = _("tenant")
        managed = get_managed()
        db_table = "auth_talent"

    def get_name(self):
        return self.name

    @trans_char_field("talent_name", {"zh": {"默认租户": "默认租户"}, "en": {"默认租户": "Default Tenant"}})
    def __getattribute__(self, name) -> Any:
        return super().__getattribute__(name)
