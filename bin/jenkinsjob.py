#!/usr/bin/env python
#
# Copyright 2015-2015 Ghent University
#
# This file is part of vsc-base,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://vscentrum.be/nl/en),
# the Hercules foundation (http://www.herculesstichting.be/in_English)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# https://github.com/hpcugent/vsc-base
#
# vsc-base is free software: you can redistribute it and/or modify
# it under the terms of the GNU Library General Public License as
# published by the Free Software Foundation, either version 2 of
# the License, or (at your option) any later version.
#
# vsc-base is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU Library General Public License
# along with vsc-base. If not, see <http://www.gnu.org/licenses/>.
#
"""

This is a helper script to help you create new jenkins jobs
This is very much tailered to vsc-* jobs on the jenkins1.ugent.be jenkins instance

It needs a jenkins url, username, api token which can be configured in a config file, or given on the command line
ype: text/xml"

@author: Jens Timmerman (Ghent University)
"""
import urllib2
import base64

from datetime import datetime

from vsc.utils.generaloption import simple_option

"""
Jenkins  API from
https://benkiew.wordpress.com/2012/01/12/automating-hudsonjenkins-via-rest-and-curl-a-very-small-cookbook


#Get the current configuration and save it locally
curl -X GET http://user:password@hudson.server.org/job/myjobname/config.xml -o mylocalconfig.xml

#Update the configuration via posting a local configuration file
curl -X POST http://user:password@hudson.server.org/job/myjobname/config.xml --data-binary "@mymodifiedlocalconfig.xml"

#Creating a new job via posting a local configuration file
curl -X POST "http://user:password@hudson.server.org/createItem?name=newjob" --data-binary "@newcfg.xml" -H "Content-Type: Text/xml"

"""

PR_BUILDER_SUFFIX = '-prbuilder'
# replaces PROJECT_TEMPLATE with e.g. vsc-install
PROJECT_TEMPLATE = 'PROJECT_TEMPLATE'
# replaces PROJECT_DOT_TEMPLATE with vsc.install
PROJECT_DOT_TEMPLATE = 'PROJECT_DOT_TEMPLATE'
# replaces PROJECT_SLASH_TEMPLATE with vsc/install
PROJECT_SLASH_TEMPLATE = 'PROJECT_SLASH_TEMPLATE'

# dict = {longopt:(help_description,type,action,default_value,shortopt),}
options = {
    'instance':('Url to jenkins instance', None, 'store', 'https://jenkins1.ugent.be', 'i'),
    'user':('user on the jenkins instance', None, 'store', 'hpc', 'n'),
    'token':(
        "api token for this user on the jenkins instance."
        "You can find tokens at e.g. https://jenkins1.ugent.be/user/hpc/configure",
        None,
        'store',
        None,
        't',
    ),
    'githubtoken':(
        "api token for the github machine user on the github instance."
        "You can find tokens at e.g. https://jenkins1.ugent.be/user/hpc/configure",
        None,
        'store',
        None,
    ),
    'config':(
        'config.xml to use as template for this new job',
        None,
        'store',
        'config.xml',
        'c',
    ),
    'prconfig':(
        'config.xml to use as template for the pull request builder this new job',
        None,
        'store',
        'pr-config.xml',
        'p',
    ),

    # TODO: make this a list, so we can update 100's of jobs at once?
    # TODO: make this an url to a github project, so we can find the api and query it (e.g. private github intances)
    'githubproject':('github project for this new jenkins job', None, 'store', None, 'g'),
    'jobname':('name for this new jenkins job', None, 'store', None, 'j'),
    'update':('update an existing job instead of create a new', None, 'store_true', False, 'u'),
}




go = simple_option(options)

go.log.debug("using options %s", go.options)


#TODO: check if githubproject really exists using github api
#TODO: Get project description using github api
#TODO:  set github pr-builder webhook using github api
#TODO:  set github web service webhook using github api
#TODO: if project is private, don't give anonymous view rights
#TODO: if project is private, we need hpcugentbot credentials (key's) generated on jenkins, and public key set on github
#TODO: give hpcugentbot write access to repo, so he can set build status, and we're sure he can pull the repo
#TODO set upstream vsc-* projects based on dependencies.


def send_config(instance, project, update, xml, user, token, suffix=''):

    authdata = base64.encodestring('%s:%s' % (user, token)).replace('\n', '')
    if update:
        url = go.options.instance + '/job/' + project + suffix + '/config.xml'
        go.log.debug('url: %s', url)
        # save original config.xml so we don't accedentaly lose things
        req = urllib2.Request(url)
        req.add_header('Authorization', 'Basic %s' % authdata)
        handle = urllib2.urlopen(req)
        filename = 'orig%s_config.xml.%s' % (suffix, datetime.now())
        open(filename, 'w').write(handle.read())
        go.log.info('saved original config.xml to %s', filename)
    else:
        prbuilderurl = instance +  '/createItem?name=' + project + suffix

    req = urllib2.Request(prbuilderurl, data=xml)
    req.add_header('Content-Type', 'Text/xml')
    req.add_header('Authorization', 'Basic %s' % authdata)

    go.log.debug('going to perform request %s', req)
    handle = urllib2.urlopen(req)
    response = handle.read()
    go.log.debug('response: %s', response)


def get_templated_data(xmltemplate, projectname):
    """
    Returns the xml data with the correct templates in it
    """
    data = open(xmltemplate).read()
    mapping = [
        (PROJECT_TEMPLATE, projectname),
        (PROJECT_DOT_TEMPLATE, projectname.replace('-', '.')),
        (PROJECT_SLASH_TEMPLATE, projectname.replace('-', '/')),
    ]
    for template, replaced in mapping:
        data = data.replace(template, replaced)
    return data

#create jenkins pr builder project
#<github-project>-pr-builder


opts = go.options
prbuilddata = get_templated_data(opts.prconfig, opts.githubproject)
go.log.debug('xml data: %s', prbuilddata)
send_config(opts.instance, opts.githubproject, opts.update, prbuilddata, opts.user, opts.token, PR_BUILDER_SUFFIX)


#TODO: create jenkins project for master
#<github-project>
data = get_templated_data(opts.config, opts.githubproject)
go.log.debug('xml data: %s', data)
send_config(opts.instance, opts.githubproject, opts.update, data, opts.user, opts.token)


#TODO show public jobs in vsc-tools dashboard
#TODO show pr builders in https://jenkins1.ugent.be/view/pull-request-builder/configure
