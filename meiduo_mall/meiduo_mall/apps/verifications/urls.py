from django.urls import re_path
from .views import VerificationsView, SMSCodeView

urlpatterns = [
    re_path(r'^image_codes/(?P<uuid>[\w-]+)/', VerificationsView.as_view()),
    re_path(r'^sms_codes/(?P<mobile>1[3-9]\d{9})/', SMSCodeView.as_view()),

]
