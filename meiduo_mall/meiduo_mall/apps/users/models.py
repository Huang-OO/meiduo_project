from django.contrib.auth.models import AbstractUser
from django.db import models
from itsdangerous import TimedJSONWebSignatureSerializer, BadData
from django.conf import settings
from meiduo_mall.utils.BaseModel import BaseModel


class User(AbstractUser):

    # 新增一个mobile字段， 用于记录前端发送的手机号信息
    mobile = models.CharField(max_length=11, unique=True, verbose_name='手机号')

    # 用于记录邮箱是否激活
    email_active = models.BooleanField(default=False)

    default_address = models.ForeignKey('Address',
                                        related_name='users',
                                        null=True,
                                        blank=True,
                                        on_delete=models.SET_NULL,
                                        verbose_name='默认地址')
    
    class Meta:
        db_table = 'tb_users'

    def __str__(self):
        return self.username

    def generate_access_token(self):
        obj = TimedJSONWebSignatureSerializer(settings.SECRET_KEY,
                                              600)
        dict = {
            'user_id': self.id,
            'email': self.email
        }
        token = obj.dumps(dict).decode()

        verify_url = settings.EMAIL_VERIFY_URL + token

        return verify_url

    @staticmethod
    def decode_access_token(token):
        """把token解密，获取user"""
        obj = TimedJSONWebSignatureSerializer(settings.SECRET_KEY, 600)
        try:
            dict = obj.loads(token)
        except BadData:
            return None
        else:
            user_id = dict.get('user_id')

            email = dict.get('email')

        try:
            user = User.objects.get(id=user_id,
                             email=email)
        except Exception as ret:
            return None
        else:
            return user


# 增加地址的模型类, 放到User模型类的下方:
class Address(BaseModel):
    """
    用户地址
    """
    user = models.ForeignKey(User,
                             on_delete=models.CASCADE,
                             related_name='addresses',
                             verbose_name='用户')

    province = models.ForeignKey('areas.Area',
                                 on_delete=models.PROTECT,
                                 related_name='province_addresses',
                                 verbose_name='省')

    city = models.ForeignKey('areas.Area',
                             on_delete=models.PROTECT,
                             related_name='city_addresses',
                             verbose_name='市')

    district = models.ForeignKey('areas.Area',
                                 on_delete=models.PROTECT,
                                 related_name='district_addresses',
                                 verbose_name='区')

    title = models.CharField(max_length=20, verbose_name='地址名称')
    receiver = models.CharField(max_length=20, verbose_name='收货人')
    place = models.CharField(max_length=50, verbose_name='地址')
    mobile = models.CharField(max_length=11, verbose_name='手机')
    tel = models.CharField(max_length=20,
                           null=True,
                           blank=True,
                           default='',
                           verbose_name='固定电话')

    email = models.CharField(max_length=30,
                             null=True,
                             blank=True,
                             default='',
                             verbose_name='电子邮箱')

    is_deleted = models.BooleanField(default=False, verbose_name='逻辑删除')

    class Meta:
        db_table = 'tb_address'
        verbose_name = '用户地址'
        verbose_name_plural = verbose_name
        ordering = ['-update_time']
