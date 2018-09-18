Convenience scripts for tripleo
===============================

This is just a collection of scripts and tools I've put together that I use for tripleo development.

net-iso-gen.py
--------------

A PyQt GUI to help with generating TripleO network isolation templates.
Uses a number of other files in this repo, so you probably want the whole
thing if you're going to use this tool.

### Requirements ###

* PyQt4
* netaddr

On Red Hat-based platforms, these can be installed with `yum install PyQt4 python-netaddr`

### News ###

See [my blog](http://blog.nemebean.com/tags/net-iso-gen) for the latest news about the tool.

### Usage ###

Since this is a GUI tool, it's easiest to run it on your workstation, as opposed
to the undercloud.  The output path should be set to a directory where
network-isolation.yaml, network-environment.yaml, and the nic-configs directory
will be written.

In addition, to facilitate loading of previously generated templates back into
the tool, it writes a ui-settings.pickle file.  Because the template settings
are entirely loaded from this file, if manual edits are made to the generated
templates they will _not_ be reflected in the tool the next time they are
loaded.

The network-isolation.yaml file needs to reference the port files shipped with
tripleo-heat-templates, so by default the tool generates the paths assuming
network-isolation.yaml will be copied into the environments/ directory of
tripleo-heat-templates.

If the generated templates were copied to the undercloud as ~/generated-templates,
and a local copy of tripleo-heat-templates exists at ~/tht, an example usage would be:

    cp ~/generated-templates/network-isolation.yaml ~/tht/environments/generated-network-isolation.yaml
    openstack overcloud deploy --templates ~/tht -e ~/tht/environments/generated-network-isolation.yaml -e ~/generated-templates/network-environment.yaml

undercloud_wizard.py
--------------------

DEPRECATED: See http://ucw.tripleo.org instead.

A PyQt GUI to help with generating undercloud.conf.  See details in the
docstring at the top of the file.

limit-fix
---------

This was a couple of templates for setting sane limits on a TripleO overcloud.
It should not be needed in any recent version of TripleO.

QuintupleO
----------

QuintupleO-related pieces (including openstackbmc) have moved to https://github.com/cybertron/openstack-virtual-baremetal
