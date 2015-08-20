Additional parameters and templates for configuring a TripleO overcloud to scale better.  Without these fixes, larger clouds on hardware with a lot of CPU cores will hit connection limits in things like rabbitmq and mysql.

To use, copy these files into your deployment directory and pass limits.yaml to the deploy command::

    openstack overcloud deploy --templates -e limits.yaml
