# nnmware(c)2012-2020

from __future__ import unicode_literals

from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class TopicAppConfig(AppConfig):
    name = "nnmware.apps.topic"
    verbose_name = _("Topic module")
