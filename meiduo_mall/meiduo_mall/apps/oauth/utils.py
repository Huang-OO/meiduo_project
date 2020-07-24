from itsdangerous import TimedJSONWebSignatureSerializer
from django.conf import settings


def generate_access_token(openid):
    """把openid加密为access_token"""

    dict = {
        'openid': openid
    }

    # JSONWebSignatureSerializer(秘钥， 有效期)
    obj = TimedJSONWebSignatureSerializer(settings.SECRET_KEY, 300)
    token_bytes = obj.dumps(dict)
    token = token_bytes.decode()

    return token


def check_access_token(access_token):
    """把access_token解密"""

    obj = TimedJSONWebSignatureSerializer(settings.SECRET_KEY, 300)
    try:
        data = obj.loads(access_token)
    except Exception as ret:
        return None
    else:
        return data.get('openid')
