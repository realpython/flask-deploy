###############
### imports ###
###############

from fabric.api import run, cd, env, lcd, put, prompt, local
from fabric.contrib.files import exists


##############
### config ###
##############

local_app_dir = './flask_project'
local_config_dir = './config'

remote_app_dir = '/home/www'
remote_flask_dir = remote_app_dir + '/flask_project'
remote_nginx_dir = '/etc/nginx/sites-enabled'
remote_supervisor_dir = '/etc/supervisor/conf.d'

env.hosts = ['ADD_IP/DOMAIN_HERE']  # replace with IP address or hostname
env.user = 'root'
# env.password = 'password'


#############
### tasks ###
#############

def install_requirements():
    """ Install required packages. """
    run('apt-get update')
    run('apt-get install -y python')
    run('apt-get install -y python-pip')
    run('apt-get install -y python-virtualenv')
    run('apt-get install -y nginx')
    run('apt-get install -y gunicorn')
    run('apt-get install -y supervisor')
    run('apt-get install -y git')


def install_flask():
    """
    1. Create project directories
    2. Create and activate a virtualenv
    3. Copy Flask files to remote host
    """
    if exists(remote_app_dir) is False:
        run('mkdir ' + remote_app_dir)
    if exists(remote_flask_dir) is False:
        run('mkdir ' + remote_flask_dir)
    with lcd(local_app_dir):
        with cd(remote_app_dir):
            run('virtualenv env')
            run('source env/bin/activate')
            run('pip install Flask==0.10.1')
        with cd(remote_flask_dir):
            put('*', './')


def configure_nginx():
    """
    1. Remove default nginx config file
    2. Create new config file
    3. Setup new symbolic link
    4. Copy local config to remote config
    5. Restart nginx
    """
    run('/etc/init.d/nginx start')
    if exists('/etc/nginx/sites-enabled/default'):
        run('rm /etc/nginx/sites-enabled/default')
    if exists('/etc/nginx/sites-enabled/flask_project') is False:
        run('touch /etc/nginx/sites-available/flask_project')
        run('ln -s /etc/nginx/sites-available/flask_project' +
            ' /etc/nginx/sites-enabled/flask_project')
    with lcd(local_config_dir):
        with cd(remote_nginx_dir):
            put('./flask_project', './')
    run('/etc/init.d/nginx restart')


def configure_supervisor():
    """
    1. Create new supervisor config file
    2. Copy local config to remote config
    3. Register new command
    """
    if exists('/etc/supervisor/conf.d/flask_project.conf') is False:
        with lcd(local_config_dir):
            with cd(remote_supervisor_dir):
                put('./flask_project.conf', './')
                run('supervisorctl reread')
                run('supervisorctl update')


def configure_git():
    """
    1. Setup bare Git repo
    2. Create post-receive hook
    """
    if exists('/' + env.user + '/flask_project.git') is False:
        with cd('/' + env.user):
            run('mkdir flask_project.git')
            with cd('flask_project.git'):
                run('git init --bare')
                with lcd(local_config_dir):
                    with cd('hooks'):
                        put('./post-receive', './')
                        run('chmod +x post-receive')


def run_app():
    """ Run the app! """
    with cd(remote_flask_dir):
        run('supervisorctl start flask_project')


def deploy():
    """
    1. Copy new Flask files
    2. Restart gunicorn via supervisor
    """
    with lcd(local_app_dir):
        local('git add -A')
        commit_message = prompt("Commit message?")
        local('git commit -am "{0}"'.format(commit_message))
        local('git push production master')
        run('supervisorctl restart flask_project')


def rollback():
    """
    1. Quick rollback in case of error
    2. Restart gunicorn via supervisor
    """
    with lcd(local_app_dir):
        local('git revert master  --no-edit')
        local('git push production master')
        run('supervisorctl restart flask_project')


def status():
    """ Is our app live? """
    run('supervisorctl status')


def create():
    install_requirements()
    install_flask()
    configure_nginx()
    configure_supervisor()
    configure_git()
