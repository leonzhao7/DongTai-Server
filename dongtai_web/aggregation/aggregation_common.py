from dongtai_common.endpoint import UserEndPoint
from dongtai_common.models import User
from dongtai_common.models.agent import IastAgent
from dongtai_common.models.hook_type import HookType
from dongtai_common.models.vulnerablity import IastVulnerabilityModel
from dongtai_web.serializers.vul import VulSerializer

# str to int list
def turnIntListOfStr(type_str, field=""):
    try:
        type_list = type_str.split(",")
        # 安全校验,强制转int
        type_list = list(map(int, type_list))
        if field:
            type_int_list = list(map(str, type_list))
            type_int_str = ",".join(type_int_list)
            return f" and {field} in ({type_int_str}) "
    except Exception:
        return ""
    else:
        return type_list
