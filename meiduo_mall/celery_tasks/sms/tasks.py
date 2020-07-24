# 定义任务
from celery_tasks.main import celery_app
from celery_tasks.yuntongxun.ccp_sms import CCP


@celery_app.task(name='send_sms_code')
def send_sms_code(mobile, sms_code):
    # 发送短信
    result = CCP().send_template_sms(mobile, [sms_code, 5], 1)

    return result
