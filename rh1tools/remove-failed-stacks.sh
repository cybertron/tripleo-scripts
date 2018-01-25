#!/bin/bash

# For some reason stacks occasionally get stuck in a DELETE_FAILED state.
# We need to run the cleanup-stack script on these to remove them.

. /home/heat-admin/rh1nodepool
for i in `heat stack-list -f stack_status=DELETE_FAILED | awk '{print $4}' | grep baremetal`; do ./cleanup-stack ${i#baremetal_}; done
