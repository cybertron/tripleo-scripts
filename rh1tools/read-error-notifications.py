#!/usr/bin/env python

# Extremely simple script to consume error notifications from rabbitmq.
# This serves two purposes - it clears the queue when it gets full of
# notifications (there's nothing else listening on that queue in our
# environment) and it allows us to view details of the notifications to
# see what is causing the errors.
#
# It is probably best to send the output to a file in case there are a large
# number of error notifications to be read.

import json
import time

import pika

fake_message1 = {"oslo.message": "{\"_context_domain\": null, \"_context_roles\": [\"_member_\"], \"_context_quota_class\": null, \"event_type\": \"compute.instance.create.error\", \"_context_request_id\": \"req-7fda1731-c9b4-46e3-8f03-5aca4aee4193\", \"_context_service_catalog\": [{\"endpoints\": [{\"adminURL\": \"http://192.168.112.42:8776/v2/b79291658f384b7ebbc9019b6349e5c9\", \"region\": \"regionOne\", \"internalURL\": \"http://192.168.112.42:8776/v2/b79291658f384b7ebbc9019b6349e5c9\", \"publicURL\": \"https://ci-overcloud.rh1.tripleo.org:13776/v2/b79291658f384b7ebbc9019b6349e5c9\"}], \"type\": \"volumev2\", \"name\": \"cinderv2\"}, {\"endpoints\": [{\"adminURL\": \"http://192.168.112.42:8776/v1/b79291658f384b7ebbc9019b6349e5c9\", \"region\": \"regionOne\", \"internalURL\": \"http://192.168.112.42:8776/v1/b79291658f384b7ebbc9019b6349e5c9\", \"publicURL\": \"https://ci-overcloud.rh1.tripleo.org:13776/v1/b79291658f384b7ebbc9019b6349e5c9\"}], \"type\": \"volume\", \"name\": \"cinder\"}], \"timestamp\": \"2017-03-22 14:46:26.693147\", \"_context_user\": \"ba119eef29ce49f5b8697f4d63948e3c\", \"_unique_id\": \"2d49abb704914218adc919a00391ae85\", \"_context_resource_uuid\": null, \"_context_instance_lock_checked\": false, \"_context_user_id\": \"ba119eef29ce49f5b8697f4d63948e3c\", \"payload\": {\"state_description\": \"spawning\", \"code\": 500, \"availability_zone\": null, \"terminated_at\": \"\", \"ephemeral_gb\": 0, \"instance_type_id\": 17, \"message\": \"OVS configuration failed with: Unexpected error while running command.\\nCommand: sudo nova-rootwrap /etc/nova/rootwrap.conf ovs-vsctl --timeout=120 -- --if-exists del-port qvob1804d96-30 -- add-port br-int qvob1804d96-30 -- set Interface qvob1804d96-30 ext\", \"deleted_at\": \"\", \"reservation_id\": \"r-uehjblho\", \"instance_id\": \"2a15ac18-abe3-49a7-80d6-d96acf90f622\", \"display_name\": \"baremetal-41522_1\", \"hostname\": \"baremetal-41522-1\", \"state\": \"building\", \"progress\": \"\", \"launched_at\": \"\", \"metadata\": {}, \"node\": \"overcloud-novacompute-20.localdomain\", \"ramdisk_id\": \"\", \"access_ip_v6\": null, \"disk_gb\": 41, \"access_ip_v4\": null, \"kernel_id\": \"\", \"host\": \"overcloud-novacompute-20.localdomain\", \"user_id\": \"ba119eef29ce49f5b8697f4d63948e3c\", \"image_ref_url\": \"http://192.168.112.64:9292/images/07fada8a-e3bd-43f3-a2b9-6b96626d0891\", \"cell_name\": \"\", \"exception\": {\"message\": \"OVS configuration failed with: Unexpected error while running command.\\nCommand: sudo nova-rootwrap /etc/nova/rootwrap.conf ovs-vsctl --timeout=120 -- --if-exists del-port qvob1804d96-30 -- add-port br-int qvob1804d96-30 -- set Interface qvob1804d96-30 external-ids:iface-id=b1804d96-30f5-46ba-a897-4170a80eeb62 external-ids:iface-status=active external-ids:attached-mac=fa:16:3e:d2:71:84 external-ids:vm-uuid=2a15ac18-abe3-49a7-80d6-d96acf90f622\\nExit code: 142\\nStdout: u''\\nStderr: u'2017-03-22T14:46:25Z|00002|fatal_signal|WARN|terminating with signal 14 (Alarm clock)\\\\n'.\", \"kwargs\": {\"code\": 500, \"inner_exception\": {\"cmd\": \"sudo nova-rootwrap /etc/nova/rootwrap.conf ovs-vsctl --timeout=120 -- --if-exists del-port qvob1804d96-30 -- add-port br-int qvob1804d96-30 -- set Interface qvob1804d96-30 external-ids:iface-id=b1804d96-30f5-46ba-a897-4170a80eeb62 external-ids:iface-status=active external-ids:attached-mac=fa:16:3e:d2:71:84 external-ids:vm-uuid=2a15ac18-abe3-49a7-80d6-d96acf90f622\", \"stdout\": \"\", \"description\": null, \"stderr\": \"2017-03-22T14:46:25Z|00002|fatal_signal|WARN|terminating with signal 14 (Alarm clock)\\n\", \"exit_code\": 142}}}, \"root_gb\": 41, \"tenant_id\": \"b79291658f384b7ebbc9019b6349e5c9\", \"created_at\": \"2017-03-22 14:44:17+00:00\", \"memory_mb\": 8192, \"instance_type\": \"baremetal\", \"vcpus\": 4, \"image_meta\": {\"os_shutdown_timeout\": \"5\", \"container_format\": \"bare\", \"min_ram\": \"0\", \"disk_format\": \"qcow2\", \"min_disk\": \"41\", \"base_image_ref\": \"07fada8a-e3bd-43f3-a2b9-6b96626d0891\"}, \"architecture\": null, \"os_type\": null, \"instance_flavor_id\": \"fe34d440-8429-411d-8d73-7517822169a6\"}, \"_context_project_name\": \"openstack-nodepool\", \"_context_read_deleted\": \"no\", \"_context_user_identity\": \"ba119eef29ce49f5b8697f4d63948e3c b79291658f384b7ebbc9019b6349e5c9 - - -\", \"_context_auth_token\": \"df4b7c8ebecb4f5a8027eee4ce78d9f6\", \"_context_show_deleted\": false, \"_context_tenant\": \"b79291658f384b7ebbc9019b6349e5c9\", \"priority\": \"ERROR\", \"_context_read_only\": false, \"_context_is_admin\": false, \"_context_project_id\": \"b79291658f384b7ebbc9019b6349e5c9\", \"_context_project_domain\": null, \"_context_timestamp\": \"2017-03-22T14:44:16.482219\", \"_context_user_domain\": null, \"_context_user_name\": \"openstack-nodepool\", \"publisher_id\": \"compute.overcloud-novacompute-20.localdomain\", \"message_id\": \"a9b19221-8f74-419a-832d-8a5601146541\", \"_context_remote_address\": \"192.168.112.44\"}", "oslo.version": "2.0"}

