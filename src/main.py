#!/usr/bin/env python2.7
#-*- coding: utf-8 -*-

import sys
import jenkins
import json

import requests
from requests.auth import HTTPBasicAuth

# config object
config = None;

API_SET_NEXT_BUILD_NUMBER = 'nextbuildnumber/submit'

def buildSetNextBuildNumberRequestUrl(instance, job_name, number, user, token):
    job = instance.get_job_info(job_name)
    url = "{}{}".format(
            job['url'],
            API_SET_NEXT_BUILD_NUMBER)
    data = {'nextBuildNumber': number}

    print 'Set next build number to ', number

    response = requests.post(
            url, auth=HTTPBasicAuth(user, token),
            data=data)

    if response.status_code != 200:
        print 'Set next build number failed. code=', response.status_code

def loadJSONConfig(path = './config.json'):
    global config;

    f = open(path, 'r')
    try:
        config = json.load(f)
    except ValueError:
        print 'JSON file format error'

    f.close()
    return config

def get_jenkins_instance(address, user, password):
    try:
        instance = jenkins.Jenkins(address, user, password)
    except:
        print 'Get Jenkins instance failed.'
        return None
    return instance

def buildJob(instance, job_name):
    try:
        instance.build_job(job_name)
    except:
        return False
    return True

def createJob(instance, job_name, configXML):
    try:
        instance.create_job(job_name, configXML)
    except jenkins.JenkinsException as e:
        print e.message.encode('utf-8')
        return False
    return True

def cloneJob(srcInstance, destInstance, job_name):
    try:
        configXML = srcInstance.get_job_config(job_name)
    except jenkins.JenkinsException as e:
        print e.message.encode('utf-8')
        return False
    return createJob(destInstance, job_name, configXML)

def show_job_info(instance, job_name):
    job = instance.get_job_info(job_name)
    print(u'Name:{}\nDescription:{}\n'.format(
        job_name,
        job['description']).encode('utf-8'))

def show_jenkins_server_info(instance):
    try:
        print "User:{}\nVersion:{}\n".format(
            instance.get_whoami(), instance.get_version(), instance.jobs_count())
    except jenkins.JenkinsException as e:
        print e.message.encode('utf-8')

def retrieveJobBuilds(instance, job_name):
    job = instance.get_job_info(job_name)
    return job['builds']

def cloneJobBuilds(srcInstance, destInstance, job_name):

    # check job is existed
    try:
        job = srcInstance.get_job_info(job_name)
    except jenkins.JenkinsException as e:
        print e.message.encode('utf-8')
        return

    result = cloneJob(srcInstance, destInstance, job_name)
    if result is False:
        print('clone job failed')
    else:
        print('clone job success')

    # retrieve builds and create build
    builds = retrieveJobBuilds(srcInstance, job_name)

    # set the build number then trigger build
    for build in builds:
        print 'trigger build: build number:{}'.format(build['number'] + 1)
        buildSetNextBuildNumberRequestUrl(
            destInstance, job_name, build['number'] + 1, config['user'], config['dest_token'])
        val = buildJob(destInstance, job_name)
        if val is False:
            print('{} build failed ignore'.format(job_name))
            return

def handle(srcInstance, destInstance, job_name):
    
    existed = False

    print('retrieve src builds')
    src_builds = retrieveJobBuilds(srcInstance, job_name)
    if len(src_builds) == 0:
        print('No build existed, ignore')
        return

    #check dest has the same job name
    try:
        job = destInstance.get_job_info(job_name)
        existed = True
    except jenkins.JenkinsException as e:
        print e.message.encode('utf-8')

    if existed is True:
        print('dest jenkins has the same job {}, retrieve dest build'.format(job_name))
        dest_builds = retrieveJobBuilds(destInstance, job_name)

        max_build_num = -1
        for build in dest_builds:
            if build['number'] > max_build_num:
                max_build_num = build['number']
        print('dest maximum build number:', max_build_num)

        the_first_build = src_builds[0]
        new_number = the_first_build['number'] + 20 

        if new_number < max_build_num: 
            print('src build number + 20 {} < dest max build number, ignore job'.format(new_number))
            return

        if max_build_num == -1:
            print('dest no build existed')
    else:
        print('clone job')
        result = cloneJob(srcInstance, destInstance, job_name)

        if result is False:
            print('{} clone job failed, handle next'.format(job_name))
            return
        else:
            print('clone job success')

    print('start build')
    for build in src_builds:
        old_number = build['number']
        new_number = old_number + 20 
        print('start build: {} -> {}'.format(old_number, new_number))

        buildSetNextBuildNumberRequestUrl(
            destInstance, job_name, new_number, config['user'], config['dest_token'])
        buildJob(destInstance, job_name)

if __name__ == '__main__':
    config = loadJSONConfig()

    srcInstance = get_jenkins_instance(
            config['src_server'], config['user'], config['src_token'])

    show_jenkins_server_info(srcInstance)

    jobs = srcInstance.get_jobs()
    print('job number:', len(jobs))

    for job in jobs:
        name = job['fullname']
        show_job_info(srcInstance, name)
