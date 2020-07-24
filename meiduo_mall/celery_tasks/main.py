import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meiduo_mall.settings.dev')
# 导入celery
from celery import Celery

# 创建celery对象
celery_app = Celery('meiduo')

# 给对象配置添加文件
celery_app.config_from_object('celery_tasks.config')

# 定义任务
# 给对象关联任务
celery_app.autodiscover_tasks(['celery_tasks.sms', 'celery_tasks.email', 'celery_tasks.html'])
