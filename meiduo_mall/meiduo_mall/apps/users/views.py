from django.shortcuts import render
from django.views import View

from carts.utils import merge_carts_cookie_to_redis
from goods.models import SKU
from .models import User, Address
from django.http import JsonResponse
from django_redis import get_redis_connection
from django.contrib.auth import login, authenticate, logout
import json
import re
from meiduo_mall.utils.view import LoginRequireMixin
from celery_tasks.email.tasks import send_verify_email

# Create your views here.
# from .utils import generate_access_token


class UsernameCountView(View):

    def get(self, request, username):
        """接受用户名判断是否重复注册"""
        # 1、进入数据库中的User中查询username相关的用户名个数
        try:
            count = User.objects.filter(username=username).count()
        except Exception as ret:
            return JsonResponse({'code': 400, 'errmsg': '查询数据库失败'})

        # 2、拼接json字符串， 返回前端
        return JsonResponse({'code': 0,
                             'errmsg': 'ok',
                             'count': count})


class MobilesCountView(View):
    def get(self, request, mobile):
        """验证手机号是否存在"""
        try:
            count = User.objects.filter(mobile=mobile).count()
        except Exception as ret:
            return JsonResponse({'code': 400, 'errmsg': '查询数据失败'})

        return JsonResponse({'code': 0,
                             'errmsg': 'ok',
                             'count': count})


class RegisterView(View):
    def post(self, request):

        dict = json.loads(request.body.decode())
        username = dict.get('username')
        password = dict.get('password')
        password1 = dict.get('password2')
        mobile = dict.get('mobile')
        allow = dict.get('allow')
        sms_code = dict.get('sms_code')

        if not all([username, password, password1, mobile, allow, sms_code]):
            return JsonResponse({
                'code': 400,
                'errmsg': '参数不完整'
            })

        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
            return JsonResponse({
                'code': 400,
                'errmsg': '用户名格式错误'
            })

        if not re.match(r'^[a-zA-Z0-9]{8,20}$', password):
            return JsonResponse({
                'code': 400,
                'errmsg': '密码格式有误'
            })

        if password != password1:
            return JsonResponse({
                'code': 400,
                'errmsg': '两次输入不正确'
            })

        if not re.match(r'^1[345789]\d{9}$', mobile):
            return JsonResponse({
                'code': 400,
                'errmsg': '手机号错误'
            })

        if allow is not True:
            return JsonResponse({
                'code': 400,
                'errmsg': 'allow有误'
            })

        redis_conn = get_redis_connection('verify_code')

        sms_code_server = redis_conn.get('sms_%s' % mobile)

        if not sms_code_server:
            return JsonResponse({
                'code': 400,
                'errmsg': 'sms_code_server过期'
            })

        if sms_code != sms_code_server.decode():
            return JsonResponse({
                'code': 400,
                'errmsg': '输入的短信验证码有误'
            })

        try:
            user = User.objects.create_user(username=username,
                                     password=password,
                                     mobile=mobile)
        except Exception as ret:
            return JsonResponse({
                'code': 400,
                'errmsg': '数据库存储失败'
            })

        login(request, user)

        response = JsonResponse({
            'code': 0,
            'errmsg': 'ok'
        })

        response.set_cookie('username',
                            user.username,
                            max_age=3600*24*14)

        response = merge_carts_cookie_to_redis(request, response)

        return response


class LoginView(View):
    def post(self, request):
        # 接收数据
        dic = json.loads(request.body.decode())

        username = dic.get('username')
        password = dic.get('password')
        remembered = dic.get('remembered')

        # 判断参数是否完整
        if not all([username, password]):
            return JsonResponse({
                'code': 400,
                'errmsg': '参数不完整'
            })

        # 判断用户
        user = authenticate(username=username,
                            password=password)

        if user is None:
            return JsonResponse({
                'code': 400,
                'errmsg': '用户名密码错误'
            })

        if remembered:
            request.session.set_expiry(None)
        else:
            request.session.set_expiry(0)

        login(request, user)

        response = JsonResponse({
            'code': 0,
            'errmsg': 'ok'
        })

        response.set_cookie('username',
                            user.username,
                            max_age=3600*24*14)

        response = merge_carts_cookie_to_redis(request, response)

        return response


