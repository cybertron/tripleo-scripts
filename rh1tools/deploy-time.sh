#!/bin/bash

#openstack stack event list -f json --nested-depth 5 $1 | ./heat-deploy-times.py
openstack stack event list -f json $1 | ./heat-deploy-times.py
