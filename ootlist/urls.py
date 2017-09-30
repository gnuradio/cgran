from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'submit', views.submit, name='submit'),
    url(r'refresh', views.refresh, name='refresh'),
    url(r'^(?P<oot_id>[0-9]+)/$', views.oot_page, name='oot_page'), 
]
