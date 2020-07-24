from django.shortcuts import render
from django.views import View
from meiduo_mall.libs.captcha.captcha import captcha
from django_redis import get_redis_connection
from django.http import HttpResponse, JsonResponse
from meiduo_mall.libs.yuntongxun.ccp_sms import CCP
from celery_tasks.sms.tasks import send_sms_code
import logging
import random
logger = logging.getLogger('django')

# Create your views here.


class VerificationsView(View):
    def get(self, request, uuid):
        """生成图形验证码并返回"""
        # 生成图片和值
        text, image = captcha.generate_captcha()

        # 连接redis，获取连接对象
        redis_conn = get_redis_connection("verify_code")

        # 把值保存到redis
        redis_conn.setex('img_%s' % uuid, 300, text)

        # 返回图片
        return HttpResponse(image, content_type='image/jpg')


class SMSCodeView(View):
    """短信验证码"""

    def get(self, request, mobile):

        redis_conn = get_redis_connection("verify_code")

        send_flag = redis_conn.get('send_flag_%s' % mobile)

        if send_flag:
            return JsonResponse({
                'code': 400,
                'errmsg': '发送请求过于频繁'
            })

        # 1、接收参数
        image_code_client = request.GET.get('image_code')
        uuid = request.GET.get('image_code_id')

        # 2、校验参数
        if not all([image_code_client, uuid]):
            return JsonResponse({
                'code': 400,
                'errmsg': '参数不完整'
            })

        # 3、创建连接到redis的对象
        # redis_conn = get_redis_connection("verify_code")

        # 4、提取图像验证码
        image_code_server = redis_conn.get('img_%s' % uuid)

        if image_code_server is None:
            return JsonResponse({
                'code': 400,
                'errmsg': '图形验证码过期'
            })

        # 5、删除图形验证码，避免恶意测试图形验证码
        try:
            redis_conn.delete('img_%s' % uuid)
        except Exception as ret:
            logger.error(ret)

        # 6、对比前后端的图形验证码，如果不相等，返回报错
        if image_code_client.lower() != image_code_server.decode().lower():
            return JsonResponse({
                'code': 400,
                'errmsg': '验证码输入有误'
            })

        # 7、生成短信验证码
        sms_code = '%06d' % random.randint(0, 999999)
        print(sms_code)

        # 8、在redis中保存短验证码

        # 创建管道对象
        pl = redis_conn.pipeline()
        pl.setex('sms_%s' % mobile,
                 300,
                 sms_code)
        pl.setex('send_flag_%s' % mobile,
                 60,
                 1)
        # 执行管道
        pl.execute()

        # 9、调用容联云发送短信验证码
        # CCP().send_template_sms(mobile, [sms_code, 5], 1)
        send_sms_code.delay(mobile, sms_code)
        # 10、返回json
        return JsonResponse({
            'code': 0,
            'errmsg': 'ok'
        })
