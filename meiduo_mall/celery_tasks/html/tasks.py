import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meiduo_mall.settings.dev')
sys.path.insert(0, '../../')
django.setup()

from goods.models import SKU
from django.conf import settings
from django.template import loader
from celery_tasks.main import celery_app
from goods.utils import get_goods_and_spec, get_categories


@celery_app.task(name='generate_static_sku_detail_html')
def generate_static_sku_detail_html(sku_id):
    """
        生成静态商品详情页面
        :param sku_id: 商品id值
        """
    # 商品分类菜单
    dict = get_categories()

    goods, specs, sku = get_goods_and_spec(sku_id)

    # 渲染模板，生成静态html文件
    context = {
        'categories': dict,
        'goods': goods,
        'specs': specs,
        'sku': sku
    }

    # 加载 loader 的 get_template 函数, 获取对应的 detail 模板
    template = loader.get_template('detail.html')
    # 拿到模板, 将上面添加好的数据渲染进去.
    html_text = template.render(context)
    # 拼接模板要生成文件的位置:
    file_path = os.path.join(settings.GENERATED_STATIC_HTML_FILES_DIR, 'goods/' + str(sku_id) + '.html')
    # 写入
    with open(file_path, 'w') as f:
        f.write(html_text)


if __name__ == '__main__':
    # 获取所有的商品信息
    skus = SKU.objects.all()
    # 遍历拿出所有的商品:
    for sku in skus:
        print(sku.id)
        # 调用我们之前在 celery_tasks.html.tasks 中写的生成商品静态页面的方法:
        # 我们最好把这个函数单独复制过来, 这样可以不依靠 celery, 否则必须要开启celery
        generate_static_sku_detail_html(sku.id)
