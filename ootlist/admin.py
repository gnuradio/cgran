# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

# add Outoftreemodule to admin panel, in a way that shows name and repo when you show the full list
from .models import Outoftreemodule
class OutoftreemoduleAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'repo')
admin.site.register(Outoftreemodule, OutoftreemoduleAdmin)
