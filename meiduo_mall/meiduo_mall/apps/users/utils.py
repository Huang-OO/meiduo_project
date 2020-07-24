from django.contrib.auth.backends import ModelBackend
import re
from .models import User
from django.conf import settings
from itsdangerous import TimedJSONWebSignatureSerializer


def checkout_username_and_mobile_by_account(account):
    """用于区分account是用户名还是手机号，
    区分完成后，根据不同获取user"""
    try:
        if re.match(r'^1[3-9]\d{9}$', account):
            # 手机号
            user = User.objects.get(mobile=account)
        else:
            # 用户名
            user = User.objects.get(username=account)
    except Exception as ret:
        return None
    else:
        return user


class UsernameMobileAuthentications(ModelBackend):
    # 重写authenticate
    def authenticate(self, request, username=None, password=None, **kwargs):
        user = checkout_username_and_mobile_by_account(username)

        if user and user.check_password(password):
            return user
