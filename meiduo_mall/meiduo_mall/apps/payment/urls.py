from django.urls import re_path
from . import views


urlpatterns = [
    # 订单支付
    re_path(r'^payment/(?P<order_id>\d+)/$', views.PaymentView.as_view()),
    # 订单支付状态
    re_path(r'^payment/status/$', views.PaymentStatusView.as_view()),
]
