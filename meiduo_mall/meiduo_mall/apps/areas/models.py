from django.db import models

# Create your models here.


class Area(models.Model):
    name = models.CharField(max_length=20)

    parent = models.ForeignKey('self',
                               on_delete=models.SET_NULL,
                               null=True,
                               blank=True)

    class Meta:
        db_table = 'tb_areas'
