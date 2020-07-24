from django.core.cache import cache
from django.shortcuts import render
from django.views import View
from django.http import JsonResponse
from .models import Area

# Create your views here.


class ProvinceAreaView(View):
    def get(self, request):
        province_list = cache.get('province_list')
        if not province_list:
            try:
                province_model_list = Area.objects.filter(parent__isnull=True)

                province_list = []

                for province in province_model_list:
                    province_list.append({
                        'id': province.id,
                        'name': province.name
                    })
                cache.set('province_list', province_list, 3600)
            except Exception as ret:
                return JsonResponse({
                    'code': 400,
                    'errmsg': '查询数据库错误'
                })

        return JsonResponse({
            'code': 0,
            'errmsg': 'ok',
            'province_list': province_list
        })


class SubAreaView(View):
    def get(self, request, pk):
        sub_data = cache.get('sub_data_' + pk)
        if not sub_data:
            try:

                parent_model = Area.objects.get(id=pk)

                sub_model_list = parent_model.area_set.all()

                sub_list = []

                for sub_model in sub_model_list:
                    sub_list.append({
                        'id': sub_model.id,
                        'name': sub_model.name
                    })
                sub_data = {
                    'id': pk,
                    'name': parent_model.name,
                    'subs': sub_list
                }
                cache.set('sub_data_' + pk, sub_data, 3600)
            except Exception as ret:
                print(ret)
                return JsonResponse({
                    'code': 400,
                    'errmsg': '查询错误'
                })

        return JsonResponse({
            'code': 0,
            'errmsg': 'ok',
            'sub_data': sub_data
        })
