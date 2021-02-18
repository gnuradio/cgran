<p align="center">
  <img src="https://raw.githubusercontent.com/gnuradio/cgran/master/ootlist/static/ootlist/images/cgran_logo_v2.png" width="250"/>
</p>

#### This is the Django web app for CGRAN.org

#### The information in the main table is automatically generated by parsing gr-recipes and gr-etcetera (PyBOMBS recipes).

### To Install
* clone this repo
* install docker-ce with https://docs.docker.com/install/linux/docker-ce/ubuntu/#install-docker-ce
* install docker-compose with https://docs.docker.com/compose/install/#prerequisites
* allow running docker as non-root with https://docs.docker.com/install/linux/linux-postinstall/#manage-docker-as-a-non-root-user
* rename settings_secret.py.template to settings_secret.py and change the value of the secret key to something else (anything else)
* create a cronjob on the server running the docker container
  1. `crontab -e`
  2. `0 1 * * * docker exec -ti cgran_cgran_web_1 /bin/sh -c "python manage.py refresh"`

### To launch app

`docker-compose up --build --no-deps`

or

`docker-compose up`

### Notepad to self

* For shell accessing- `docker exec -ti nginx bash` or `docker exec -ti web bash` 
* `docker ps` lists docker containers that are running
* `docker ps -a` lists all built containers
* you can stop and remove all docker containers using `docker stop $(docker ps -a -q)` then `docker rm $(docker ps -a -q)`
* three-step guide to making model changes:
  1. Change your models (in models.py).
  2. Run python manage.py makemigrations to create migrations for those changes
  3. Run python manage.py migrate to apply those changes to the database.
* save db to yaml file- `python manage.py dumpdata --format yaml ootlist.Outoftreemodule -o db.yaml`
* load yaml file to db- `python manage.py loaddata db.yaml` 
