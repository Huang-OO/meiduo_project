from django.core.paginator import Paginator, EmptyPage
from django.shortcuts import render
from django.views import View
from goods.models import SKU, GoodsCategory
from django.http import JsonResponse
from .utils import get_breadcrumb
from haystack.views import SearchView
from django.conf import settings

# Create your views here.


class ListView(View):
    def get(self, request, category_id):
        # 接受参数
        page = request.GET.get('page')
        page_size = request.GET.get('page_size')
        ordering = request.GET.get('ordering')

        # 校验参数
        if not all([page, page_size, ordering]):
            return JsonResponse({
                'code': 400,
                'errmsg': '缺少参数'
            })

        # 根据category_id 获取对应类别
        try:
            category = GoodsCategory.objects.get(id=category_id)
        except Exception as ret:
            return JsonResponse({
                'code': 400,
                'errmsg': '没有对应的商品类别'
            })
        dict = get_breadcrumb(category)

        # 从SKU表中获取该类的商品
        try:
            skus = SKU.objects.filter(category=category,
                              is_launched=True).order_by(ordering)
        except Exception as ret:
            print(ret)
            return JsonResponse({
                'code': 400,
                'errmsg': '读取上数据库失败'
            })

        paginator = Paginator(skus, page_size)

        try:
            page_skus = paginator.page(page)
        except EmptyPage as ret:
            return JsonResponse({
                'code': 400,
                'errmsg': '获取该页数据失败'
            })

        total_pages = paginator.num_pages

        list = []
        for sku in page_skus:
            list.append({
                'id': sku.id,
                'default_image_url': sku.default_image_url,
                'name': sku.name,
                'price': sku.price
            })

        return JsonResponse({
            'code': 0,
            'errmsg': 'ok',
            'count': total_pages,
            'list': list,
            'breadcrumb': dict
        })


class HotGoodsView(View):
    def get(self, request, category_id):
        try:
            skus = SKU.objects.filter(category_id=category_id,
                               is_launched=True).order_by('-sales')[:2]

        except Exception as ret:
            return JsonResponse({
                'code': 400,
                'errmsg': '查询数据库失败'
            })

        list = []
        for sku in skus:
            list.append({
                'id': sku.id,
                'default_image_url': sku.default_image_url,
                'name': sku.name,
                'price': sku.price
            })

        return JsonResponse({
            'code': 0,
            'errmsg': 'ok',
            'hot_skus': list
        })


class MySearchView(SearchView):
    '''重写SearchView类'''
    def create_response(self):
        page = self.request.GET.get('page')
        # 获取搜索结果
        context = self.get_context()
        data_list = []
        for sku in context['page'].object_list:
            data_list.append({
                'id': sku.object.id,
                'name': sku.object.name,
                'price': sku.object.price,
                'default_image_url': sku.object.default_image_url,
                'searchkey': context.get('query'),
                'page_size': settings.HAYSTACK_SEARCH_RESULTS_PER_PAGE,
                'count': context['page'].paginator.count
            })
        # 拼接参数, 返回
        return JsonResponse(data_list, safe=False)



