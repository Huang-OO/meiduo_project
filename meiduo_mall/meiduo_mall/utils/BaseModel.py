from django.db import models


class BaseModel(models.Model):
    # 创建时间
    # auto_now_add: 自动添加
    create_time = models.DateTimeField(auto_now_add=True,
                                       )

    # 更新时间
    # auto_now: 自动更新
    update_time = models.DateTimeField(auto_now=True)

    class Meta:
        # 抽象类
        abstract = True