fake_message2 = {"oslo.message": "{\"_context_domain\": null, \"_context_roles\": [\"_member_\"], \"_context_quota_class\": null, \"event_type\": \"start_instance\", \"_context_request_id\": \"req-42b301cd-68d4-45f8-85ce-570e43d923d2\", \"_context_service_catalog\": [{\"endpoints\": [{\"adminURL\": \"http://192.168.112.42:8776/v2/b79291658f384b7ebbc9019b6349e5c9\", \"region\": \"regionOne\", \"internalURL\": \"http://192.168.112.42:8776/v2/b79291658f384b7ebbc9019b6349e5c9\", \"publicURL\": \"https://ci-overcloud.rh1.tripleo.org:13776/v2/b79291658f384b7ebbc9019b6349e5c9\"}], \"type\": \"volumev2\", \"name\": \"cinderv2\"}, {\"endpoints\": [{\"adminURL\": \"http://192.168.112.42:8776/v1/b79291658f384b7ebbc9019b6349e5c9\", \"region\": \"regionOne\", \"internalURL\": \"http://192.168.112.42:8776/v1/b79291658f384b7ebbc9019b6349e5c9\", \"publicURL\": \"https://ci-overcloud.rh1.tripleo.org:13776/v1/b79291658f384b7ebbc9019b6349e5c9\"}], \"type\": \"volume\", \"name\": \"cinder\"}], \"timestamp\": \"2017-03-22 17:05:37.690504\", \"_context_user\": \"ba119eef29ce49f5b8697f4d63948e3c\", \"_unique_id\": \"c87cad5a649947a6b0f4862b2d351aa5\", \"_context_resource_uuid\": null, \"_context_instance_lock_checked\": false, \"_context_user_id\": \"ba119eef29ce49f5b8697f4d63948e3c\", \"payload\": {\"exception\": {\"status_code\": 401, \"message\": \"Authentication required\\nNeutron server returns request_ids: ['req-aa62557c-8b47-4f8a-ba8c-e9fc312746a6']\", \"_error_string\": \"Authentication required\\nNeutron server returns request_ids: ['req-aa62557c-8b47-4f8a-ba8c-e9fc312746a6']\", \"request_ids\": [\"req-aa62557c-8b47-4f8a-ba8c-e9fc312746a6\"]}, \"args\": {\"instance\": {\"vm_state\": \"stopped\", \"availability_zone\": null, \"terminated_at\": null, \"ephemeral_gb\": 0, \"instance_type_id\": 17, \"user_data\": \"Q29udGVudC1UeXBlOiBtdWx0aXBhcnQvbWl4ZWQ7IGJvdW5kYXJ5PSI9PT09PT09PT09PT09PT04MTA3MDczMzcwMjcyNDY2OTk4PT0iCk1JTUUtVmVyc2lvbjogMS4wCgotLT09PT09PT09PT09PT09PTgxMDcwNzMzNzAyNzI0NjY5OTg9PQpDb250ZW50LVR5cGU6IHRleHQvY2xvdWQtY29uZmlnOyBjaGFyc2V0PSJ1cy1hc2NpaSIKTUlNRS1WZXJzaW9uOiAxLjAKQ29udGVudC1UcmFuc2Zlci1FbmNvZGluZzogN2JpdApDb250ZW50LURpc3Bvc2l0aW9uOiBhdHRhY2htZW50OyBmaWxlbmFtZT0iY2xvdWQtY29uZmlnIgoKCgojIENhcHR1cmUgYWxsIHN1YnByb2Nlc3Mgb3V0cHV0IGludG8gYSBsb2dmaWxlCiMgVXNlZnVsIGZvciB0cm91Ymxlc2hvb3RpbmcgY2xvdWQtaW5pdCBpc3N1ZXMKb3V0cHV0OiB7YWxsOiAnfCB0ZWUgLWEgL3Zhci9sb2cvY2xvdWQtaW5pdC1vdXRwdXQubG9nJ30KCi0tPT09PT09PT09PT09PT09ODEwNzA3MzM3MDI3MjQ2Njk5OD09CkNvbnRlbnQtVHlwZTogdGV4dC9jbG91ZC1ib290aG9vazsgY2hhcnNldD0idXMtYXNjaWkiCk1JTUUtVmVyc2lvbjogMS4wCkNvbnRlbnQtVHJhbnNmZXItRW5jb2Rpbmc6IDdiaXQKQ29udGVudC1EaXNwb3NpdGlvbjogYXR0YWNobWVudDsgZmlsZW5hbWU9ImJvb3Rob29rLnNoIgoKIyEvYmluL2Jhc2gKCiMgRklYTUUoc2hhZG93ZXIpIHRoaXMgaXMgYSB3b3JrYXJvdW5kIGZvciBjbG91ZC1pbml0IDAuNi4zIHByZXNlbnQgaW4gVWJ1bnR1CiMgMTIuMDQgTFRTOgojIGh0dHBzOi8vYnVncy5sYXVuY2hwYWQubmV0L2hlYXQvK2J1Zy8xMjU3NDEwCiMKIyBUaGUgb2xkIGNsb3VkLWluaXQgZG9lc24ndCBjcmVhdGUgdGhlIHVzZXJzIGRpcmVjdGx5IHNvIHRoZSBjb21tYW5kcyB0byBkbwojIHRoaXMgYXJlIGluamVjdGVkIHRob3VnaCBub3ZhX3V0aWxzLnB5LgojCiMgT25jZSB3ZSBkcm9wIHN1cHBvcnQgZm9yIDAuNi4zLCB3ZSBjYW4gc2FmZWx5IHJlbW92ZSB0aGlzLgoKCiMgaW4gY2FzZSBoZWF0LWNmbnRvb2xzIGhhcyBiZWVuIGluc3RhbGxlZCBmcm9tIHBhY2thZ2UgYnV0IG5vIHN5bWxpbmtzCiMgYXJlIHlldCBpbiAvb3B0L2F3cy9iaW4vCmNmbi1jcmVhdGUtYXdzLXN5bWxpbmtzCgojIERvIG5vdCByZW1vdmUgLSB0aGUgY2xvdWQgYm9vdGhvb2sgc2hvdWxkIGFsd2F5cyByZXR1cm4gc3VjY2VzcwpleGl0IDAKCi0tPT09PT09PT09PT09PT09ODEwNzA3MzM3MDI3MjQ2Njk5OD09CkNvbnRlbnQtVHlwZTogdGV4dC9wYXJ0LWhhbmRsZXI7IGNoYXJzZXQ9InVzLWFzY2lpIgpNSU1FLVZlcnNpb246IDEuMApDb250ZW50LVRyYW5zZmVyLUVuY29kaW5nOiA3Yml0CkNvbnRlbnQtRGlzcG9zaXRpb246IGF0dGFjaG1lbnQ7IGZpbGVuYW1lPSJwYXJ0LWhhbmRsZXIucHkiCgojIHBhcnQtaGFuZGxlcgojCiMgICAgTGljZW5zZWQgdW5kZXIgdGhlIEFwYWNoZSBMaWNlbnNlLCBWZXJzaW9uIDIuMCAodGhlICJMaWNlbnNlIik7IHlvdSBtYXkKIyAgICBub3QgdXNlIHRoaXMgZmlsZSBleGNlcHQgaW4gY29tcGxpYW5jZSB3aXRoIHRoZSBMaWNlbnNlLiBZb3UgbWF5IG9idGFpbgojICAgIGEgY29weSBvZiB0aGUgTGljZW5zZSBhdAojCiMgICAgICAgICBodHRwOi8vd3d3LmFwYWNoZS5vcmcvbGljZW5zZXMvTElDRU5TRS0yLjAKIwojICAgIFVubGVzcyByZXF1aXJlZCBieSBhcHBsaWNhYmxlIGxhdyBvciBhZ3JlZWQgdG8gaW4gd3JpdGluZywgc29mdHdhcmUKIyAgICBkaXN0cmlidXRlZCB1bmRlciB0aGUgTGljZW5zZSBpcyBkaXN0cmlidXRlZCBvbiBhbiAiQVMgSVMiIEJBU0lTLCBXSVRIT1VUCiMgICAgV0FSUkFOVElFUyBPUiBDT05ESVRJT05TIE9GIEFOWSBLSU5ELCBlaXRoZXIgZXhwcmVzcyBvciBpbXBsaWVkLiBTZWUgdGhlCiMgICAgTGljZW5zZSBmb3IgdGhlIHNwZWNpZmljIGxhbmd1YWdlIGdvdmVybmluZyBwZXJtaXNzaW9ucyBhbmQgbGltaXRhdGlvbnMKIyAgICB1bmRlciB0aGUgTGljZW5zZS4KCmltcG9ydCBkYXRldGltZQppbXBvcnQgZXJybm8KaW1wb3J0IG9zCmltcG9ydCBzeXMKCgpkZWYgbGlzdF90eXBlcygpOgogICAgcmV0dXJuKFsidGV4dC94LWNmbmluaXRkYXRhIl0pCgoKZGVmIGhhbmRsZV9wYXJ0KGRhdGEsIGN0eXBlLCBmaWxlbmFtZSwgcGF5bG9hZCk6CiAgICBpZiBjdHlwZSA9PSAiX19iZWdpbl9fIjoKICAgICAgICB0cnk6CiAgICAgICAgICAgIG9zLm1ha2VkaXJzKCcvdmFyL2xpYi9oZWF0LWNmbnRvb2xzJywgaW50KCI3MDAiLCA4KSkKICAgICAgICBleGNlcHQgT1NFcnJvcjoKICAgICAgICAgICAgZXhfdHlwZSwgZSwgdGIgPSBzeXMuZXhjX2luZm8oKQogICAgICAgICAgICBpZiBlLmVycm5vICE9IGVycm5vLkVFWElTVDoKICAgICAgICAgICAgICAgIHJhaXNlCiAgICAgICAgcmV0dXJuCgogICAgaWYgY3R5cGUgPT0gIl9fZW5kX18iOgogICAgICAgIHJldHVybgoKICAgIHRpbWVzdGFtcCA9IGRhdGV0aW1lLmRhdGV0aW1lLm5vdygpCiAgICB3aXRoIG9wZW4oJy92YXIvbG9nL3BhcnQtaGFuZGxlci5sb2cnLCAnYScpIGFzIGxvZzoKICAgICAgICBsb2cud3JpdGUoJyVzIGZpbGVuYW1lOiVzLCBjdHlwZTolc1xuJyAlICh0aW1lc3RhbXAsIGZpbGVuYW1lLCBjdHlwZSkpCgogICAgaWYgY3R5cGUgPT0gJ3RleHQveC1jZm5pbml0ZGF0YSc6CiAgICAgICAgd2l0aCBvcGVuKCcvdmFyL2xpYi9oZWF0LWNmbnRvb2xzLyVzJyAlIGZpbGVuYW1lLCAndycpIGFzIGY6CiAgICAgICAgICAgIGYud3JpdGUocGF5bG9hZCkKCiAgICAgICAgIyBUT0RPKHNkYWtlKSBob3BlZnVsbHkgdGVtcG9yYXJ5IHVudGlsIHVzZXJzIG1vdmUgdG8gaGVhdC1jZm50b29scy0xLjMKICAgICAgICB3aXRoIG9wZW4oJy92YXIvbGliL2Nsb3VkL2RhdGEvJXMnICUgZmlsZW5hbWUsICd3JykgYXMgZjoKICAgICAgICAgICAgZi53cml0ZShwYXlsb2FkKQoKLS09PT09PT09PT09PT09PT04MTA3MDczMzcwMjcyNDY2OTk4PT0KQ29udGVudC1UeXBlOiB0ZXh0L3gtY2ZuaW5pdGRhdGE7IGNoYXJzZXQ9InVzLWFzY2lpIgpNSU1FLVZlcnNpb246IDEuMApDb250ZW50LVRyYW5zZmVyLUVuY29kaW5nOiA3Yml0CkNvbnRlbnQtRGlzcG9zaXRpb246IGF0dGFjaG1lbnQ7IGZpbGVuYW1lPSJjZm4tdXNlcmRhdGEiCgoKLS09PT09PT09PT09PT09PT04MTA3MDczMzcwMjcyNDY2OTk4PT0KQ29udGVudC1UeXBlOiB0ZXh0L3gtc2hlbGxzY3JpcHQ7IGNoYXJzZXQ9InVzLWFzY2lpIgpNSU1FLVZlcnNpb246IDEuMApDb250ZW50LVRyYW5zZmVyLUVuY29kaW5nOiA3Yml0CkNvbnRlbnQtRGlzcG9zaXRpb246IGF0dGFjaG1lbnQ7IGZpbGVuYW1lPSJsb2d1c2VyZGF0YS5weSIKCiMhL3Vzci9iaW4vZW52IHB5dGhvbgojCiMgICAgTGljZW5zZWQgdW5kZXIgdGhlIEFwYWNoZSBMaWNlbnNlLCBWZXJzaW9uIDIuMCAodGhlICJMaWNlbnNlIik7IHlvdSBtYXkKIyAgICBub3QgdXNlIHRoaXMgZmlsZSBleGNlcHQgaW4gY29tcGxpYW5jZSB3aXRoIHRoZSBMaWNlbnNlLiBZb3UgbWF5IG9idGFpbgojICAgIGEgY29weSBvZiB0aGUgTGljZW5zZSBhdAojCiMgICAgICAgICBodHRwOi8vd3d3LmFwYWNoZS5vcmcvbGljZW5zZXMvTElDRU5TRS0yLjAKIwojICAgIFVubGVzcyByZXF1aXJlZCBieSBhcHBsaWNhYmxlIGxhdyBvciBhZ3JlZWQgdG8gaW4gd3JpdGluZywgc29mdHdhcmUKIyAgICBkaXN0cmlidXRlZCB1bmRlciB0aGUgTGljZW5zZSBpcyBkaXN0cmlidXRlZCBvbiBhbiAiQVMgSVMiIEJBU0lTLCBXSVRIT1VUCiMgICAgV0FSUkFOVElFUyBPUiBDT05ESVRJT05TIE9GIEFOWSBLSU5ELCBlaXRoZXIgZXhwcmVzcyBvciBpbXBsaWVkLiBTZWUgdGhlCiMgICAgTGljZW5zZSBmb3IgdGhlIHNwZWNpZmljIGxhbmd1YWdlIGdvdmVybmluZyBwZXJtaXNzaW9ucyBhbmQgbGltaXRhdGlvbnMKIyAgICB1bmRlciB0aGUgTGljZW5zZS4KCmltcG9ydCBkYXRldGltZQpmcm9tIGRpc3R1dGlscyBpbXBvcnQgdmVyc2lvbgppbXBvcnQgZXJybm8KaW1wb3J0IGxvZ2dpbmcKaW1wb3J0IG9zCmltcG9ydCByZQppbXBvcnQgc3VicHJvY2VzcwppbXBvcnQgc3lzCgppbXBvcnQgcGtnX3Jlc291cmNlcwoKClZBUl9QQVRIID0gJy92YXIvbGliL2hlYXQtY2ZudG9vbHMnCkxPRyA9IGxvZ2dpbmcuZ2V0TG9nZ2VyKCdoZWF0LXByb3Zpc2lvbicpCgoKZGVmIGNoa19jaV92ZXJzaW9uKCk6CiAgICB0cnk6CiAgICAgICAgdiA9IHZlcnNpb24uTG9vc2VWZXJzaW9uKAogICAgICAgICAgICBwa2dfcmVzb3VyY2VzLmdldF9kaXN0cmlidXRpb24oJ2Nsb3VkLWluaXQnKS52ZXJzaW9uKQogICAgICAgIHJldHVybiB2ID49IHZlcnNpb24uTG9vc2VWZXJzaW9uKCcwLjYuMCcpCiAgICBleGNlcHQgRXhjZXB0aW9uOgogICAgICAgIHBhc3MKICAgIGRhdGEgPSBzdWJwcm9jZXNzLlBvcGVuKFsnY2xvdWQtaW5pdCcsICctLXZlcnNpb24nXSwKICAgICAgICAgICAgICAgICAgICAgICAgICAgIHN0ZG91dD1zdWJwcm9jZXNzLlBJUEUsCiAgICAgICAgICAgICAgICAgICAgICAgICAgICBzdGRlcnI9c3VicHJvY2Vzcy5QSVBFKS5jb21tdW5pY2F0ZSgpCiAgICBpZiBkYXRhWzBdOgogICAgICAgIHJhaXNlIEV4Y2VwdGlvbigpCiAgICAjIGRhdGFbMV0gaGFzIHN1Y2ggZm9ybWF0OiAnY2xvdWQtaW5pdCAwLjcuNVxuJywgbmVlZCB0byBwYXJzZSB2ZXJzaW9uCiAgICB2ID0gcmUuc3BsaXQoJyB8XG4nLCBkYXRhWzFdKVsxXS5zcGxpdCgnLicpCiAgICByZXR1cm4gdHVwbGUodikgPj0gdHVwbGUoWycwJywgJzYnLCAnMCddKQoKCmRlZiBpbml0X2xvZ2dpbmcoKToKICAgIExPRy5zZXRMZXZlbChsb2dnaW5nLklORk8pCiAgICBMT0cuYWRkSGFuZGxlcihsb2dnaW5nLlN0cmVhbUhhbmRsZXIoKSkKICAgIGZoID0gbG9nZ2luZy5GaWxlSGFuZGxlcigiL3Zhci9sb2cvaGVhdC1wcm92aXNpb24ubG9nIikKICAgIG9zLmNobW9kKGZoLmJhc2VGaWxlbmFtZSwgaW50KCI2MDAiLCA4KSkKICAgIExPRy5hZGRIYW5kbGVyKGZoKQoKCmRlZiBjYWxsKGFyZ3MpOgoKICAgIGNsYXNzIExvZ1N0cmVhbShvYmplY3QpOgoKICAgICAgICBkZWYgd3JpdGUoc2VsZiwgZGF0YSk6CiAgICAgICAgICAgIExPRy5pbmZvKGRhdGEpCgogICAgTE9HLmluZm8oJyVzXG4nLCAnICcuam9pbihhcmdzKSkgICMgbm9xYQogICAgdHJ5OgogICAgICAgIGxzID0gTG9nU3RyZWFtKCkKICAgICAgICBwID0gc3VicHJvY2Vzcy5Qb3BlbihhcmdzLCBzdGRvdXQ9c3VicHJvY2Vzcy5QSVBFLAogICAgICAgICAgICAgICAgICAgICAgICAgICAgIHN0ZGVycj1zdWJwcm9jZXNzLlBJUEUpCiAgICAgICAgZGF0YSA9IHAuY29tbXVuaWNhdGUoKQogICAgICAgIGlmIGRhdGE6CiAgICAgICAgICAgIGZvciB4IGluIGRhdGE6CiAgICAgICAgICAgICAgICBscy53cml0ZSh4KQogICAgZXhjZXB0IE9TRXJyb3I6CiAgICAgICAgZXhfdHlwZSwgZXgsIHRiID0gc3lzLmV4Y19pbmZvKCkKICAgICAgICBpZiBleC5lcnJubyA9PSBlcnJuby5FTk9FWEVDOgogICAgICAgICAgICBMT0cuZXJyb3IoJ1VzZXJkYXRhIGVtcHR5IG9yIG5vdCBleGVjdXRhYmxlOiAlcycsIGV4KQogICAgICAgICAgICByZXR1cm4gb3MuRVhfT0sKICAgICAgICBlbHNlOgogICAgICAgICAgICBMT0cuZXJyb3IoJ09TIGVycm9yIHJ1bm5pbmcgdXNlcmRhdGE6ICVzJywgZXgpCiAgICAgICAgICAgIHJldHVybiBvcy5FWF9PU0VSUgogICAgZXhjZXB0IEV4Y2VwdGlvbjoKICAgICAgICBleF90eXBlLCBleCwgdGIgPSBzeXMuZXhjX2luZm8oKQogICAgICAgIExPRy5lcnJvcignVW5rbm93biBlcnJvciBydW5uaW5nIHVzZXJkYXRhOiAlcycsIGV4KQogICAgICAgIHJldHVybiBvcy5FWF9TT0ZUV0FSRQogICAgcmV0dXJuIHAucmV0dXJuY29kZQoKCmRlZiBtYWluKCk6CgogICAgdHJ5OgogICAgICAgIGlmIG5vdCBjaGtfY2lfdmVyc2lvbigpOgogICAgICAgICAgICAjIHByZSAwLjYuMCAtIHVzZXIgZGF0YSBleGVjdXRlZCB2aWEgY2xvdWRpbml0LCBub3QgdGhpcyBoZWxwZXIKICAgICAgICAgICAgTE9HLmVycm9yKCdVbmFibGUgdG8gbG9nIHByb3Zpc2lvbmluZywgbmVlZCBhIG5ld2VyIHZlcnNpb24gb2YgJwogICAgICAgICAgICAgICAgICAgICAgJ2Nsb3VkLWluaXQnKQogICAgICAgICAgICByZXR1cm4gLTEKICAgIGV4Y2VwdCBFeGNlcHRpb246CiAgICAgICAgTE9HLndhcm5pbmcoJ0NhbiBub3QgZGV0ZXJtaW5lIHRoZSB2ZXJzaW9uIG9mIGNsb3VkLWluaXQuIEl0IGlzICcKICAgICAgICAgICAgICAgICAgICAncG9zc2libGUgdG8gZ2V0IGVycm9ycyB3aGlsZSBsb2dnaW5nIHByb3Zpc2lvbmluZy4nKQoKICAgIHVzZXJkYXRhX3BhdGggPSBvcy5wYXRoLmpvaW4oVkFSX1BBVEgsICdjZm4tdXNlcmRhdGEnKQogICAgb3MuY2htb2QodXNlcmRhdGFfcGF0aCwgaW50KCI3MDAiLCA4KSkKCiAgICBMT0cuaW5mbygnUHJvdmlzaW9uIGJlZ2FuOiAlcycsIGRhdGV0aW1lLmRhdGV0aW1lLm5vdygpKQogICAgcmV0dXJuY29kZSA9IGNhbGwoW3VzZXJkYXRhX3BhdGhdKQogICAgTE9HLmluZm8oJ1Byb3Zpc2lvbiBkb25lOiAlcycsIGRhdGV0aW1lLmRhdGV0aW1lLm5vdygpKQogICAgaWYgcmV0dXJuY29kZToKICAgICAgICByZXR1cm4gcmV0dXJuY29kZQoKCmlmIF9fbmFtZV9fID09ICdfX21haW5fXyc6CiAgICBpbml0X2xvZ2dpbmcoKQoKICAgIGNvZGUgPSBtYWluKCkKICAgIGlmIGNvZGU6CiAgICAgICAgTE9HLmVycm9yKCdQcm92aXNpb24gZmFpbGVkIHdpdGggZXhpdCBjb2RlICVzJywgY29kZSkKICAgICAgICBzeXMuZXhpdChjb2RlKQoKICAgIHByb3Zpc2lvbl9sb2cgPSBvcy5wYXRoLmpvaW4oVkFSX1BBVEgsICdwcm92aXNpb24tZmluaXNoZWQnKQogICAgIyB0b3VjaCB0aGUgZmlsZSBzbyBpdCBpcyB0aW1lc3RhbXBlZCB3aXRoIHdoZW4gZmluaXNoZWQKICAgIHdpdGggb3Blbihwcm92aXNpb25fbG9nLCAnYScpOgogICAgICAgIG9zLnV0aW1lKHByb3Zpc2lvbl9sb2csIE5vbmUpCgotLT09PT09PT09PT09PT09PTgxMDcwNzMzNzAyNzI0NjY5OTg9PQpDb250ZW50LVR5cGU6IHRleHQveC1jZm5pbml0ZGF0YTsgY2hhcnNldD0idXMtYXNjaWkiCk1JTUUtVmVyc2lvbjogMS4wCkNvbnRlbnQtVHJhbnNmZXItRW5jb2Rpbmc6IDdiaXQKQ29udGVudC1EaXNwb3NpdGlvbjogYXR0YWNobWVudDsgZmlsZW5hbWU9ImNmbi13YXRjaC1zZXJ2ZXIiCgpodHRwOi8vMTkyLjE2OC4xMTIuNDI6ODAwMwotLT09PT09PT09PT09PT09PTgxMDcwNzMzNzAyNzI0NjY5OTg9PQpDb250ZW50LVR5cGU6IHRleHQveC1jZm5pbml0ZGF0YTsgY2hhcnNldD0idXMtYXNjaWkiCk1JTUUtVmVyc2lvbjogMS4wCkNvbnRlbnQtVHJhbnNmZXItRW5jb2Rpbmc6IDdiaXQKQ29udGVudC1EaXNwb3NpdGlvbjogYXR0YWNobWVudDsgZmlsZW5hbWU9ImNmbi1tZXRhZGF0YS1zZXJ2ZXIiCgpodHRwOi8vMTkyLjE2OC4xMTIuNDI6ODAwMC92MS8KLS09PT09PT09PT09PT09PT04MTA3MDczMzcwMjcyNDY2OTk4PT0KQ29udGVudC1UeXBlOiB0ZXh0L3gtY2ZuaW5pdGRhdGE7IGNoYXJzZXQ9InVzLWFzY2lpIgpNSU1FLVZlcnNpb246IDEuMApDb250ZW50LVRyYW5zZmVyLUVuY29kaW5nOiA3Yml0CkNvbnRlbnQtRGlzcG9zaXRpb246IGF0dGFjaG1lbnQ7IGZpbGVuYW1lPSJjZm4tYm90by1jZmciCgpbQm90b10KZGVidWcgPSAwCmlzX3NlY3VyZSA9IDAKaHR0cHNfdmFsaWRhdGVfY2VydGlmaWNhdGVzID0gMQpjZm5fcmVnaW9uX25hbWUgPSBoZWF0CmNmbl9yZWdpb25fZW5kcG9pbnQgPSAxOTIuMTY4LjExMi40MgpjbG91ZHdhdGNoX3JlZ2lvbl9uYW1lID0gaGVhdApjbG91ZHdhdGNoX3JlZ2lvbl9lbmRwb2ludCA9IDE5Mi4xNjguMTEyLjQyCi0tPT09PT09PT09PT09PT09ODEwNzA3MzM3MDI3MjQ2Njk5OD09LS0=\", \"cleaned\": false, \"vm_mode\": null, \"flavor\": {\"memory_mb\": 8192, \"root_gb\": 41, \"deleted_at\": null, \"name\": \"baremetal\", \"deleted\": false, \"created_at\": \"2016-11-17T22:55:19.000000\", \"ephemeral_gb\": 0, \"updated_at\": null, \"disabled\": false, \"vcpus\": 4, \"extra_specs\": {}, \"swap\": 0, \"rxtx_factor\": 1.0, \"is_public\": true, \"flavorid\": \"fe34d440-8429-411d-8d73-7517822169a6\", \"vcpu_weight\": 0, \"id\": 17}, \"deleted_at\": null, \"reservation_id\": \"r-h2ee9mss\", \"id\": 503409, \"disable_terminate\": false, \"root_device_name\": \"/dev/vda\", \"display_name\": \"baremetal-41589_2\", \"uuid\": \"875e7da1-d1e3-4f22-9387-6392c1c9319b\", \"default_swap_device\": null, \"info_cache\": {\"instance_uuid\": \"875e7da1-d1e3-4f22-9387-6392c1c9319b\", \"deleted\": false, \"created_at\": \"2017-03-22T16:03:04.000000\", \"updated_at\": \"2017-03-22T16:19:03.000000\", \"network_info\": [{\"profile\": {}, \"ovs_interfaceid\": \"b12641e7-2c54-4bd1-86bf-9ea44c44731b\", \"preserve_on_delete\": true, \"network\": {\"bridge\": \"br-int\", \"label\": \"provision-41589\", \"meta\": {\"injected\": false, \"tenant_id\": \"b79291658f384b7ebbc9019b6349e5c9\", \"mtu\": 1450}, \"id\": \"a631964e-557c-45ed-9adb-157c48f79d6f\", \"subnets\": [{\"ips\": [{\"meta\": {}, \"type\": \"fixed\", \"version\": 4, \"address\": \"192.0.2.3\", \"floating_ips\": []}], \"version\": 4, \"meta\": {}, \"dns\": [], \"routes\": [], \"cidr\": \"192.0.2.0/24\", \"gateway\": {\"meta\": {}, \"type\": \"gateway\", \"version\": null, \"address\": null}}]}, \"devname\": \"tapb12641e7-2c\", \"qbh_params\": null, \"vnic_type\": \"normal\", \"meta\": {}, \"details\": {\"port_filter\": true, \"ovs_hybrid_plug\": true}, \"address\": \"fa:16:3e:9c:6d:89\", \"active\": true, \"type\": \"ovs\", \"id\": \"b12641e7-2c54-4bd1-86bf-9ea44c44731b\", \"qbg_params\": null}], \"deleted_at\": null}, \"hostname\": \"baremetal-41589-2\", \"launched_on\": \"overcloud-novacompute-26.localdomain\", \"display_description\": \"baremetal-41589_2\", \"key_data\": \"ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCdK/KnJPXaycb8hOX9j1f/lU1HuB9GMUhCN7of4KrRs3OjzCtMUNZJSTCQaeUlR6VijNvUIe6Wx5zWCDR1DgNv/InQjr+7RhSgMofStz1TfJrlkGBfZw2mrhpPnX3fLaCf9Dyl+8+cuTjxGTMtYngJx2/9aNpgl75hMgaM6BRh/ULM+lLBDlCI+r9dFSsVx9UKTQUyenDh4A3J3eszP1CTT1sBWDKU5zz39MqWpzIxRaBgk+nI8+Uxbih7FUPaLLqlrl4Nxdr9A/Aul9pB8OSk/BK1oX/8mYW5mDE3usbeXIVU53ojEG0pkKaq4N9oeMorGB65xG7uAf845Av0qOpr derekh@Tea540\\nssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEA+yNMzUrQXa0EOfv+WJtfmLO1WdoOaD47G9qwllSUc4GPRkYzkTNdxcEPrR3XBR94ctOeWOHZ/w7ymhvwK5LLsoNBK+WgRz/mg8oHcii2GoL0fNojdwUMyFMIJxJT+iwjF/omyhyrW/aLAztAKRO7BdOkNlXMAAcMxKzQtFqdZm09ghoImu3BPYUTyDKHMp+t0P1d7mkHdd719oDfMf+5miHxQeJZJCWAsGwroN7k8a46rvezDHEygBsDAF2ZpS2iGMABos/vTp1oyHkCgCqc3rM0OoKqcKB5iQ9Qaqi5ung08BXP/PHfVynXzdGMjTh4w+6jiMw7Dx2GrQIJsDolKQ== dan.prince@dovetail\\nssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDSP0DZRAwaTAvHk7mHlLfSwVq6QCRqKn8mE6nwW1UzBmTzKdq9pK5XPqEAQgUKoarl+M+QhCNrBaNKpUqPF1dH76S0+2k2HARrxubTlXsQ9UDQQHQZxGjsrYW9sZ/F7yh4Yac7HW4pZANumyAxt0yKE0BLTZX9JojaiBn7bMzw1i5BS6qXIyH7oohd3YThxkpMCqP4O6W6wX90FSDYPtbSaZ1Q+9hzNkS29bXcsoy6uwTixkfedsCgkLb2wa9jcDHCely94Tn/oR+JjT9OQ19Tq8p/rjL8lullIrkHsEEsQ/4sIlB6441DgbeLtQAPPA7pyw50KfBCyTfHQZWPsacN jslagle@redhat.com\\nssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDv9l/F0vq7nzAT5hdrBfqDv0rD76nHNn+siS6s5gaFyAuvXJG808pqFk5bJLbRdRIA1/cLxIQeB+bB7IjeTS7Afbz/baAOPTtoumwEU8wLPzR7IyTg60R4o7pKOJG2cP45s3TGODsYt5eEAr96EGp9ayyanfuJZZf2wQWdNp1+vQXain8WHv9KIKI5XmcKI80x8RBWV86OKKsmbqV4yYxAkuLitq4h3Bhw3LP+VOxaqApevnpt7fcrvn8QR3XMsLKNZsJhT9r1qeLEZisundZPN+0EuiC7seu5zAuCBcKjRrBo7Ime8TYn5sjz9DTMcWvY3xHF2DZN2YdVxp4O8/iD bnemec@localhost.localdomain\\n\", \"deleted\": false, \"power_state\": 4, \"key_name\": \"tripleo-cd-admins\", \"default_ephemeral_device\": null, \"progress\": 0, \"project_id\": \"b79291658f384b7ebbc9019b6349e5c9\", \"launched_at\": \"2017-03-22T16:03:29.000000\", \"metadata\": {\"libvirt:pxe-first\": \"\"}, \"node\": \"overcloud-novacompute-26.localdomain\", \"ramdisk_id\": \"\", \"access_ip_v6\": null, \"access_ip_v4\": null, \"kernel_id\": \"\", \"old_flavor\": null, \"updated_at\": \"2017-03-22T17:05:36.000000\", \"host\": \"overcloud-novacompute-26.localdomain\", \"root_gb\": 41, \"user_id\": \"ba119eef29ce49f5b8697f4d63948e3c\", \"system_metadata\": {\"image_disk_format\": \"qcow2\", \"image_os_shutdown_timeout\": \"5\", \"image_container_format\": \"bare\", \"image_min_ram\": \"0\", \"image_min_disk\": \"41\", \"image_base_image_ref\": \"07fada8a-e3bd-43f3-a2b9-6b96626d0891\"}, \"task_state\": null, \"shutdown_terminate\": false, \"cell_name\": null, \"ephemeral_key_uuid\": null, \"locked\": false, \"name\": \"instance-0007ae71\", \"created_at\": \"2017-03-22T16:03:04.000000\", \"locked_by\": null, \"launch_index\": 0, \"memory_mb\": 8192, \"vcpus\": 4, \"image_ref\": \"07fada8a-e3bd-43f3-a2b9-6b96626d0891\", \"architecture\": null, \"auto_disk_config\": false, \"os_type\": null, \"config_drive\": \"\", \"new_flavor\": null}, \"context\": {\"domain\": null, \"project_domain\": null, \"auth_token\": \"04a8d0ed1ce14869a33aab82f66022d5\", \"resource_uuid\": null, \"read_only\": false, \"user_id\": \"ba119eef29ce49f5b8697f4d63948e3c\", \"_read_deleted\": \"no\", \"instance_lock_checked\": false, \"project_id\": \"b79291658f384b7ebbc9019b6349e5c9\", \"user_name\": \"openstack-nodepool\", \"db_connection\": null, \"project_name\": \"openstack-nodepool\", \"timestamp\": \"2017-03-22T17:05:36.081828\", \"remote_address\": \"192.168.112.44\", \"quota_class\": null, \"is_admin\": false, \"user\": \"ba119eef29ce49f5b8697f4d63948e3c\", \"service_catalog\": [{\"endpoints\": [{\"adminURL\": \"http://192.168.112.42:8776/v2/b79291658f384b7ebbc9019b6349e5c9\", \"region\": \"regionOne\", \"internalURL\": \"http://192.168.112.42:8776/v2/b79291658f384b7ebbc9019b6349e5c9\", \"publicURL\": \"https://ci-overcloud.rh1.tripleo.org:13776/v2/b79291658f384b7ebbc9019b6349e5c9\"}], \"type\": \"volumev2\", \"name\": \"cinderv2\"}, {\"endpoints\": [{\"adminURL\": \"http://192.168.112.42:8776/v1/b79291658f384b7ebbc9019b6349e5c9\", \"region\": \"regionOne\", \"internalURL\": \"http://192.168.112.42:8776/v1/b79291658f384b7ebbc9019b6349e5c9\", \"publicURL\": \"https://ci-overcloud.rh1.tripleo.org:13776/v1/b79291658f384b7ebbc9019b6349e5c9\"}], \"type\": \"volume\", \"name\": \"cinder\"}], \"tenant\": \"b79291658f384b7ebbc9019b6349e5c9\", \"show_deleted\": false, \"roles\": [\"_member_\"], \"request_id\": \"req-42b301cd-68d4-45f8-85ce-570e43d923d2\", \"user_auth_plugin\": null, \"user_domain\": null}}}, \"_context_project_name\": \"openstack-nodepool\", \"_context_read_deleted\": \"no\", \"_context_user_identity\": \"ba119eef29ce49f5b8697f4d63948e3c b79291658f384b7ebbc9019b6349e5c9 - - -\", \"_context_auth_token\": \"04a8d0ed1ce14869a33aab82f66022d5\", \"_context_show_deleted\": false, \"_context_tenant\": \"b79291658f384b7ebbc9019b6349e5c9\", \"priority\": \"ERROR\", \"_context_read_only\": false, \"_context_is_admin\": false, \"_context_project_id\": \"b79291658f384b7ebbc9019b6349e5c9\", \"_context_project_domain\": null, \"_context_timestamp\": \"2017-03-22T17:05:36.081828\", \"_context_user_domain\": null, \"_context_user_name\": \"openstack-nodepool\", \"publisher_id\": \"compute.overcloud-novacompute-26.localdomain\", \"message_id\": \"4ffd015c-71ff-4a01-aa7e-f23b3a15811c\", \"_context_remote_address\": \"192.168.112.44\"}", "oslo.version": "2.0"}
fake_message3 = {u'oslo.message': u'{"_context_domain": null, "_context_roles": ["_member_"], "_context_quota_class": null, "event_type": "compute.instance.create.error", "_context_request_id": "req-1cbfff85-01a6-42e3-8caa-2b814b2e0eee", "_context_service_catalog": [{"endpoints": [{"adminURL": "http://192.168.112.42:8776/v2/b79291658f384b7ebbc9019b6349e5c9", "region": "regionOne", "internalURL": "http://192.168.112.42:8776/v2/b79291658f384b7ebbc9019b6349e5c9", "publicURL": "https://ci-overcloud.rh1.tripleo.org:13776/v2/b79291658f384b7ebbc9019b6349e5c9"}], "type": "volumev2", "name": "cinderv2"}, {"endpoints": [{"adminURL": "http://192.168.112.42:8776/v1/b79291658f384b7ebbc9019b6349e5c9", "region": "regionOne", "internalURL": "http://192.168.112.42:8776/v1/b79291658f384b7ebbc9019b6349e5c9", "publicURL": "https://ci-overcloud.rh1.tripleo.org:13776/v1/b79291658f384b7ebbc9019b6349e5c9"}], "type": "volume", "name": "cinder"}], "timestamp": "2017-03-22 17:54:58.100396", "_context_user": "ba119eef29ce49f5b8697f4d63948e3c", "_unique_id": "bdded68141894403abb2672074345e6b", "_context_resource_uuid": null, "_context_instance_lock_checked": false, "_context_user_id": "ba119eef29ce49f5b8697f4d63948e3c", "payload": {"state_description": "spawning", "code": 500, "availability_zone": null, "terminated_at": "", "ephemeral_gb": 0, "instance_type_id": 6, "message": "Argument list too long", "deleted_at": "", "reservation_id": "r-8lu0rmtr", "instance_id": "4643bade-f764-463b-8f59-6b8a234ca1b5", "display_name": "bmc-41650", "hostname": "bmc-41650", "state": "building", "progress": "", "launched_at": "", "metadata": {}, "node": "overcloud-novacompute-4.localdomain", "ramdisk_id": "", "access_ip_v6": null, "disk_gb": 20, "access_ip_v4": null, "kernel_id": "", "host": "overcloud-novacompute-4.localdomain", "user_id": "ba119eef29ce49f5b8697f4d63948e3c", "image_ref_url": "http://192.168.112.50:9292/images/1aabe923-041d-46c2-b5bf-1bfa28317416", "cell_name": "", "exception": {"err": [89, 47, "Argument list too long", 2, "System.Error.E2BIG", null, null, 0, 0]}, "root_gb": 20, "tenant_id": "b79291658f384b7ebbc9019b6349e5c9", "created_at": "2017-03-22 17:54:40+00:00", "memory_mb": 512, "instance_type": "bmc", "vcpus": 1, "image_meta": {"instance_uuid": "9a89e86c-8ca5-4c8a-be8a-c3e7a2eaa57c", "image_location": "snapshot", "image_state": "available", "user_id": "ba119eef29ce49f5b8697f4d63948e3c", "image_type": "snapshot", "container_format": "bare", "min_ram": "0", "disk_format": "qcow2", "min_disk": "20", "base_image_ref": "797e216e-44da-4cca-b249-e90c120a0557", "owner_id": "b79291658f384b7ebbc9019b6349e5c9"}, "architecture": null, "os_type": null, "instance_flavor_id": "2aaef5e1-a585-4bb9-b1e8-134d82f55982"}, "_context_project_name": "openstack-nodepool", "_context_read_deleted": "no", "_context_user_identity": "ba119eef29ce49f5b8697f4d63948e3c b79291658f384b7ebbc9019b6349e5c9 - - -", "_context_auth_token": "fc7c2ce7d57146cd86552b50bad72a4a", "_context_show_deleted": false, "_context_tenant": "b79291658f384b7ebbc9019b6349e5c9", "priority": "ERROR", "_context_read_only": false, "_context_is_admin": false, "_context_project_id": "b79291658f384b7ebbc9019b6349e5c9", "_context_project_domain": null, "_context_timestamp": "2017-03-22T17:54:40.095888", "_context_user_domain": null, "_context_user_name": "openstack-nodepool", "publisher_id": "compute.overcloud-novacompute-4.localdomain", "message_id": "9dff5562-2b06-45d5-a50f-0e3e45e85550", "_context_remote_address": "192.168.112.44"}', u'oslo.version': u'2.0'}
fake_message4 = {u'oslo.message': u'{"_context_domain": null, "_context_roles": ["_member_"], "_context_quota_class": null, "event_type": "compute.instance.create.error", "_context_request_id": "req-fba52505-1d4d-4c45-ba61-b69aabe5d92f", "_context_service_catalog": [{"endpoints": [{"adminURL": "http://192.168.112.42:8776/v2/b79291658f384b7ebbc9019b6349e5c9", "region": "regionOne", "internalURL": "http://192.168.112.42:8776/v2/b79291658f384b7ebbc9019b6349e5c9", "publicURL": "https://ci-overcloud.rh1.tripleo.org:13776/v2/b79291658f384b7ebbc9019b6349e5c9"}], "type": "volumev2", "name": "cinderv2"}, {"endpoints": [{"adminURL": "http://192.168.112.42:8776/v1/b79291658f384b7ebbc9019b6349e5c9", "region": "regionOne", "internalURL": "http://192.168.112.42:8776/v1/b79291658f384b7ebbc9019b6349e5c9", "publicURL": "https://ci-overcloud.rh1.tripleo.org:13776/v1/b79291658f384b7ebbc9019b6349e5c9"}], "type": "volume", "name": "cinder"}], "timestamp": "2017-03-22 17:54:09.159117", "_context_user": "ba119eef29ce49f5b8697f4d63948e3c", "_unique_id": "26e66dc9b64546bab4042b490cb45d01", "_context_resource_uuid": null, "_context_instance_lock_checked": false, "_context_user_id": "ba119eef29ce49f5b8697f4d63948e3c", "payload": {"state_description": "spawning", "code": 400, "availability_zone": null, "terminated_at": "", "ephemeral_gb": 0, "instance_type_id": 6, "message": "Port 0668d309-58d5-4b26-be42-a21a3edadf01 is still in use.", "deleted_at": "", "reservation_id": "r-7qqeyl0v", "instance_id": "42eda720-222c-407b-9837-a712ede207fb", "display_name": "bmc-41633", "hostname": "bmc-41633", "state": "building", "progress": "", "launched_at": "", "metadata": {}, "node": "overcloud-novacompute-12.localdomain", "ramdisk_id": "", "access_ip_v6": null, "disk_gb": 20, "access_ip_v4": null, "kernel_id": "", "host": "overcloud-novacompute-12.localdomain", "user_id": "ba119eef29ce49f5b8697f4d63948e3c", "image_ref_url": "http://192.168.112.70:9292/images/1aabe923-041d-46c2-b5bf-1bfa28317416", "cell_name": "", "exception": {"message": "Port 0668d309-58d5-4b26-be42-a21a3edadf01 is still in use.", "kwargs": {"code": 400, "port_id": "0668d309-58d5-4b26-be42-a21a3edadf01"}}, "root_gb": 20, "tenant_id": "b79291658f384b7ebbc9019b6349e5c9", "created_at": "2017-03-22 17:53:40+00:00", "memory_mb": 512, "instance_type": "bmc", "vcpus": 1, "image_meta": {"instance_uuid": "9a89e86c-8ca5-4c8a-be8a-c3e7a2eaa57c", "image_location": "snapshot", "image_state": "available", "user_id": "ba119eef29ce49f5b8697f4d63948e3c", "image_type": "snapshot", "container_format": "bare", "min_ram": "0", "disk_format": "qcow2", "min_disk": "20", "base_image_ref": "797e216e-44da-4cca-b249-e90c120a0557", "owner_id": "b79291658f384b7ebbc9019b6349e5c9"}, "architecture": null, "os_type": null, "instance_flavor_id": "2aaef5e1-a585-4bb9-b1e8-134d82f55982"}, "_context_project_name": "openstack-nodepool", "_context_read_deleted": "no", "_context_user_identity": "ba119eef29ce49f5b8697f4d63948e3c b79291658f384b7ebbc9019b6349e5c9 - - -", "_context_auth_token": "a4e050b794e04a67b7f64481acf541b3", "_context_show_deleted": false, "_context_tenant": "b79291658f384b7ebbc9019b6349e5c9", "priority": "ERROR", "_context_read_only": false, "_context_is_admin": false, "_context_project_id": "b79291658f384b7ebbc9019b6349e5c9", "_context_project_domain": null, "_context_timestamp": "2017-03-22T17:53:39.933420", "_context_user_domain": null, "_context_user_name": "openstack-nodepool", "publisher_id": "compute.overcloud-novacompute-12.localdomain", "message_id": "e3227eff-2b49-4c80-b5b4-70592a0c359e", "_context_remote_address": "192.168.112.44"}', u'oslo.version': u'2.0'}

