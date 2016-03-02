### Convenience scripts for tripleo ###

This is just a collection of scripts I've put together that I use for tripleo development.

undercloud_wizard.py
--------------------

A PyQt GUI to help with generating undercloud.conf.  See details in the
docstring at the top of the file.

net-iso-gen.py
--------------

A PyQt GUI to help with generating TripleO network isolation templates.
Uses a number of other files in this repo, so you probably want the whole
thing if you're going to use this tool.

limit-fix
---------

This was a couple of templates for setting sane limits on a TripleO overcloud.
It should not be needed in any recent version of TripleO.

QuintupleO
----------

QuintupleO-related pieces (including openstackbmc) have moved to https://github.com/cybertron/openstack-virtual-baremetal
