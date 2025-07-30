# 检测设置，item_id和对应的关键词列表, 关键词任意一个匹配即可触发推送
# item_id可以在网页端的URL中找到，例如：https://detail.damai.cn/item.htm?id=xxxxxxxxxxxx
TARGET_SETTINGS = {
    # 'item_id1': ['keyword1', 'keyword2', ...],
    # 'item_id2': ['keyword1', 'keyword2', ...]
}

MESSPUSHER_CONFIG = {
    'pushplus': {
        'token': 'your_pushplus_token_here'
    }
}

# 代理设置，如果不需要代理可以不用修改
PROXIES = [
    # 'http://proxy1:port',
    # 'http://user:password@proxy2:port',
]