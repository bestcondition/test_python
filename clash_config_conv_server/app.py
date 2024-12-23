import dataclasses
from collections import OrderedDict
import re

from flask import Flask, request

app = Flask(__name__)


@dataclasses.dataclass
class ProxyName:
    # 倍率
    rate: float
    # 地区
    area: str
    # 全名
    name: str

    def get_sv(self):
        return self.area, -self.rate, self.name

    def __lt__(self, other):
        return self.get_sv() < other.get_sv()


area_content = {
    # 加编号用于排序
    '02台': ['台'],
    '03日': ['日'],
    '04韩': ['韩'],
    '05新': ['新'],
    '06美': ['美'],
    '07德': ['德'],
    '08法': ['法'],
    # 港放下面，放上面有可能误识别
    '01港': ['港'],
    '09其他': [''],
}


def name_to_area(name: str) -> str:
    for area, names in area_content.items():
        if any(n in name for n in names):
            return area
    return '其他'


def name_to_rate(name: str) -> float:
    """江苏联通转日本TE4[M][Trojan][倍率:0.8]"""
    p = re.search(r'倍率:([\d.]+)', name).group(1)
    return float(p)


def paser_proxy_name(name: str) -> ProxyName:
    return ProxyName(
        name=name,
        area=name_to_area(name),
        rate=name_to_rate(name),
    )


def convert(
        content: dict,
        new_group_name: list[str] = None,
        new_rules: list[str] = None
) -> dict:
    if new_group_name is None:
        new_group_name = []
    if new_rules is None:
        new_rules = []
    # 参数校验
    if not all(k in content for k in 'proxies proxy-groups rules'.split()):
        return content
    proxies = content['proxies']
    # 按照指定名称属性排序
    proxies.sort(key=lambda p: paser_proxy_name(p['name']))
    # 区域到代理名称结构体的映射
    area_to_pns = OrderedDict()
    for p in proxies:
        pn = paser_proxy_name(p['name'])
        if pn.area not in area_to_pns:
            area_to_pns[pn.area] = []
        area_to_pns[pn.area].append(pn)
    proxy_groups = content['proxy-groups']
    # 所有的区域
    areas = list(area_to_pns.keys())
    for pg in proxy_groups:
        # 现有的group都可以选新加的area group
        pg['proxies'] = pg['proxies'] + areas
    area_groups = []
    # 为每个area创建一个proxy-group
    for area, pns in area_to_pns.items():
        # 可选为该区域的所有proxy
        names = [p.name for p in pns]
        j = {
            "name": area,
            "type": "url-test",  # 代理组类型为，通过延迟测速，自动选择
            "proxies": names,
            "url": "http://www.gstatic.com/generate_204",
            "interval": 300,
            "tolerance": 100
        }
        area_groups.append(j)
    proxy_groups += area_groups
    # 目前来说所有的代理组的名字，老的 和 区域 的都在
    now_gn = [
        pg['name']
        for pg in proxy_groups
    ]
    new_groups = []
    # 添加新的代理组
    for gn in new_group_name:
        new_groups.append({
            "name": gn,
            "type": "select",  # 模式为选择，选项为所有代理组
            "proxies": now_gn,
        })
    proxy_groups += new_groups
    rules = content['rules']
    # 新规则放前面
    rules = new_rules + rules
    content['rules'] = rules
    # 注意key别错了
    content['proxy-groups'] = proxy_groups
    content['proxies'] = proxies
    return content


@app.route('/', methods=['GET', 'POST'])
def index():
    x = convert(
        content=request.json['content'],
        # openai 的规则，来源：https://github.com/blackmatrix7/ios_rule_script/blob/master/rule/Clash/OpenAI/OpenAI.list
        new_group_name=['OpenAI'],
        new_rules="""
DOMAIN,browser-intake-datadoghq.com,OpenAI
DOMAIN,chat.openai.com.cdn.cloudflare.net,OpenAI
DOMAIN,gemini.google.com,OpenAI
DOMAIN,openai-api.arkoselabs.com,OpenAI
DOMAIN,openaicom-api-bdcpf8c6d2e9atf6.z01.azurefd.net,OpenAI
DOMAIN,openaicomproductionae4b.blob.core.windows.net,OpenAI
DOMAIN,production-openaicom-storage.azureedge.net,OpenAI
DOMAIN,static.cloudflareinsights.com,OpenAI
DOMAIN-SUFFIX,ai.com,OpenAI
DOMAIN-SUFFIX,algolia.net,OpenAI
DOMAIN-SUFFIX,api.statsig.com,OpenAI
DOMAIN-SUFFIX,auth0.com,OpenAI
DOMAIN-SUFFIX,chatgpt.com,OpenAI
DOMAIN-SUFFIX,chatgpt.livekit.cloud,OpenAI
DOMAIN-SUFFIX,client-api.arkoselabs.com,OpenAI
DOMAIN-SUFFIX,events.statsigapi.net,OpenAI
DOMAIN-SUFFIX,featuregates.org,OpenAI
DOMAIN-SUFFIX,host.livekit.cloud,OpenAI
DOMAIN-SUFFIX,identrust.com,OpenAI
DOMAIN-SUFFIX,intercom.io,OpenAI
DOMAIN-SUFFIX,intercomcdn.com,OpenAI
DOMAIN-SUFFIX,launchdarkly.com,OpenAI
DOMAIN-SUFFIX,oaistatic.com,OpenAI
DOMAIN-SUFFIX,oaiusercontent.com,OpenAI
DOMAIN-SUFFIX,observeit.net,OpenAI
DOMAIN-SUFFIX,openai.com,OpenAI
DOMAIN-SUFFIX,openaiapi-site.azureedge.net,OpenAI
DOMAIN-SUFFIX,openaicom.imgix.net,OpenAI
DOMAIN-SUFFIX,segment.io,OpenAI
DOMAIN-SUFFIX,sentry.io,OpenAI
DOMAIN-SUFFIX,stripe.com,OpenAI
DOMAIN-SUFFIX,turn.livekit.cloud,OpenAI
DOMAIN-KEYWORD,openai,OpenAI
IP-CIDR,24.199.123.28/32,OpenAI,no-resolve
IP-CIDR,64.23.132.171/32,OpenAI,no-resolve
        """.strip().splitlines(),
    )
    return {
        "content": x
    }


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5555)
