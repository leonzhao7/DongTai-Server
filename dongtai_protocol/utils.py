#!/usr/bin/env python
# datetime: 2021/6/1 上午9:53

# -*- coding: utf-8 -*-
import base64
import logging

logger = logging.getLogger("dongtai.openapi")

def base64_decode(raw: str) -> str:
    try:
        return base64.b64decode(raw).decode("utf-8").strip()
    except Exception as decode_error:
        logger.exception(f"base64 decode error, raw: {raw}\nreason: ", exc_info=decode_error)
        return ""

def build_request_header(req_method, raw_req_header, uri, query_params, http_protocol):
    decode_req_header = base64_decode(raw_req_header)
    return f"{req_method} {uri + ('?' + query_params if query_params else '')} {http_protocol}\n{decode_req_header}"
