# nnmware(c)2012-2020

from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _

from nnmware.apps.address.models import Country
from nnmware.core.abstract import AbstractColor, AbstractName, AbstractVendor, AbstractDate
from nnmware.apps.business.models import AbstractSeller
from nnmware.core.utils import current_year, tuplify


class VehicleColor(AbstractColor):
    pass


class VehicleKind(AbstractName):
    pass

    class Meta:
        verbose_name = _('Vehicle type')
        verbose_name_plural = _('Vehicle types')


class ForVehicles(models.Model):
    type_vehicles = models.ManyToManyField(VehicleKind, verbose_name=_('Using in vehicles'), blank=True)

    class Meta:
        abstract = True


class VehicleTransmission(AbstractName, ForVehicles):
    pass

    class Meta:
        verbose_name = _('Transmission type')
        verbose_name_plural = _('Transmission types')


class VehicleCarcass(AbstractName, ForVehicles):
    pass

    class Meta:
        verbose_name = _('Vehicle carcass type')
        verbose_name_plural = _('Vehicle carcass types')


class VehicleEngine(AbstractName, ForVehicles):
    pass

    class Meta:
        verbose_name = _('Vehicle carcass type')
        verbose_name_plural = _('Vehicle carcass types')


class VehicleFeature(AbstractName, ForVehicles):
    pass

    class Meta:
        verbose_name = _('Vehicle feature')
        verbose_name_plural = _('Vehicle features')


class VehicleMark(AbstractName, ForVehicles):
    pass

    class Meta:
        verbose_name = _('Vehicle mark')
        verbose_name_plural = _('Vehicle mark')


class VehicleVendor(AbstractVendor, ForVehicles):
    country = models.ForeignKey(Country, verbose_name=_('Country'), null=True, blank=True, on_delete=models.SET_NULL)


VEHICLE_YEAR = map(tuplify, range(current_year - 55, current_year + 1))


class Vehicle(AbstractName, AbstractDate, AbstractSeller):
    kind = models.ForeignKey(VehicleKind, verbose_name=_('Type of vehicle'), on_delete=models.CASCADE)
    color = models.ForeignKey(VehicleColor, verbose_name=_('Vehicle color'), on_delete=models.CASCADE)
    transmission = models.ForeignKey(VehicleTransmission, verbose_name=_('Type of transmission'), on_delete=models.CASCADE)
    carcass = models.ForeignKey(VehicleCarcass, verbose_name=_('Carcass of vehicle'), on_delete=models.CASCADE)
    engine = models.ForeignKey(VehicleEngine, verbose_name=_('Engine of vehicle'), on_delete=models.CASCADE)
    vendor = models.ForeignKey(VehicleVendor, verbose_name=_('Vendor of vehicle'), on_delete=models.CASCADE)
    mileage = models.IntegerField(verbose_name=_('Mileage'), null=True, blank=True)
    vin = models.CharField(verbose_name=_('VIN-code'), max_length=100, blank=True)
    horsepower = models.IntegerField(verbose_name=_('Horsepower'), null=True, blank=True)
    displacement = models.IntegerField(verbose_name=_('Displacement'), null=True, blank=True)
    features = models.ManyToManyField(VehicleFeature, verbose_name=_('Vehicle features'))
    year = models.IntegerField(verbose_name=_('Year'), choices=VEHICLE_YEAR, default=None, blank=True, null=True)
    mark = models.ForeignKey(VehicleMark, verbose_name=_('Mark of vehicle'), on_delete=models.CASCADE)
    left_control = models.BooleanField(verbose_name=_('Left hand drive'), default=False)

    class Meta:
        verbose_name = _('Vehicle')
        verbose_name_plural = _('Vehicles')
