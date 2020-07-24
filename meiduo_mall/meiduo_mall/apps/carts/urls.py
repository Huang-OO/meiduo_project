from django.urls import re_path
from . import views


urlpatterns = [
    re_path(r'^carts/selection/', views.SelectAllView.as_view()),
    re_path(r'^carts/', views.CartsView.as_view()),

]
