#!/usr/bin/env python
# datetime: 2021/7/12 下午5:49
import string
import uuid

default_app_config = "dongtai_common.apps.DongTaiConfig"

def generate_token() -> string:
    return uuid.uuid4().hex