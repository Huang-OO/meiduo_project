from QQLoginTool.QQtool import OAuthQQ
from django.contrib.auth import login
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from django.conf import settings

from carts.utils import merge_carts_cookie_to_redis
from oauth.models import OAuthQQUser
from users.models import User
from .utils import generate_access_token, check_access_token
import json, re
from django_redis import get_redis_connection

# Create your views here.


class QQFirstView(View):

    def get(self, request):
        """qq登录的第一个接口， 返回qq登录的地址"""

        # 接受参数
        next = request.GET.get('next')

        # 根据QQLoginTool工具类中的类，生成对象
        oauth = OAuthQQ(client_id=settings.QQ_CLIENT_ID,
                        client_secret=settings.QQ_CLIENT_SECRET,
                        redirect_uri=settings.QQ_REDIRECT_URI,
                        state=next)

        # 调用对象的get_qq_url()方法，获取对应的登录地址
        url = oauth.get_qq_url()

        # 拼接json参数，返回
        return JsonResponse({
            'code': 0,
            'errmsg': 'ok',
            'login_url': url
        })


class QQSecondView(View):

    def get(self, request):
        """根据code获取openid，根据openid查看是否登录成功"""
        # 接受参数
        code = request.GET.get('code')

        # 检验参数
        if not code:
            return JsonResponse({
                'code': 400,
                'errmsg': '确实参数'
            })

        # 创建QQLoginTool工具类的对象
        oauth = OAuthQQ(client_id=settings.QQ_CLIENT_ID,
                        client_secret=settings.QQ_CLIENT_SECRET,
                        redirect_uri=settings.QQ_REDIRECT_URI,
                        state=next)
        try:
            # 调用对象的方法，根据code获取access_token
            access_token = oauth.get_access_token(code)

            # 根据access_token获取openid
            openid = oauth.get_open_id(access_token)
        except Exception as ret:
            return ({
                'code': 400,
                'errmsg': '发送请求失败'
            })

        try:
            # 根据openid去qq的表中查询，查看是否有记录
            oauth_qq = OAuthQQUser.objects.get(openid=openid)
        except Exception as ret:
            # 如果没有记录，检验失败openid===》access_token
            # 自定义一个函数，把openid加密为：access_token
            # 返回json字符串（access_token）
            access_token = generate_access_token(openid)
            return JsonResponse({
                'code': 300,
                'errmsg': 'ok',
                'access_token': access_token
            })
        else:
            # 如果有记录，说明登录成功
            # 实现状态保持
            user = oauth_qq.user
            login(request, user)

            # 往cookie中写入username
            response = JsonResponse({
                'code': 0,
                'errmsg': 'ok'
            })

            response.set_cookie('username',
                                user.username,
                                max_age=3600*24*14)

            response = merge_carts_cookie_to_redis(request, response)

            # 返回响应
            return response

    def post(self, request):
        # 接收参数json
        dict = json.loads(request.body.decode())

        mobile = dict.get('mobile')
        password = dict.get('password')
        sms_code_client = dict.get('sms_code')
        access_token = dict.get('access_token')
        # 总体检验
        if not all([mobile, password, sms_code_client, access_token]):
            return JsonResponse({
                'code': 400,
                'errmsg': '船体数据补完整'
            })
        # 单个检验mobile
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return JsonResponse({
                'code': 400,
                'errmsg': '手机号错误'
            })
        # 单个检验password
        if not re.match(r'^[a-zA-Z0-9]{8,20}$', password):
            return JsonResponse({
                'code': 400,
                'errmsg': '密码有误'
            })

        # 单个检验sms_code，连接redis数据库
        redis_conn = get_redis_connection('verify_code')

        # 从redis数据库中获取数据
        sms_code_server = redis_conn.get('sms_%s' % mobile)

        # 判断sms_code是否存在
        if sms_code_server is None:
            return JsonResponse({
                'code': 400,
                'errmsg': '验证码过期'
            })

        # 对比客户端的sms_code跟服务端的sms_code
        if sms_code_server.decode() != sms_code_client:
            return JsonResponse({
                'code': 400,
                'errmsg': '验证码输入有误'
            })

        # 自定义一个函数，把access_token解密
        openid = check_access_token(access_token)

        if openid is None:
            return JsonResponse({
                'code': 400,
                'errmsg': 'access_token有误'
            })
        try:
            # 先从User模型类中获取该mobile用户，查看能够获取
            user = User.objects.get(mobile=mobile)
        except Exception as ret:
            # 如果获取不到，新增User对象
            User.objects.create_user(username=mobile,
                                     password=password,
                                     mobile=mobile)
        else:
            if not user.check_password(password):
                return JsonResponse({
                    'code': 400,
                    'errmsg': '密码有误'
                })

        try:
            # 向 QQ表中增加一个数据
            OAuthQQUser.objects.create(user=user,
                                       openid=openid)
        except Exception as ret:
            return JsonResponse({
                'code': 400,
                'errmsg': '写入数据库错误'
            })

        # 状态保持
        login(request, user)

        # cookie中写入username
        response = JsonResponse({
            'code': 0,
            'errmsg': 'ok'
        })

        response.set_cookie('username',
                            user.username,
                            max_age=3600*24*14)

        response = merge_carts_cookie_to_redis(request, response)

        # 返回json
        return response
