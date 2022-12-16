from django.urls import re_path

from . import views

app_name = 'ootlist'

urlpatterns = [
    re_path(r'^$', views.index, name='index'),
    re_path(r'submit', views.submit, name='submit'),
    re_path(r'refresh', views.refresh, name='refresh'),
    re_path(r'^(?P<oot_id>[0-9]+)/$', views.oot_page, name='oot_page'),
]