def _callback(ch, method, properties, body):
    _parse_message(json.loads(body))

def _parse_message(msg):
    print('*** Notification Details ***')
    try:
        content = json.loads(msg['oslo.message'])
        print('timestamp: %s' % content['timestamp'])
        print('retrieved: %s' % time.ctime())
        payload = content['payload']
        base = payload
        if 'exception' in base:
            print('%s: %s' % ('exception', payload['exception']))
            if 'args' in base:
                base = base['args'].get('instance', {})
        for key in ['state_description', 'code', 'message', 'display_name',
                    'state', 'node']:
            print('%s: %s' % (key, base.get(key, 'NA')))
    except KeyError:
        print('Failed to parse %s' % msg)

def _main():
    credentials = pika.PlainCredentials('guest', 'NgCZnypbuUYUWmXycHJMNmqwj')
    connection = pika.BlockingConnection(
        pika.ConnectionParameters('192.168.112.44',
                                  credentials=credentials))
    channel = connection.channel()
    channel.queue_declare(queue='notifications.error')
    fake_message = False
    #fake_message = True
    if fake_message:
        channel.basic_publish(exchange='',
                            routing_key='notifications.error',
                            body=json.dumps(fake_message1))
        channel.basic_publish(exchange='',
                            routing_key='notifications.error',
                            body=json.dumps(fake_message2))
        channel.basic_publish(exchange='',
                            routing_key='notifications.error',
                            body=json.dumps(fake_message3))
        channel.basic_publish(exchange='',
                            routing_key='notifications.error',
                            body=json.dumps(fake_message4))
        print('sent')
    channel.basic_consume(_callback, queue='notifications.error', no_ack=True)
    channel.start_consuming()
    connection.close()

if __name__ == '__main__':
    _main()