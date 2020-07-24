import json
from decimal import Decimal
from django.http import JsonResponse
from django.utils import timezone
from django.views import View
from django_redis import get_redis_connection
from meiduo_mall.utils.view import LoginRequireMixin
from orders.models import OrderInfo, OrderGoods
from goods.models import SKU
from users.models import Address
from django.db import transaction


class OrderSettlementView(LoginRequireMixin, View):
    def get(self, request):
        # 从mysql中Address获取该用户所有未删除的地址===>addresses
        try:
            addresses = Address.objects.filter(user=request.user,
                                               is_deleted=False)
        except Exception as ret:
            return JsonResponse({
                'code': 400,
                'errmsg': '地址查询错误'
            })


        # 遍历所有的地址===>address===>{}===>[]
        address_list = []
        for address in addresses:
            address_list.append({
                'id': address.id,
                'province': address.province.name,
                'city': address.city.name,
                'district': address.district.name,
                'place': address.place,
                'mobile': address.mobile,
                'receiver': address.receiver
            })

        # 连接redis获取连接对象
        redis_conn = get_redis_connection('carts')

        # 从redis的hash中获取count
        dict_item = redis_conn.hgetall('carts_%s' % request.user.id)

        # 从set中获取 sku_id(选中的商品的id)
        selected_item = redis_conn.smembers('selected_%s' % request.user.id)

        # 把hash中的count和set中的sku_id整理到{sku_id:count}
        dict = {}
        for sku_id in selected_item:
            dict[int(sku_id)] = int(dict_item[sku_id])

        # 把dict 中的sku_id都变成sku
        sku_ids = dict.keys()

        try:
            skus = SKU.objects.filter(id__in=sku_ids)
        except Exception as ret:
            return JsonResponse({
                'code': 400,
                'errmsg': '查询数据库错误'
            })

        # 获取所有的商品,遍历skus==>sku===>{}===>[]
        sku_list = []
        for sku in skus:
            sku_list.append({
                'id': sku.id,
                'name': sku.name,
                'default_image_url': sku.default_image_url,
                'count': dict[sku.id],
                'price': sku.price
            })

        # 定义一个运费的变量
        freight = Decimal('10.00')

        # 整理数据
        context = {
            'addresses': address_list,
            'skus': sku_list,
            'freight': freight
        }

        # 返回

        return JsonResponse({
            'code': 0,
            'errmsg': 'ok',
            'context': context
        })


class SaveOrdersView(View):
    def post(self, request):
        """保存订单信息"""

        # 接受参数json(address_id+pay_methed)
        json_dict = json.loads(request.body)
        address_id = json_dict.get('address_id')
        pay_method = json_dict.get('pay_method')

        # 总体检验
        if not all([address_id, pay_method]):
            return JsonResponse({
                'code': 400,
                'errmsg': '参数不完整'
            })

        # 单个检验
        try:
            address = Address.objects.get(id=address_id)
        except Exception as ret:
            return JsonResponse({
                'code': 400,
                'errmsg': 'address_id有误'
            })

        if pay_method not in [1, 2]:
            return JsonResponse({
                'code': 400,
                'errmsg': 'pay_method有误'
            })

        # 创建一个order_id,年月日时分秒
        order_id = timezone.localtime().strftime('%Y%m%d%H%M%S') + ('%09d' % request.user.id)

        with transaction.atomic():

            save_id = transaction.savepoint()
            # OrderInfo中存储订单的基本信息
            order = OrderInfo.objects.create(
                order_id=order_id,
                user=request.user,
                address=address,
                total_count=0,
                total_amount=Decimal('0'),
                freight=Decimal('10.00'),
                pay_method=pay_method,
                status=1 if pay_method == 2 else 2
            )

            # 连接redis,获取连接对象
            redis_conn = get_redis_connection('carts')

            # 从redis的hash中取出count
            dict_item = redis_conn.hgetall('carts_%s' % request.user.id)

            # 从redis的set中获取sku_id
            selected_item = redis_conn.smembers('selected_%s' % request.user.id)

            # 整理:dict={sku_id:count}
            dict = {}
            for sku_id in selected_item:
                dict[int(sku_id)] = int(dict_item[sku_id])

            # 从dict中共 获取所有的sku_ids
            sku_ids = dict.keys()

            # 遍历sku_ids===>sku_id
            for sku_id in sku_ids:
                while True:
                    # 把sku_id 变为sku
                    sku = SKU.objects.get(id=sku_id)

                    origin_stock = sku.stock
                    origin_sales = sku.sales

                    # 判断该商品的stock与销售数量的关系, 如果销售数量 > stock, 返回
                    if sku.stock < dict[sku_id]:
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({
                            'code': 400,
                            'errmsg': '库存不足'
                        })

                    # # 更改sku的销量和库存===>保存
                    # sku.stock -= dict[sku_id]
                    # sku.sales += dict[sku_id]
                    # sku.save()

                    new_stock = origin_stock - dict[sku_id]
                    new_sales = origin_sales + dict[sku_id]

                    result = SKU.objects.filter(id=sku_id,
                                                stock=origin_stock
                                                ).update(stock=new_stock, sales=new_sales)

                    if result == 0:
                        continue

                    # 更改spu的销量 ===> 保存
                    sku.goods.sales += dict[sku_id]
                    sku.goods.save()

                    # 把sku相关数据保存到订单商品表中OrderGoods
                    OrderGoods.objects.create(
                        order=order,
                        sku=sku,
                        count=dict[sku_id],
                        price=sku.price,
                    )

                    order.total_count += dict[sku_id]
                    order.total_amount += sku.price * dict[sku_id]

                    break

            order.total_amount += order.freight
            order.save()
            transaction.savepoint_commit(save_id)

        redis_conn.hdel('carts_%s' % request.user.id, *selected_item)
        redis_conn.srem('selected_%s' % request.user.id, *selected_item)

        return JsonResponse({
            'code': 0,
            'errmsg': 'ok',
            'order_id': order_id
        })
