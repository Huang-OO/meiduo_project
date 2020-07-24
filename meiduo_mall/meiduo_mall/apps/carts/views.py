import base64
import json
import pickle

from django.http import JsonResponse
from django.shortcuts import render

# Create your views here.
from django.views import View
from django_redis import get_redis_connection

from goods.models import SKU


class CartsView(View):
    def post(self, request):
        # 接受参数
        json_dict = json.loads(request.body)
        sku_id = json_dict.get('sku_id')
        count = json_dict.get('count')
        selected = json_dict.get('selected', True)

        # 检验参数
        if not all([sku_id, count]):
            return JsonResponse({
                'code': 400,
                'errmsg': '参数不完整'
            })


        try:
            SKU.objects.get(id=sku_id)
        except Exception as ret:
            return JsonResponse({
                'code': 400,
                'errmsg': '增加的商品不存在'
            })

        try:
            count = int(count)

            if count <= 0:
                return JsonResponse({
                    'code': 400,
                    'errmsg': 'count有误'
                })

        except Exception as ret:
            return JsonResponse({
                'code': 400,
                'errmsg': 'count输入有误'
            })

        # 判断用户是否登录
        # 如果用户登录
        if request.user.is_authenticated:
            user = request.user
            # 链接redis获取连接对象
            redis_conn = get_redis_connection('carts')
            pl = redis_conn.pipeline()
            # 往hash中写入数据
            pl.hincrby('carts_%s' % user.id, sku_id, count)

            # 往set中写入数据(如果该商品的selected为true,增加)
            if selected:
                pl.sadd('selected_%s' % user.id, sku_id)

            pl.execute()
            # 返回json
            return JsonResponse({
                'code': 0,
                'errmsg': 'ok'
            })


        else:
            # 未登录用户
            # 先获取cookie中的数据(加过密的数据)
            carts = request.COOKIES.get('carts')

            # 判断cookie是否存在
            if carts:
                # 如果存在,解密 ===> dict
                carts_dict = pickle.loads(base64.b64decode(carts))
            else:
                # 如果不存在, 创建一个新的dict
                carts_dict = {}

            # 判断前端传入的sku_id是否在dict中
            if sku_id in carts_dict:
                # 如果在, 该商品的个数累加
                count += carts_dict[sku_id]['count']

            # 把sku_id, count(累加过的), selected保存到dict中
            carts_dict[sku_id] = {
                'count': count,
                'selected': selected
            }

            # 把dict加密
            carts_dict = base64.b64encode(pickle.dumps(carts_dict))

            # 把加密后的数据写入到cookie中
            response = JsonResponse({
                'code': 0,
                'errmsg': 'ok'
            })

            response.set_cookie('carts',
                                carts_dict,
                                max_age=3600*24*14)

            # 返回json数据
            return response

    def get(self, request):
        # 判断用户是否登录
        if request.user.is_authenticated:
            # 用户登录
            user_id = request.user.id
            # 连接redis,获取连接对象
            redis_conn = get_redis_connection('carts')

            # 从redis中获取数据
            item_dict = redis_conn.hgetall('carts_%s' % user_id)
            selected_item = redis_conn.smembers('selected_%s' % user_id)
            # 构造一个新的dict, 把hash中的sku_id&count以及set中的状态保存进去
            cart_dict = {}
            for sku_id, count in item_dict.items():
                cart_dict[int(sku_id)] = {
                    'count': int(count),
                    'selected': sku_id in selected_item
                }
        else:
            # 用户未登录
            # 从cookie中获取数据
            cart_dict = request.COOKIES.get('carts')
            # 判断该数据是否存在
            if cart_dict:
                # 如果存在解密
                pickle.loads(base64.b64decode(cart_dict))
            else:
                # 如果不存在新建一个dict
                cart_dict = {}

        # 从字典中取出所有的sku_ids
        sku_ids = cart_dict.keys()

        # 把sku_ids ===> skus
        try:
            skus = SKU.objects.filter(id__in=sku_ids)
        except Exception as ret:
            return JsonResponse({
                'code': 400,
                'errmsg': '获取数据有误'
            })

        # 遍历skus ===>sku ===>{}===>[]
        sku_list = list()
        for sku in skus:
            sku_list.append({
                'id': sku.id,
                'selected': cart_dict[sku.id]['selected'],
                'default_image_url': sku.default_image_url,
                'name': sku.name,
                'price': sku.price,
                'count': cart_dict[sku.id]['count'],
                'amount': sku.price * cart_dict[sku.id]['count'],

            })

        return JsonResponse({
            'code': 0,
            'errmsg': 'ok',
            'cart_skus': sku_list
        })

    def put(self, request):
        # 接受参数
        json_dict = json.loads(request.body)
        sku_id = json_dict.get('sku_id')
        count = json_dict.get('count')
        selected = json_dict.get('selected', True)

        # 检验参数
        if not all([sku_id, count]):
            return JsonResponse({
                'code': 400,
                'errmsg': '参数不完整'
            })

        try:
            sku = SKU.objects.get(id=sku_id)
        except Exception as ret:
            return JsonResponse({
                'code': 400,
                'errmsg': '增加的商品不存在'
            })

        try:
            count = int(count)

            if count <= 0:
                return JsonResponse({
                    'code': 400,
                    'errmsg': 'count有误'
                })
        except Exception as ret:
            return JsonResponse({
                'code': 400,
                'errmsg': '增加的商品不存在'
            })

        if selected:
            if not isinstance(selected, bool):
                return JsonResponse({
                    'code': 400,
                    'errmsg': 'selected只能是bool值'
                })

        # 判断用户是否登录
        if request.user.is_authenticated:
            # 如果登录
            user_id = request.user.id
            # 连接redis获取连接对象
            redis_conn = get_redis_connection('carts')
            pl = redis_conn.pipeline()

            # 把数据写入hash
            pl.hset('carts_%s' % user_id, sku_id, count)

            # 根据selected,如果为true,把数据写入set, 如果为false,从set中移除
            if selected:
                pl.sadd('selected_%s' % user_id, sku_id)
            else:
                pl.srem('selected_%s' % user_id, sku_id)
            pl.execute()
            # 拼接参数返回
            return JsonResponse({
                'code': 0,
                'errmsg': 'ok',
                'cart_sku': {
                    'id': sku_id,
                    'count': count,
                    'selected': selected,
                    'name': sku.name,
                    'default_image_url': sku.default_image_url,
                    'price': sku.price,
                    'amount': sku.price * count,

                }

            })
        else:
            # 未登录用户
            # 先获取cookie中的数据(加过密的数据)
            carts = request.COOKIES.get('carts')

            # 判断cookie是否存在
            if carts:
                # 如果存在,解密 ===> dict
                carts_dict = pickle.loads(base64.b64decode(carts))
            else:
                # 如果不存在, 创建一个新的dict
                carts_dict = {}
            carts_dict[sku_id] = {
                'count': int(count),
                'selected': selected
            }

            # 把dict加密
            carts_dict = base64.b64encode(pickle.dumps(carts_dict)).decode()

            cart_sku = {
                'id': sku_id,
                'count': int(count),
                'selected': selected
            }
            # 把加密后的数据写入到cookie中
            response = JsonResponse({
                'code': 0,
                'errmsg': 'ok',
                'cart_sku': cart_sku
            })

            response.set_cookie('carts',
                                carts_dict,
                                max_age=3600 * 24 * 14)

            # 返回json数据
            return response

    def delete(self, request):
        # 接受参数
        json_dict = json.loads(request.body)
        sku_id = json_dict.get('sku_id')

        # 检验参数
        try:
            sku = SKU.objects.get(id=sku_id)
        except Exception as ret:
            return JsonResponse({
                'code': 400,
                'errmsg': '增加的商品不存在'
            })
        # 判断用户是否登录
        if request.user.is_authenticated:
            # 如果登录
            # 连接redis 获取连接对象
            user_id = request.user.id
            redis_conn = get_redis_connection('carts')
            # 从hash中删除该id对应的数据
            redis_conn.hdel('carts_%s' % user_id, sku_id)
            # 从set中删除该id对应的数据
            redis_conn.srem('selected_%s' % user_id, sku_id)
            return JsonResponse({
                'code': 0,
                'errmsg': 'ok'
            })
        else:
            # 如果未登录
            # 从cookie中获取数据
            carts = request.COOKIES.get('carts')
            # 判断该数据是否存在
            if carts:
                # 如果存在,解密 ===> dict
                carts_dict = pickle.loads(base64.b64decode(carts))
            else:
                # 如果不存在, 创建一个新的dict
                carts_dict = {}

            response = JsonResponse({
                'code': 0,
                'errmsg': 'ok'
            })
            if sku_id in carts_dict.keys():
                # 判断id是否在字典中,如果在,删除该行数据
                del carts_dict[sku_id]

                # 把剩下的字典加密
                carts_dict = base64.b64encode(pickle.dumps(carts_dict)).decode()

                # 把加过密的数据写入cookie
                response.set_cookie('carts',
                                    carts_dict,
                                    max_age=3600 * 24 * 14)

            return response


