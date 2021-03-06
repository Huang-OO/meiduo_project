from django.urls import re_path
from . import views

urlpatterns = [
    re_path(r'^usernames/(?P<username>[a-zA-Z0-9_-]{5,20})/count/', views.UsernameCountView.as_view()),
    re_path(r'^mobiles/(?P<mobile>1[3-9]\d{9})/count/', views.MobilesCountView.as_view()),
    re_path(r'^register/', views.RegisterView.as_view()),
    re_path(r'^login/', views.LoginView.as_view()),
    re_path(r'^logout/', views.LogoutView.as_view()),
    re_path(r'^info/', views.UserInfoView.as_view()),
    re_path(r'^emails/$', views.EmailView.as_view()),
    re_path(r'^emails/verification/$', views.VeifyEmailView.as_view()),
    re_path(r'^addresses/create/$', views.CreateAddressView.as_view()),
    re_path(r'^addresses/$', views.ShowAddressView.as_view()),
    re_path(r'^addresses/(?P<address_id>\d+)/default/', views.DefaultAddressView.as_view()),
    re_path(r'addresses/(?P<address_id>\d+)/title/', views.SetTitleView.as_view()),
    re_path(r'^addresses/(?P<address_id>\d+)/', views.ChangeAddressView.as_view()),
    re_path(r'^password/', views.ChangePasswordView.as_view()),
    re_path(r'^browse_histories/', views.SaveHistoryView.as_view()),

]
