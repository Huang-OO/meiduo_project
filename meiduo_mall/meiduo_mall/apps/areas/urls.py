from django.urls import re_path
from . import views

urlpatterns = [
    re_path(r'areas/(?P<pk>[1-9]\d+)/', views.SubAreaView.as_view()),
    re_path(r'^areas/', views.ProvinceAreaView.as_view()),

]