class LogoutView(View):
    def delete(self, request):
        # 清除所有的session&sessionid===》logout
        logout(request)

        # 清除cookie中的username

        response = JsonResponse({
            'code': 0,
            'errmsg': 'ok'
        })

        response.delete_cookie('username')

        return response


class UserInfoView(LoginRequireMixin, View):

    def get(self, request):

        count_data = {
            'username': request.user.username,
            'mobile': request.user.mobile,
            'email': request.user.email,
            'email_active': request.user.email_active
        }

        return JsonResponse({
            'code': 0,
            'errmsg': 'ok',
            'info_data': count_data
        })


class EmailView(LoginRequireMixin, View):
    def put(self, request):
        """增加email到数据库"""
        # 接受json参数
        dict = json.loads(request.body.decode())
        email = dict.get('email')
        # 检验参数
        if not email:
            return JsonResponse({
                'code': 400,
                'errmsg': '缺少email'
            })

        if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return JsonResponse({
                'code': 400,
                'errmsg': '格式不正确'
            })

        try:
            request.user.email = email
            request.user.save()
        except Exception as ret:
            return JsonResponse({
                'code': 400,
                'errmsg': '保存失败'
            })

        # 给当前的email发送邮件
        verify_url = request.user.generate_access_token()
        send_verify_email.delay(email, verify_url)

        return JsonResponse({
            'code': 0,
            'errmsg': 'ok'
        })


class VeifyEmailView(View):
    def put(self, request):
        """验证链接"""

        # 接受参数
        token = request.GET.get('token')

        # 验证参数
        if not token:
            return JsonResponse({
                'code': 400,
                'errmsg': '确实token'
            })

        # 把token解密 ===》user
        user = User.decode_access_token(token)

        if not user:
            return JsonResponse({
                'code': 400,
                'errmsg': 'token有误'
            })
        # 把user的email_active改为True
        try:
            user.email_active = True

            user.save()
        except Exception as ret:
            return JsonResponse({
                'code': 400,
                'errmsg': '存储失败'
            })

        return JsonResponse({
            'code': 0,
            'errmsg': 'ok'
        })

        # 保存

        # 返回结果


class CreateAddressView(LoginRequireMixin, View):
    def post(self, request):
        try:
            count = Address.objects.filter(user=request.user, is_deleted=False).count()
        except Exception as ret:
            return JsonResponse({
                'code': 400,
                'errmsg': '数据库错误'
            })

        if count >= 20:
            return JsonResponse({
                'code': 400,
                'errmsg': '超过个数'
            })

        dict = json.loads(request.body.decode())
        receiver = dict.get('receiver')
        province_id = dict.get('province_id')
        city_id = dict.get('city_id')
        district_id = dict.get('district_id')
        place = dict.get('place')
        mobile = dict.get('mobile')
        tel = dict.get('tel')
        email = dict.get('email')

        if not all([receiver, province_id, city_id, district_id, place, mobile]):
            return JsonResponse({
                'code': 400,
                'errmsg': '参数不完整'
            })

        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return JsonResponse({
                'code': 400,
                'errmsg': '手机号错误'
            })

        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return JsonResponse({
                    'code': 400,
                    'errmsg': '电话号码有误'
                })

        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return JsonResponse({
                    'code': 400,
                    'errmsg': '邮箱错误'
                })

        try:
            address = Address.objects.create(
                user=request.user,
                province_id=province_id,
                city_id=city_id,
                district_id=district_id,
                title=receiver,
                receiver=receiver,
                mobile=mobile,
                place=place,
                tel=tel,
                email=email
            )

            if not request.user.default_address:
                request.user.default_address = address

                request.user.save()
        except Exception as ret:
            print(ret)
            return JsonResponse({
                'code': 400,
                'errmsg': '插入数据库错误'
            })

        address_dict = {
            "id": address.id,
            "title": address.title,
            "receiver": address.receiver,
            "province": address.province.name,
            "city": address.city.name,
            "district": address.district.name,
            "place": address.place,
            "mobile": address.mobile,
            "tel": address.tel,
            "email": address.email
        }

        # 响应保存结果
        return JsonResponse({'code': 0,
                             'errmsg': '新增地址成功',
                             'address': address_dict})


