# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
from django.template import loader
from django_tables2 import RequestConfig
from django.shortcuts import redirect

from .models import Outoftreemodule
from .tables import OutoftreemoduleTable
from .forms import SearchForm

def index(request):
    if request.method == 'POST': # if this is a POST request we need to process the form data
        form = SearchForm(request.POST)
        if form.is_valid(): # check whether it's valid
            # search for oots with the provided string in either the name, tags, description, authors, or body_text
            objects = (Outoftreemodule.objects.filter(name__icontains=form.cleaned_data['search_text']) | 
                       Outoftreemodule.objects.filter(tags__icontains=form.cleaned_data['search_text']) |
                       Outoftreemodule.objects.filter(description__icontains=form.cleaned_data['search_text']) |
                       Outoftreemodule.objects.filter(author__icontains=form.cleaned_data['search_text']) |
                       Outoftreemodule.objects.filter(body_text__icontains=form.cleaned_data['search_text']))
            table = OutoftreemoduleTable(objects) # icontains is case-insensitive
            RequestConfig(request, paginate={'per_page': 100}).configure(table)
            return render(request, 'ootlist/index.html', {'table': table, 'form': form})
    else:
        form = SearchForm()
        table = OutoftreemoduleTable(Outoftreemodule.objects.all(), order_by=("-last_commit"))
        RequestConfig(request, paginate={'per_page': 200}).configure(table)
        return render(request, 'ootlist/index.html', {'table': table, 'form': form})

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
    for recipe in recipes:
        if '.lwr' in recipe:
            # read the lwr file
            doc = open(recipe, 'r').read()
            indx = doc.find('source: ')
            if indx != -1:
                indx2 = doc[indx:].find('.git')
                if indx2 != -1:
                    # fetch the raw MANIFEST.md of each recipe
                    indx4 = doc[indx:indx+indx2].find('github.com/')
                    if indx4 != -1:
                        giturl = doc[indx+indx4+11:indx+indx2]
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
                            print(giturl)
                            
                            # blacklist stuff that's not actually an OOT (edit blacklist.txt to add more)
                            f = open('blacklist.txt', 'r')
                            blacklist = f.read().split('\n')
                            f.close()
                            if giturl not in blacklist:
                                # fetch branches page of github to find the most recent commit
                                f = urllib.request.urlopen('https://github.com/' + giturl + '/branches') 
                                branch_page = f.read().decode('utf-8') # this converts it from a byte object to a python string   
                                updateds = [m.start() for m in re.finditer('time-ago datetime=', branch_page)]
                                dates = []
                                for updated in updateds:
                                    date = branch_page[updated+19:updated+29] # pull out date in year-mn-dy format
                                    dates.append(datetime.date(int(date[0:4]), int(date[5:7]), int(date[8:10]))) # parse out year/month/day  
                                if dates: # if dates is empty its an indication the URL was broken
                                    commit_date = max(dates) # most recent commit
                                    if processed_yaml: # if the MANIFEST file existed
                                        new_oots.append(Outoftreemodule(name = giturl.split('/')[1].replace('-','‑'), # people kept giving their stuff long titles, it worked out better to just use their github project url. also, i replace the standard hyphen with a non-line-breaking hyphen =)
                                                                        tags = ", ".join(processed_yaml['tags']), 
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
                                                                        author = ['None'],
                                                                        dependencies = ['None'],
                                                                        copyright_owner = ['None'],
                                                                        icon = 'None',
                                                                        website = 'None',
                                                                        body_text = body_text))                                                        
                                
                        except yaml.YAMLError:
                            print(giturl, "had error parsing MANIFEST yaml")
                            print(' ')
                        

    # clear table
    Outoftreemodule.objects.all().delete()
    # all the new objects to db
    for new_oot in new_oots:
        new_oot.save() # adds to db
                                    
    table = OutoftreemoduleTable(Outoftreemodule.objects.all(), order_by=("status", "name"))
    RequestConfig(request, paginate={'per_page': 100}).configure(table)
    return render(request, 'ootlist/index.html', {'table': table})
