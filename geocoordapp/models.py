from django.db import models


class Place(models.Model):
    lon = models.FloatField(
        verbose_name='Долгота',
        blank=True,
        null=True,
    )
    lat = models.FloatField(
        verbose_name='Широта',
        blank=True,
        null=True,
    )
    address = models.CharField(
        max_length=256,
        verbose_name='Адрес',
        unique=True,
    )
    updated_at = models.TimeField(
        auto_now=True,
        verbose_name='Время обновления',
    )

    class Meta:
        verbose_name = 'место'
        verbose_name_plural = 'места'
