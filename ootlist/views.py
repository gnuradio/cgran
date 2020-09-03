# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
from django.template import loader
from django_tables2 import RequestConfig
from django.shortcuts import redirect
from django.http import HttpResponse

from .models import Outoftreemodule
from .models import Packageversion
from .tables import OutoftreemoduleTable
from .forms import SearchForm

def index(request):
    package_versions = Packageversion.objects.all()
    if request.method == 'POST': # if this is a POST request we need to process the form data
        form = SearchForm(request.POST)
        if form.is_valid(): # check whether it's valid
            # search for oots with the provided string in either the name, tags, description, authors, or body_text
            objects = (Outoftreemodule.objects.filter(name__icontains=form.cleaned_data['search_text']) |
                       Outoftreemodule.objects.filter(tags__icontains=form.cleaned_data['search_text']) |
                       Outoftreemodule.objects.filter(description__icontains=form.cleaned_data['search_text']) |
                       Outoftreemodule.objects.filter(author__icontains=form.cleaned_data['search_text']) |
                       Outoftreemodule.objects.filter(body_text__icontains=form.cleaned_data['search_text']))
            table = OutoftreemoduleTable(objects, order_by=("-last_commit")) # icontains is case-insensitive
            RequestConfig(request, paginate={'per_page': 200}).configure(table)
            return render(request, 'ootlist/index.html', {'table': table, 'form': form, 'package_versions': package_versions})
    form = SearchForm()
    table = OutoftreemoduleTable(Outoftreemodule.objects.all(), order_by=("-last_commit"))
    RequestConfig(request, paginate={'per_page': 200}).configure(table)
    return render(request, 'ootlist/index.html', {'table': table, 'form': form, 'package_versions': package_versions})

# submit your own OOT link
def submit(request):
    return render(request, 'ootlist/submit.html')

# page that shows up when you click an OOT
def oot_page(request, oot_id):
    oot = Outoftreemodule.objects.get(pk=oot_id)
    return render(request, 'ootlist/oot_page.html', {'oot': oot})

def refresh(request):
    return HttpResponse("Refresh feature moved to management command called refresh, ran with a cronjob")