class SelectAllView(View):
    def put(self, request):
        # 接受参数
        json_dict = json.loads(request.body)
        selected = json_dict.get('selected')

        if not isinstance(selected, bool):
            return JsonResponse({
                'code': 400,
                'errmsg': '参数有误'
            })

        # 判断用户是否登录
        if request.user.is_authenticated:
            # 如果登录
            # 连接redis 获取连接对象
            user_id = request.user.id
            redis_conn = get_redis_connection('carts')
            # 从hash中删除该id对应的数据
            item_dict = redis_conn.hgetall('carts_%s' % user_id)
            sku_ids = item_dict.keys()
            # 从set中删除该id对应的数据
            if selected:
                redis_conn.sadd('selected_%s' % user_id, *sku_ids)
            else:
                redis_conn.srem('selected_%s' % user_id, *sku_ids)
            return JsonResponse({
                'code': 0,
                'errmsg': 'ok'
            })
        else:
            # 如果未登录
            # 从cookie中获取数据
            carts = request.COOKIES.get('carts')

            response = JsonResponse({
                'code': 0,
                'errmsg': 'ok'
            })
            # 判断该数据是否存在
            if carts:
                # 如果存在,解密 ===> dict
                carts_dict = pickle.loads(base64.b64decode(carts))

                for sku_id in carts_dict.keys():
                    carts_dict[sku_id]['selected'] = selected
                cart_data = base64.b64encode(pickle.dumps(carts_dict)).decode()

                response.set_cookie('carts', cart_data)
            return response


