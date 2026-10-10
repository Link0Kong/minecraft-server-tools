import os
import json
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest

AK = os.environ["ALIYUN_AK_ID"]
SK = os.environ["ALIYUN_AK_SECRET"]
client = AcsClient(AK, SK, "cn-hangzhou")

req = CommonRequest()
req.set_accept_format("json")
req.set_domain("ecs.aliyuncs.com")
req.set_method("POST")
req.set_version("2014-05-26")
req.set_action_name("DescribeInstances")
req.add_query_param("RegionId", "cn-hangzhou")
req.add_query_param("PageSize", "50")

resp = client.do_action_with_exception(req)
data = json.loads(resp)
for inst in data.get("Instances", {}).get("Instance", []):
    print("ID       :", inst.get("InstanceId"))
    print("Name     :", inst.get("InstanceName"))
    print("Status   :", inst.get("Status"))
    print("PublicIP :", inst.get("PublicIpAddress", {}).get("IpAddress"))
    print("EIP      :", inst.get("EipAddress", {}).get("IpAddress"))
    print("Charge   :", inst.get("InstanceChargeType"))
    print("Type     :", inst.get("InstanceType"))
    print("-" * 40)
