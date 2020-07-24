from django.http import JsonResponse


def login_require(func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            # 登录成功
            return func(request, *args, **kwargs)
        else:
            return JsonResponse({
                'code': 400,
                'errmsg': '未登录'
            })
    return wrapper


# 定义一个Mixin扩展类


class LoginRequireMixin(object):
    @classmethod
    def as_view(cls, *args, **kwargs):
        view = super().as_view(*args, **kwargs)

        return login_require(view)