class CartsSimpleView(View):
    def get(self, request):
        # 判断用户是否登录
        if request.user.is_authenticated:
            # 用户登录
            user_id = request.user.id
            # 连接redis,获取连接对象
            redis_conn = get_redis_connection('carts')

            # 从redis中获取数据
            item_dict = redis_conn.hgetall('carts_%s' % user_id)
            selected_item = redis_conn.smembers('selected_%s' % user_id)
            # 构造一个新的dict, 把hash中的sku_id&count以及set中的状态保存进去
            cart_dict = {}
            for sku_id, count in item_dict.items():
                cart_dict[int(sku_id)] = {
                    'count': int(count),
                    'selected': sku_id in selected_item
                }
        else:
            # 用户未登录
            # 从cookie中获取数据
            cart_dict = request.COOKIES.get('carts')
            # 判断该数据是否存在
            if cart_dict:
                # 如果存在解密
                pickle.loads(base64.b64decode(cart_dict))
            else:
                # 如果不存在新建一个dict
                cart_dict = {}

        # 从字典中取出所有的sku_ids
        sku_ids = cart_dict.keys()

        # 把sku_ids ===> skus
        try:
            skus = SKU.objects.filter(id__in=sku_ids)
        except Exception as ret:
            return JsonResponse({
                'code': 400,
                'errmsg': '获取数据有误'
            })

        # 遍历skus ===>sku ===>{}===>[]
        sku_list = list()
        for sku in skus:
            sku_list.append({
                'id': sku.id,
                'selected': cart_dict[sku.id]['selected'],
                'default_image_url': sku.default_image_url,
                'name': sku.name,
                'price': sku.price,
                'count': cart_dict[sku.id]['count'],
                'amount': sku.price * cart_dict[sku.id]['count'],

            })

        return JsonResponse({
            'code': 0,
            'errmsg': 'ok',
            'cart_skus': sku_list
        })
