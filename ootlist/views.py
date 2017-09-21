# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
from django.template import loader
from django_tables2 import RequestConfig
from django.shortcuts import redirect

from .models import Outoftreemodule
from .tables import OutoftreemoduleTable

def index(request):
    table = OutoftreemoduleTable(Outoftreemodule.objects.all(), order_by=("-last_commit"))
    RequestConfig(request, paginate={'per_page': 100}).configure(table)
    return render(request, 'ootlist/index.html', {'table': table})

def submit(request):
    return render(request, 'ootlist/submit.html')
    
def refresh(request):
    print "RUNING SCRAPER" # FIXME get this code pulled out into another filed called scraper.py
    import urllib
    import subprocess
    import os
    import shutil
    import yaml
    from cStringIO import StringIO
    import re
    import datetime

    # get around unicode error because of symbols in peoples names
    import sys
    reload(sys)
    sys.setdefaultencoding('utf-8')

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
    i = 0
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
                    giturl = doc[indx+31:indx+indx2]
                    f = urllib.urlopen('https://raw.githubusercontent.com/' + giturl + '/master/MANIFEST.md')
                    manifest = f.read()
                    indx3 = manifest.find('---')
                    f2 = StringIO(manifest[:indx3]) # annoying step, pyyaml wants a file object but i already have it in a string, so i wrap the string as a file object
                    if indx3 != -1:
                        # parse yaml, creates dict, extract what we want
                        try:
                            processed_yaml = yaml.safe_load(f2) 
                            print giturl
                            i += 1
                            #print processed_yaml.get('author', 'None')
                            #print processed_yaml.get('dependencies', 'None')
                            #print processed_yaml.get('copyright_owner', 'None')
                            #print processed_yaml.get('icon', 'None')
                            #print processed_yaml.get('website', 'None')
                            

                            
                            # fetch branches page of github to find the most recent commit
                            f = urllib.urlopen('https://github.com/' + giturl + '/branches') 
                            branch_page = f.read()   
                            updateds = [m.start() for m in re.finditer('time-ago datetime=', branch_page)]
                            dates = []
                            for updated in updateds:
                                date = branch_page[updated+19:updated+29] # pull out date in year-mn-dy format
                                dates.append(datetime.date(int(date[0:4]), int(date[5:7]), int(date[8:10]))) # parse out year/month/day  
                            commit_date = max(dates) # most recent commit

                            new_oots.append(Outoftreemodule(name = processed_yaml.get('title', 'None'),
                                                            tags = ", ".join(processed_yaml.get('tags', 'None')), 
                                                            description = processed_yaml.get('brief', 'None'), 
                                                            repo = 'https://github.com/' + giturl, # use repo from lwr instead of that provided in manifest 
                                                            last_commit = commit_date,
                                                            author = processed_yaml.get('author', 'None'),
                                                            dependencies = processed_yaml.get('dependencies', 'None'),
                                                            copyright_owner = processed_yaml.get('copyright_owner', 'None'),
                                                            icon = processed_yaml.get('icon', 'None'),
                                                            website = processed_yaml.get('website', 'None')))                    
                            
                        except yaml.YAMLError, exc:
                            print giturl, "had error parsing MANIFEST yaml:", exc
                            print ' '

    # clear table
    Outoftreemodule.objects.all().delete()
    # all the new objects to db
    for new_oot in new_oots:
        new_oot.save() # adds to db
                                    
    table = OutoftreemoduleTable(Outoftreemodule.objects.all(), order_by=("status", "name"))
    RequestConfig(request, paginate={'per_page': 100}).configure(table)
    return render(request, 'ootlist/index.html', {'table': table})