class ShowAddressView(View):
    def get(self, request):
        try:
            address_list = Address.objects.filter(user=request.user, is_deleted=False)

            addresses_list = []

            for address in address_list:
                dict = {
                    'id': address.id,
                    'title': address.title,
                    'receiver': address.receiver,
                    'province': address.province.name,
                    'city': address.city.name,
                    'district': address.district.name,
                    'place': address.place,
                    'mobile': address.mobile,
                    'tel': address.tel,
                    'email': address.email
                }
                default_address = request.user.default_address
                if default_address.id == address.id:
                    addresses_list.insert(0, dict)
                else:
                    addresses_list.append(dict)

        except Exception as ret:
            print(ret)
            return JsonResponse({
                'code': 400,
                'errmsg': '查询数据出错'
            })

        return JsonResponse({
            'code': 0,
            'errmsg': 'ok',
            'default_address_id': request.user.default_address_id,
            'addresses': addresses_list
        })


class ChangeAddressView(View):
    def put(self, request, address_id):
        try:
            count = Address.objects.filter(user=request.user, is_deleted=False).count()
        except Exception as ret:
            return JsonResponse({
                'code': 400,
                'errmsg': '数据库错误'
            })
        try:
            address = Address.objects.get(id=address_id)
        except Exception as ret:
            return JsonResponse({
                'code': 400,
                'errmsg': '修改的数据不存在'
            })

        if count >= 20:
            return JsonResponse({
                'code': 400,
                'errmsg': '超过个数'
            })

        dict = json.loads(request.body.decode())
        receiver = dict.get('receiver')
        province_id = dict.get('province_id')
        city_id = dict.get('city_id')
        district_id = dict.get('district_id')
        place = dict.get('place')
        mobile = dict.get('mobile')
        tel = dict.get('tel')
        email = dict.get('email')

        if not all([receiver, province_id, city_id, district_id, place, mobile]):
            return JsonResponse({
                'code': 400,
                'errmsg': '参数不完整'
            })

        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return JsonResponse({
                'code': 400,
                'errmsg': '手机号错误'
            })

        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return JsonResponse({
                    'code': 400,
                    'errmsg': '电话号码有误'
                })

        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return JsonResponse({
                    'code': 400,
                    'errmsg': '邮箱错误'
                })

        try:
            address.user = request.user
            address.province_id = province_id
            address.city_id = city_id
            address.district_id = district_id
            address.title = receiver
            address.receiver = receiver
            address.mobile = mobile
            address.place = place
            address.tel = tel
            address.email = email

            request.user.save()
        except Exception as ret:
            print(ret)
            return JsonResponse({
                'code': 400,
                'errmsg': '插入数据库错误'
            })

        address_dict = {
            "id": address.id,
            "title": address.title,
            "receiver": address.receiver,
            "province": address.province.name,
            "city": address.city.name,
            "district": address.district.name,
            "place": address.place,
            "mobile": address.mobile,
            "tel": address.tel,
            "email": address.email
        }

        # 响应保存结果
        return JsonResponse({'code': 0,
                             'errmsg': '修改地址成功',
                             'address': address_dict})

    def delete(self, request, address_id):
        try:
            address = Address.objects.get(id=address_id)
            address.is_deleted = True
            address.save()
        except Exception as ret:
            print(ret)
            return JsonResponse({
                'code': 400,
                'errmsg': '删除失败'
            })

        return JsonResponse({
            'code': 0,
            'errmsg': '删除成功'
        })


