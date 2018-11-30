# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
from django.template import loader
from django_tables2 import RequestConfig
from django.shortcuts import redirect

from .models import Outoftreemodule
from .models import Packageversion
from .tables import OutoftreemoduleTable
from .forms import SearchForm

from django.utils.dateparse import parse_datetime

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
    print("RUNING SCRAPER") # FIXME get this code pulled out into another filed called scraper.py
    import urllib.request
    import subprocess
    import os
    import shutil
    import yaml # yaml parser
    from io import StringIO # allows strings to be converted to file object type things
    import re
    import datetime 
    import mistune # markdown parser
    
    # get around unicode error because of symbols in peoples names
    #import sys
    #reload(sys)
    #sys.setdefaultencoding('utf-8')

    # pull versions of gnuradio in ubuntu packages
    Packageversion.objects.all().delete() # clear out the table
    ubuntu14 = 'https://packages.ubuntu.com/trusty/gnuradio'
    ubuntu16 = 'https://packages.ubuntu.com/xenial/gnuradio'
    ubuntu18 = 'https://packages.ubuntu.com/bionic/gnuradio'
    ubuntus = [(ubuntu14, 'Ubuntu-14.04'), (ubuntu16, 'Ubuntu-16.04'), (ubuntu18, 'Ubuntu-18.04')]
    for ubuntu in ubuntus:
        response = urllib.request.urlopen(ubuntu[0])
        html = response.read().decode('utf-8')
        indx = html.find('Package: gnuradio')
        indx2 = html[indx:].find('-')
        new_packageversion = Packageversion(os_name = ubuntu[1], gr_version_string = html[indx+19:indx+indx2])
        new_packageversion.save() # add to db

    def git(*args):
        return subprocess.check_call(['git'] + list(args))

    # who needs bash!
    shutil.rmtree('gr-recipes', ignore_errors=True)  # remove directory gr-recipes
    shutil.rmtree('gr-etcetera', ignore_errors=True) # remove directory gr-etcetera
    git("clone", 'git://github.com/gnuradio/gr-recipes.git') # clone repo
    git("clone", 'git://github.com/gnuradio/gr-etcetera.git') # clone repo

    # get list of lwr files
    gr_recipes = ['gr-recipes/' + recipe for recipe in os.listdir('gr-recipes')]
    gr_etcetera = ['gr-etcetera/' + recipe for recipe in os.listdir('gr-etcetera')]
    recipes = gr_recipes + gr_etcetera
    new_oots = [] # will contain new objects, that then get saved all at once
    f = open('blacklist.txt', 'r') # read in list of recipes that are definitely not OOTs
    blacklist = f.read().split('\n')
    f.close()
    for recipe in recipes:
        if '.lwr' in recipe and recipe not in blacklist:
            # read the lwr file
            doc = open(recipe, 'r').read()
            indx = doc.find('source: ')
            if indx != -1:
                indx2 = doc[indx:].find('\n')
                if indx2 != -1:
                    # fetch the raw MANIFEST.md of each recipe
                    indx4 = doc[indx:indx+indx2].find('github.com/') # right now cgran only works with OOTs in github =(
                    if indx4 != -1:
                        giturl = doc[indx+indx4+11:indx+indx2]
                        giturl = giturl.replace('.git','') # remove the .git that most of them have at the end
                        giturl = giturl.replace('/releases/download/v2.6.1/protobuf-2.6.1.tar.gz','') # the protobufs recipe is a weird one
                        try: # a good chunk of OOTs dont have this file
                            f = urllib.request.urlopen('https://raw.githubusercontent.com/' + giturl + '/master/MANIFEST.md') 
                            manifest = f.read().decode('utf-8') # this converts it from a byte object to a python string   
                        except:
                            manifest = '' # this will cause the fields to be blank
                        indx3 = manifest.find('---') # this bar separates header from "body_text"
                        f2 = StringIO(manifest[:indx3]) # annoying step, pyyaml wants a file object but i already have it in a string, so i wrap the string as a file object
                        md = mistune.Markdown() # at some point they changed the way Markdown objects work
                        body_text = md.parse(manifest[indx3+3:]) # grab everything after the bar, and run it through markdown parser                    
                        #if indx3 != -1:
                        # parse yaml, creates dict, extract what we want
                        try:
                            processed_yaml = yaml.safe_load(f2) 
                            # fetch branches page of github to find the most recent commit
                            f = urllib.request.urlopen('https://github.com/' + giturl + '/branches') 
                            branch_page = f.read().decode('utf-8') # this converts it from a byte object to a python string   
                            updateds = [m.start() for m in re.finditer('time-ago datetime=', branch_page)]
                            dates = []
                            for updated in updateds:
                                date = branch_page[updated+19:updated+29] # pull out date in year-mn-dy format
                                dates.append(datetime.date(int(date[0:4]), int(date[5:7]), int(date[8:10]))) # parse out year/month/day  
                            if dates: # if dates is empty its an indication the URL was broken so the OOT doesn't get added to the list
                                commit_date = max(dates) # most recent commit
                                if processed_yaml: # if the MANIFEST file existed
                                    new_oots.append(Outoftreemodule(name = giturl.split('/')[1].replace('-','‑'), # people kept giving their stuff long titles, it worked out better to just use their github project url. also, i replace the standard hyphen with a non-line-breaking hyphen =)
                                                                    tags = ", ".join(processed_yaml.get('tags',['None'])), 
                                                                    description = processed_yaml.get('brief', 'None'), 
                                                                    repo = 'https://github.com/' + giturl, # use repo from lwr instead of that provided in manifest 
                                                                    last_commit = commit_date,
                                                                    author = ", ".join(processed_yaml.get('author', ['None'])),
                                                                    dependencies = ", ".join(processed_yaml.get('dependencies', ['None'])),
                                                                    copyright_owner = ", ".join(processed_yaml.get('copyright_owner', ['None'])),
                                                                    icon = processed_yaml.get('icon', 'None'),
                                                                    website = processed_yaml.get('website', 'None'),
                                                                    body_text = body_text)) 
                                else:
                                    new_oots.append(Outoftreemodule(name = giturl.split('/')[1].replace('-','‑'), # people kept giving their stuff long titles, it worked out better to just use their github project url. also, i replace the standard hyphen with a non-line-breaking hyphen =)
                                                                    tags = 'None', 
                                                                    description = 'None', 
                                                                    repo = 'https://github.com/' + giturl, # use repo from lwr instead of that provided in manifest 
                                                                    last_commit = commit_date,
                                                                    author = 'None',
                                                                    dependencies = 'None',
                                                                    copyright_owner = 'None',
                                                                    icon = 'None',
                                                                    website = 'None',
                                                                    body_text = body_text))                                                        
                            else:
                                print('error- recipe ' + recipe + ' had a broken URL')
                                    
                        except yaml.YAMLError:
                            print(giturl, "had error parsing MANIFEST yaml")
                        except urllib.error.HTTPError:
                            print('error opening up the branches page of recipe: ' + recipe)

                    else:
                        print('*** Skipping recipe ' + recipe + ' because its not github based')    
                else: 
                    print('error- recipe ' + recipe + ' had no new line at the end of the source field')    
            else: 
                print('error- recipe ' + recipe + ' had no source: field')    
                        
    # Go through and manually add a bunch of OOTs that do not use github
    new_oots.append(Outoftreemodule(name = 'gr-iqbal'.replace('-','‑'), # people kept giving their stuff long titles, it worked out better to just use their github project url. also, i replace the standard hyphen with a non-line-breaking hyphen =)
                                    tags = ", ".join(['iq imbalance','rx','osmocom']), 
                                    description = 'GNU Radio block to correct IQ imbalance in quadrature receivers', 
                                    repo = 'git://git.osmocom.org/gr-iqbal', 
                                    last_commit = parse_datetime('2015-11-21 11:47:58'),
                                    author = 'Sylvain Munaut <tnt@246tNt.com>',
                                    dependencies = 'None',
                                    copyright_owner = 'Sylvain Munaut <tnt@246tNt.com>',
                                    icon = 'http://people.osmocom.org/~tnt/stuff/iqbal-icon.png',
                                    website = 'None',
                                    body_text = ' '))      
    
    new_oots.append(Outoftreemodule(name = 'gr-fosphor'.replace('-','‑'), # people kept giving their stuff long titles, it worked out better to just use their github project url. also, i replace the standard hyphen with a non-line-breaking hyphen =)
                                    tags = ", ".join(['fft','gpu','opencl','opengl']), 
                                    description = 'GNU Radio block for RTSA-like spectrum visualization using OpenCL and OpenGL acceleration', 
                                    repo = 'git://git.osmocom.org/gr-fosphor', 
                                    last_commit = parse_datetime('2016-05-22 11:47:58'),
                                    author = 'Sylvain Munaut <tnt@246tNt.com>',
                                    dependencies = 'None',
                                    copyright_owner = 'Sylvain Munaut <tnt@246tNt.com>',
                                    icon = 'http://people.osmocom.org/~tnt/stuff/fosphor-icon.png',
                                    website = 'None',
                                    body_text = ' '))  
                                        
    # clear table
    Outoftreemodule.objects.all().delete()
    # all the new objects to db
    for new_oot in new_oots:
        new_oot.save() # adds to db
                                    
    table = OutoftreemoduleTable(Outoftreemodule.objects.all(), order_by=("status", "name"))
    RequestConfig(request, paginate={'per_page': 100}).configure(table)
    return render(request, 'ootlist/index.html', {'table': table})
