import urllib.request
import subprocess
import os
import shutil
import yaml # yaml parser
from io import StringIO # allows strings to be converted to file object type things
import re
import datetime
import mistune # markdown parser
from ootlist.models import Outoftreemodule
from ootlist.models import Packageversion
from django.utils.dateparse import parse_datetime
from socket import gaierror
import requests
from django.core.management.base import BaseCommand, CommandError

# You run this code using python manage.py refresh, e.g. in a cronjob

class Command(BaseCommand): # must be called command, use file name to name the functionality
    def handle(self, *args, **options):
        print("RUNING SCRAPER") # FIXME get this code pulled out into another filed called scraper.py
        
        # pull versions of gnuradio in ubuntu packages
        Packageversion.objects.all().delete() # clear out the table
        ubuntu16 = 'https://packages.ubuntu.com/xenial/gnuradio'
        ubuntu18 = 'https://packages.ubuntu.com/bionic/gnuradio'
        #ubuntu19 = 'https://packages.ubuntu.com/eoan/gnuradio'
        ubuntu20 = 'https://packages.ubuntu.com/focal/gnuradio'
        #ubuntus = [(ubuntu16, 'Ubuntu-16.04'), (ubuntu18, 'Ubuntu-18.04'), (ubuntu19, 'Ubuntu-19.10'), (ubuntu20, 'Ubuntu-20.04')]
        ubuntus = [(ubuntu16, 'Ubuntu-16.04'), (ubuntu18, 'Ubuntu-18.04'), (ubuntu20, 'Ubuntu-20.04')]
        for ubuntu in ubuntus:
            print(ubuntu)
            response = urllib.request.urlopen(ubuntu[0])
            html = response.read().decode('utf-8')
            indx = html.find('Package: gnuradio')
            indx2 = html[indx:].find('-')
            version_string = html[indx+19:indx+indx2]
            print(version_string)
            new_packageversion = Packageversion(os_name = ubuntu[1], gr_version_string = version_string)
            new_packageversion.save() # add to db

        def git(*args):
            return subprocess.check_call(['git'] + list(args))

        def validate_icon_URL(url):
            """
            checks if an icon URL is provided and validates the http
            request. If validation succeds, the provided URL is set to
            the icon. otherwise, a default no-logo image is propagated.
            """
            # TODO: In addition of checking if the URL is alive, check
            # if it only contains a supported image
            icon = '/static/ootlist/images/cgran_no_logo.png'
            if url:
                try:
                    code = requests.get(url).status_code
                    if code == requests.codes.ok:
                        icon = url
                except (OSError, gaierror) as err:
                    print("*** Invalid logo URL")
                    pass
            return icon

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
            if '.lwr' not in recipe:
                continue
            if recipe in blacklist:
                continue
            # Read the lwr file
            print(recipe)
            with open(recipe) as ff:
                recipe_yaml = yaml.safe_load(ff)
            # Pull out github URL
            gitbranch = recipe_yaml.get("gitbranch", "master") # some use main instead of master
            giturl = recipe_yaml.get("source", None)
            if not giturl:
                print("    No source entry in Manifest")
                continue
            giturl = giturl.replace('git+https://github.com/', '') # remove the first portion
            giturl = giturl.replace('https://github.com/', '') # in case git+ wasn't provided
            giturl = giturl.replace('.git','') # remove the .git that most of them have at the end
            giturl = giturl.replace('#','') # the pound symbol will cause an error with urllib's request
            giturl = giturl.replace('/releases/download/v2.6.1/protobuf-2.6.1.tar.gz','') # the protobufs recipe is a weird one
            
            # Pull down and read the MANIFEST file
            try: # a good chunk of OOTs dont have this file
                f = urllib.request.urlopen('https://raw.githubusercontent.com/' + giturl + '/' + gitbranch + '/MANIFEST.md')
                manifest = f.read().decode('utf-8') # this converts it from a byte object to a python string
            except:
                print("    MANIFEST file missing, or it wasn't a github URL")
                manifest = '' # this will cause the fields to be blank but it will still get listed
            indx3 = manifest.find('---') # this bar separates header from "body_text"
            f2 = StringIO(manifest[:indx3]) # annoying step, pyyaml wants a file object but i already have it in a string, so i wrap the string as a file object
            md = mistune.Markdown() # at some point they changed the way Markdown objects work
            body_text = md.parse(manifest[indx3+3:]) # grab everything after the bar, and run it through markdown parser
            
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
                if not dates: # if dates is empty its an indication the URL was broken so the OOT doesn't get added to the list
                    continue
                commit_date = max(dates) # most recent commit
                if processed_yaml: # if the MANIFEST file existed
                    supported_version = processed_yaml.get('gr_supported_version', '')
                    if supported_version:
                        supported_version.replace("'","").replace("[","").replace("]","")
                    new_oots.append(Outoftreemodule(name = giturl.split('/')[1].replace('-','‑'), # people kept giving their stuff long titles, it worked out better to just use their github project url. also, i replace the standard hyphen with a non-line-breaking hyphen =)
                                                    tags = ", ".join(processed_yaml.get('tags',['None'])),
                                                    description = processed_yaml.get('brief', 'None'),
                                                    repo = 'https://github.com/' + giturl, # use repo from lwr instead of that provided in manifest
                                                    last_commit = commit_date,
                                                    author = ", ".join(processed_yaml.get('author', ['None'])),
                                                    dependencies = ", ".join(processed_yaml.get('dependencies', ['None'])),
                                                    copyright_owner = ", ".join(processed_yaml.get('copyright_owner', ['None'])),
                                                    icon = validate_icon_URL(processed_yaml.get('icon', '')),
                                                    website = processed_yaml.get('website', 'None'),
                                                    gr_supported_version = supported_version,
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
                                                    icon = validate_icon_URL(''),
                                                    website = 'None',
                                                    gr_supported_version = '',
                                                    body_text = body_text))
            except yaml.YAMLError:
                print("   ", giturl, "had error parsing MANIFEST yaml")
            except urllib.error.HTTPError:
                print('    error opening up the branches page of recipe: ' + recipe)

        # Go through and manually add a bunch of OOTs that do not use github
        new_oots.append(Outoftreemodule(name = 'gr-iqbal'.replace('-','‑'), # people kept giving their stuff long titles, it worked out better to just use their github project url. also, i replace the standard hyphen with a non-line-breaking hyphen =)
                                        tags = ", ".join(['iq imbalance','rx','osmocom']),
                                        description = 'GNU Radio block to correct IQ imbalance in quadrature receivers',
                                        repo = 'git://git.osmocom.org/gr-iqbal',
                                        last_commit = parse_datetime('2019-12-04 11:47:58'),
                                        author = 'Sylvain Munaut <tnt@246tNt.com>',
                                        dependencies = 'None',
                                        copyright_owner = 'Sylvain Munaut <tnt@246tNt.com>',
                                        icon = 'http://people.osmocom.org/~tnt/stuff/iqbal-icon.png',
                                        website = 'None',
                                        gr_supported_version = 'v3.7, v3.8',
                                        body_text = ' '))

        new_oots.append(Outoftreemodule(name = 'gr-fosphor'.replace('-','‑'), # people kept giving their stuff long titles, it worked out better to just use their github project url. also, i replace the standard hyphen with a non-line-breaking hyphen =)
                                        tags = ", ".join(['fft','gpu','opencl','opengl']),
                                        description = 'GNU Radio block for RTSA-like spectrum visualization using OpenCL and OpenGL acceleration',
                                        repo = 'git://git.osmocom.org/gr-fosphor',
                                        last_commit = parse_datetime('2019-12-08 11:47:58'),
                                        author = 'Sylvain Munaut <tnt@246tNt.com>',
                                        dependencies = 'None',
                                        copyright_owner = 'Sylvain Munaut <tnt@246tNt.com>',
                                        icon = 'http://people.osmocom.org/~tnt/stuff/fosphor-icon.png',
                                        website = 'None',
                                        gr_supported_version = 'v3.7, v3.8',
                                        body_text = ' '))

        # clear table
        Outoftreemodule.objects.all().delete()
        # all the new objects to db
        for new_oot in new_oots:
            new_oot.save() # adds to db

