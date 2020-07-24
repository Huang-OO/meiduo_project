from django.urls import re_path
from . import views


urlpatterns = [
    re_path(r'^orders/settlement/', views.OrderSettlementView.as_view()),
    re_path(r'^orders/commit/', views.SaveOrdersView.as_view()),
]
