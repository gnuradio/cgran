# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

class Outoftreemodule(models.Model):
    name = models.CharField(max_length=500)
    tags = models.CharField(max_length=500, null=True, blank=True)
    description = models.CharField(max_length=500, null=True, blank=True)
    repo = models.URLField(max_length=500, null=True, blank=True)
    added_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=30, null=True, blank=True) # green, yellow, red
    last_commit = models.DateField(null=True, blank=True)
    author = models.CharField(max_length=500, null=True, blank=True)
    dependencies = models.CharField(max_length=500, null=True, blank=True)
    copyright_owner = models.CharField(max_length=500, null=True, blank=True)
    icon = models.CharField(max_length=500, null=True, blank=True) # most urls provided by people dont even work anymore, so dont display the icon for now
    website = models.CharField(max_length=500, null=True, blank=True)
    body_text = models.CharField(max_length=50000, null=True, blank=True)
    
class Packageversion(models.Model):
    os_name = models.CharField(max_length=500)
    gr_version_string = models.CharField(max_length=500)
