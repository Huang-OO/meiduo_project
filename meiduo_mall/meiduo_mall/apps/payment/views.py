import os

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from alipay import AliPay
# Create your views here.
from django.views import View

from orders.models import OrderInfo
from payment.models import Payment


class PaymentView(View):
    def get(self, request, order_id):
        """返回支付宝支付地址的接口"""
        # 在OrderInfo表中验证order_id是否为真
        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                  user=request.user,
                                  status=1)
        except Exception as ret:
            return JsonResponse({
                'code': 400,
                'errmsg': '订单错误'
            })

        # 调用python-alipay-sdk工具类, 创建一个对象
        alipay = AliPay(
            appid=settings.ALIPAY_APPID,
            app_notify_url=None,  # 默认回调url
            app_private_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "keys/app_private_key.pem"),
            alipay_public_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "keys/alipay_public_key.pem"),
            sign_type="RSA2",
            debug=settings.ALIPAY_DEBUG
        )

        # 调用对象的方法 ===> 拼接好的字符串(参数)
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,
            total_amount=str(order.total_amount),
            subject="美多商城%s" % order_id,
            return_url=settings.ALIPAY_RETURN_URL,
        )

        # 把支付宝的网关(url) + 字符串 ===> 完整地址
        alipay_url = settings.ALIPAY_URL + "?" + order_string
        return JsonResponse({'code': 1,
                             'errmsg': 'OK',
                             'alipay_url': alipay_url})


class PaymentStatusView(View):
    """保存订单支付结果"""

    def put(self, request):
        # 获取前端传入的请求参数
        query_dict = request.GET
        data = query_dict.dict()
        # 获取并从请求参数中剔除signature
        signature = data.pop('sign')

        # 创建支付宝支付对象
        alipay = AliPay(
            appid=settings.ALIPAY_APPID,
            app_notify_url=None,
            app_private_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "keys/app_private_key.pem"),
            alipay_public_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "keys/alipay_public_key.pem"),
            sign_type="RSA2",
            debug=settings.ALIPAY_DEBUG
        )
        # 校验这个重定向是否是alipay重定向过来的
        success = alipay.verify(data, signature)
        if success:
            # 读取order_id
            order_id = data.get('out_trade_no')
            # 读取支付宝流水号
            trade_id = data.get('trade_no')
            # 保存Payment模型类数据
            Payment.objects.create(
                order_id=order_id,
                trade_id=trade_id
            )

            # 修改订单状态为待评价
            OrderInfo.objects.filter(order_id=order_id,
                  status=OrderInfo.ORDER_STATUS_ENUM['UNPAID']).update(
                  status=OrderInfo.ORDER_STATUS_ENUM["UNCOMMENT"])

            return JsonResponse({'code':0,
                                 'errmsg':'ok',
                                 'trade_id':trade_id})
        else:
            # 订单支付失败，重定向到我的订单
            return JsonResponse({'code':400,
                                 'errmsg':'非法请求'})
