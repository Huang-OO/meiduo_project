import base64
import pickle

from django_redis import get_redis_connection


def merge_carts_cookie_to_redis(request, response):
    """把cookie中的内容合并到reids(hash+set)中"""
    # 从cookie中获取数据
    cookie_cart = request.COOKIES.get('carts')

    # 判断获取的数据是否存在,如果不存在,返回
    if not cookie_cart:
        return response

    # 如果存在,解密===>dict
    cart_dict = pickle.loads(base64.b64decode(cookie_cart))

    # 定义三个容器,把dict中获取的不同数据,分别存放到不同的容器中
    new_dict = {}
    new_add = []
    new_remove = []

    # 遍历dict,获取key&value
    for k, v in cart_dict.items():
        # 把sku_id&count===>{}
        new_dict[int(k)] = int(v['count'])

        # 判断selected对应的值, 如果True,把sku_id暂时存放到add[]
        if k['selected']:
            new_add.append(k)
        else:
            # 如果selected对应的值是False, 将sku_id暂时存放到remove[]
            new_remove.append(k)

    # 连接redis, 获取连接对象
    redis_conn = get_redis_connection('carts')

    # 把dict中的值, 写入到hash中
    redis_conn.hset('carts_%s' % request.user.id, new_dict)

    # 判断add[]中是否优质, 如果有值, 我们往set中增加id
    if new_add:
        redis_conn.sadd('selected_%s' % request.user.id, *new_add)

    # 判断remove[]中是否有值, 如果有值, 我们从set中删除id
    if new_remove:
        redis_conn.srem('selected_%s' % request.user.id, *new_remove)

    # 删除cookie中的购物车记录
    response.delete_cookie('carts')

    return response
