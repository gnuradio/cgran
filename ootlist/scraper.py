import urllib.request
import subprocess
import os
import shutil
import yaml # yaml parser
from io import StringIO # allows strings to be converted to file object type things
import re
from dateutil.parser import isoparse
import mistune # markdown parser
from ootlist.models import Outoftreemodule
from ootlist.models import Packageversion
from socket import gaierror
import requests
import logging

def scrape():
    print("RUNING SCRAPER")
    
    # pull versions of gnuradio in ubuntu packages
    Packageversion.objects.all().delete() # clear out the table
    ubuntu20 = 'https://packages.ubuntu.com/focal/gnuradio'
    ubuntu22 = 'https://packages.ubuntu.com/jammy/gnuradio'
    ubuntus = [(ubuntu20, 'Ubuntu-20.04'), (ubuntu22, 'Ubuntu-22.04')]
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
        # TODO: In addition of checking if the URL is alive, check if it only contains a supported image
        icon = '/static/ootlist/images/cgran_no_logo.png'
        if url:
            try:
                code = requests.get(url).status_code
                if code == requests.codes.ok:
                    icon = url
            except (OSError, gaierror) as err:
                print("    Invalid logo URL")
                pass
        return icon

    # who needs bash!
    shutil.rmtree('gr-recipes', ignore_errors=True)  # remove directory gr-recipes
    shutil.rmtree('gr-etcetera', ignore_errors=True) # remove directory gr-etcetera
    git("clone", 'https://github.com/gnuradio/gr-recipes.git') # clone repo
    git("clone", 'https://github.com/gnuradio/gr-etcetera.git') # clone repo

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
        gitbranch = recipe_yaml.get("gitbranch", "master") # github will redirect master to main automatically, but not vice versa
        giturl = recipe_yaml.get("mirror", None) # check if there's a mirror specified, this is used when the main repo isnt through github
        if not giturl:
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
            full_url = 'https://raw.githubusercontent.com/' + giturl + '/' + gitbranch + '/MANIFEST.md'
            f = urllib.request.urlopen(full_url)
            manifest = f.read().decode('utf-8') # this converts it from a byte object to a python string
        except:
            print("    MANIFEST file missing, or it wasn't a github URL")
            manifest = '' # this will cause the fields to be blank but it will still get listed
        indx3 = manifest.find('---') # this bar separates header from "body_text"
        top_yaml = StringIO(manifest[:indx3]) # annoying step, pyyaml wants a file object but i already have it in a string, so i wrap the string as a file object
        body_text = mistune.html(manifest[indx3+3:]) # grab everything after the bar, and run it through markdown parser
        
        # parse yaml, creates dict, extract what we want
        try:
            processed_yaml = yaml.safe_load(top_yaml)
            try:
                """
                Just ask the github API for the newest commit. No HTML parsing required.

                This is how you do it using curl and jq:
                ```shell
                curl -L \
                -H "Accept: application/vnd.github+json" \
                -H "X-GitHub-Api-Version: 2022-11-28" \
                "https://api.github.com/repos/OWNER/REPO/commits?per_page=1" \
                | jq '.[0].commit.author.date'
                ```
                """
                response = requests.get(f"https://api.github.com/repos/{giturl}/commits?per_page=1",
                                        headers={
                                            "X-GitHub-Api-Version": "2022-11-28",
                                            "Accept": "application/vnd.github+json"
                                        },
                                        allow_redirects=True
                                        )
                try:
                    commit_date = isoparse(response.json()[0]["commit"]["author"]["date"])
                except Exception as e:
                    logging.warn(f"Failed to extract latest commit from response for {giturl}")
                    raise e
            except Exception as e:
                logging.warn(f"Failed to get latest commit:\n{e}\nSetting None")
                commit_date = None

            if processed_yaml:  # if the MANIFEST file existed
                supported_version = processed_yaml.get('gr_supported_version', '')
                if isinstance(supported_version, list):
                    supported_version = ','.join(supported_version)
                deps = processed_yaml.get('dependencies', ['None'])
                if deps:
                    if isinstance(deps, list):
                        deps = ", ".join(deps)
                else:
                    deps = 'None'
                new_oots.append(Outoftreemodule(name = giturl.split('/')[1].replace('-','‑'), # people kept giving their stuff long titles, it worked out better to just use their github project url. also, i replace the standard hyphen with a non-line-breaking hyphen =)
                                                tags = ", ".join(processed_yaml.get('tags',['None'])),
                                                description = processed_yaml.get('brief', 'None'),
                                                repo = 'https://github.com/' + giturl, # use repo from lwr instead of that provided in manifest
                                                last_commit = commit_date,
                                                author = ", ".join(processed_yaml.get('author', ['None'])),
                                                dependencies = deps,
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
        except Exception as e:
            print(e)

    # clear table
    Outoftreemodule.objects.all().delete()
    # all the new objects to db
    for new_oot in new_oots:
        new_oot.save() # adds to db


