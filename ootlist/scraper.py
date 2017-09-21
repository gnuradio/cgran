import urllib
import subprocess
import os
import shutil
import yaml
from cStringIO import StringIO
import re
import datetime

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
                    print manifest[:indx3]
                    try:
                        processed_yaml = yaml.safe_load(f2) 
                        print i
                        i += 1
                        print processed_yaml.get('author', 'None')
                        print processed_yaml.get('title', 'None')
                        print processed_yaml.get('tags', 'None')
                        print processed_yaml.get('brief', 'None')
                        print processed_yaml.get('repo', 'None')
                        print processed_yaml.get('dependencies', 'None')
                        print processed_yaml.get('copyright_owner', 'None')
                        print processed_yaml.get('icon', 'None')
                        print processed_yaml.get('website', 'None')
                        
                        # fetch branches page of github to find the most recent commit
                        f = urllib.urlopen('https://github.com/' + giturl + '/branches') 
                        branch_page = f.read()   
                        updateds = [m.start() for m in re.finditer('time-ago datetime=', branch_page)]
                        dates = []
                        for updated in updateds:
                            date = branch_page[updated+19:updated+29] # pull out date in year-mn-dy format
                            dates.append(datetime.date(int(date[0:4]), int(date[5:7]), int(date[8:10]))) # parse out year/month/day  
                        print max(dates) # most recent commit
                    
                        print ' '
                        
                    except yaml.YAMLError, exc:
                        print giturl, "had error parsing MANIFEST yaml:", exc
                        print ' '

                     
                    
                        
                    
                    