class DefaultAddressView(View):
    def put(self, request, address_id):
        try:
            address = Address.objects.get(id=address_id)
            request.user.default_address = address
            request.user.save()
        except Exception as ret:
            print(ret)
            return JsonResponse({
                'code': 400,
                'errmsg': '设置默认地址失败'
            })

        return JsonResponse({
            'code': 0,
            'errmsg': 'ok'
        })


class SetTitleView(View):
    def put(self, request, address_id):
        dict = json.loads(request.body.decode())
        title = dict.get('title')

        if not title:
            return JsonResponse({
                'code': 400,
                'errmsg': '参数不完整'
            })

        try:
            address = Address.objects.get(id=address_id)
            address.title = title
            address.save()
        except Exception as ret:
            return JsonResponse({
                'code': 400,
                'errmsg': '修改标题失败'
            })

        return JsonResponse({
            'code': 0,
            'errmsg': 'ok'
        })


class ChangePasswordView(View):
    def put(self, request):
        dict = json.loads(request.body.decode())
        old_password = dict.get('old_password')
        new_password = dict.get('new_password')
        new_password2 = dict.get('new_password2')

        if not all([old_password, new_password, new_password2]):
            return JsonResponse({
                'code': 400,
                'errmsg': '参数不完整'
            })

        if not request.user.check_password(old_password):
            return JsonResponse({
                'code': 400,
                'errmsg': '旧密码输入错误'
            })

        if not re.match(r'^[a-zA-Z0-9]{8,20}$', new_password):
            return JsonResponse({
                'code': 400,
                'errmsg': '请设置8-20位的密码'
            })

        if new_password != new_password2:
            return JsonResponse({
                'code': 400,
                'errmsg': '两次输入的密码不一致'
            })

        try:
            request.user.set_password(new_password)
            request.user.save()
        except Exception as ret:
            return JsonResponse({
                'code': 400,
                'errmsg': '存储数据库失败'
            })

        logout(request)

        response = JsonResponse({
            'code': 0,
            'errmsg': 'ok'
        })
        response.delete_cookie('username')
        return response


class SaveHistoryView(View):
    def post(self, request):
        """保存用户浏览记录"""
        # 接收参数
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')

        # 校验参数:
        try:
            SKU.objects.get(id=sku_id)
        except Exception as e:
            return JsonResponse({
                'code': 400,
                'errmsg': 'sku不存在'
            })

        # 保存用户浏览数据
        redis_conn = get_redis_connection('history')
        pl = redis_conn.pipeline()
        user_id = request.user.id

        # 先去重: 这里给 0 代表去除所有的 sku_id
        pl.lrem('history_%s' % user_id, 0, sku_id)
        # 再存储
        pl.lpush('history_%s' % user_id, sku_id)
        # 最后截取: 界面有限, 只保留 5 个
        pl.ltrim('history_%s' % user_id, 0, 4)
        # 执行管道
        pl.execute()

        # 响应结果
        return JsonResponse({'code': 0,
                             'errmsg': 'OK'})

    def get(self, request):
        """获取用户浏览记录"""
        # 获取Redis存储的sku_id列表信息
        redis_conn = get_redis_connection('history')
        sku_ids = redis_conn.lrange('history_%s' % request.user.id, 0, -1)

        # 根据sku_ids列表数据，查询出商品sku信息
        skus = []
        for sku_id in sku_ids:
            sku = SKU.objects.get(id=sku_id)
            skus.append({
                'id': sku.id,
                'name': sku.name,
                'default_image_url': sku.default_image_url,
                'price': sku.price
            })

        return JsonResponse({'code': 0,
                             'errmsg': 'OK',
                         'skus': skus})
