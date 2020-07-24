from django.db import models
from meiduo_mall.utils.BaseModel import BaseModel

# Create your models here.


class OAuthQQUser(BaseModel):
    user = models.ForeignKey('users.User',
                             on_delete=models.CASCADE)

    openid = models.CharField(max_length=64,
                              db_index=True)

    class Meta:
        db_table = 'tb_oauth_qq'
