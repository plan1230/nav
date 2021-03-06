#
# Copyright (C) 2011-2015 Uninett AS
#
# This file is part of Network Administration Visualized (NAV).
#
# NAV is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License version 3 as published by
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.  You should have received a copy of the GNU General Public License
# along with NAV. If not, see <http://www.gnu.org/licenses/>.
#
"""Util functions for the PortAdmin"""
from __future__ import unicode_literals
import re
import logging
from operator import attrgetter

from django.template import loader

from nav.django.utils import is_admin
from nav.portadmin.config import CONFIG
from nav.portadmin.management import ManagementFactory
from nav.portadmin.vlan import FantasyVlan
from nav.enterprise.ids import VENDOR_ID_CISCOSYSTEMS


_logger = logging.getLogger("nav.web.portadmin")


def get_and_populate_livedata(netbox, interfaces):
    """Fetch live data from netbox"""
    handler = ManagementFactory.get_instance(netbox)
    live_ifaliases = handler.get_all_if_alias()
    live_vlans = handler.get_all_vlans()
    live_operstatus = dict(handler.get_netbox_oper_status())
    live_adminstatus = dict(handler.get_netbox_admin_status())
    update_interfaces_with_snmpdata(interfaces, live_ifaliases, live_vlans,
                                    live_operstatus, live_adminstatus)

    return handler


def update_interfaces_with_snmpdata(interfaces, ifalias, vlans, operstatus,
                                    adminstatus):
    """
    Update the interfaces with data gathered via snmp.
    """
    for interface in interfaces:
        if interface.ifindex in ifalias:
            interface.ifalias = ifalias[interface.ifindex]
        if interface.ifindex in vlans:
            interface.vlan = vlans[interface.ifindex]
        if interface.ifindex in operstatus:
            interface.ifoperstatus = operstatus[interface.ifindex]
        if interface.ifindex in adminstatus:
            interface.ifadminstatus = adminstatus[interface.ifindex]


def find_and_populate_allowed_vlans(account, netbox, interfaces, factory):
    """Find allowed vlans and indicate which interface can be edited"""
    allowed_vlans = find_allowed_vlans_for_user_on_netbox(account, netbox,
                                                          factory)
    set_editable_on_interfaces(netbox, interfaces, allowed_vlans)
    return allowed_vlans


def find_allowed_vlans_for_user_on_netbox(account, netbox, factory=None):
    """Find allowed vlans for this user on this netbox

    ::returns list of Fantasyvlans

    """
    netbox_vlans = find_vlans_on_netbox(netbox, factory=factory)

    if CONFIG.is_vlan_authorization_enabled():
        if is_admin(account):
            allowed_vlans = netbox_vlans
        else:
            all_allowed_vlans = find_allowed_vlans_for_user(account)
            allowed_vlans = intersect(all_allowed_vlans, netbox_vlans)
    else:
        allowed_vlans = netbox_vlans

    return sorted(allowed_vlans, key=attrgetter('vlan'))


def find_vlans_on_netbox(netbox, factory=None):
    """Find all the vlans on this netbox

    fac: already instantiated factory instance. Use this if possible
    to enable use of cached values

    :returns: list of FantasyVlans
    :rtype: list
    """
    if not factory:
        factory = ManagementFactory.get_instance(netbox)
    return factory.get_netbox_vlans()


def find_allowed_vlans_for_user(account):
    """Find the allowed vlans for this user based on organization"""
    allowed_vlans = []
    for org in account.organizations.all():
        allowed_vlans.extend(find_vlans_in_org(org))

    defaultvlan = CONFIG.find_default_vlan()
    if defaultvlan and defaultvlan not in allowed_vlans:
        allowed_vlans.append(defaultvlan)

    return allowed_vlans


def set_editable_on_interfaces(netbox, interfaces, vlans):
    """
    Set a flag on the interface to indicate if user is allowed to edit it.
    """
    vlan_numbers = [vlan.vlan for vlan in vlans]

    for interface in interfaces:
        iseditable = (interface.vlan in vlan_numbers and netbox.read_write)
        if iseditable:
            interface.iseditable = True
        else:
            interface.iseditable = False


def intersect(list_a, list_b):
    """Find intersection between two lists"""
    return list(set(list_a) & set(list_b))


def find_vlans_in_org(org):
    """Find all vlans in an organization and child organizations

    :returns: list of FantasyVlans
    :rtype: list
    """
    vlans = list(org.vlan_set.all())
    for child_org in org.organization_set.all():
        vlans.extend(find_vlans_in_org(child_org))
    return [FantasyVlan(x.vlan, x.net_ident) for x in list(set(vlans)) if
            x.vlan]


def check_format_on_ifalias(ifalias):
    """Verify that format on ifalias is correct if it is defined in config"""
    if not ifalias:
        return True
    ifalias_format = CONFIG.get_ifaliasformat()
    if ifalias_format:
        ifalias_format = re.compile(ifalias_format)
        if ifalias_format.match(ifalias):
            return True
        else:
            _logger.error('Wrong format on ifalias: %s', ifalias)
            return False
    else:
        return True


def get_aliastemplate():
    """Fetch template for displaying ifalias format as help to user"""
    return loader.get_template("portadmin/aliasformat.html")


def save_to_database(interfaces):
    """Save changes for all interfaces to database"""
    for interface in interfaces:
        interface.save()


def filter_vlans(target_vlans, old_vlans, allowed_vlans):
    """Return a list of vlans that matches following criteria

    - All target vlans should be set if the vlan is in allowed_vlans
    - Remove the old_vlans if they are in allowed_vlans
    """
    return list((set(target_vlans) & set(allowed_vlans)) |
                (set(old_vlans) - set(allowed_vlans)))


def should_check_access_rights(account):
    """Return boolean indicating that this user is restricted"""
    return (CONFIG.is_vlan_authorization_enabled() and
            not is_admin(account))


def mark_detained_interfaces(interfaces):
    """Mark interfaces detained in Arnold
    :type interfaces: list[nav.models.manage.Interface]
    """
    for interface in interfaces:
        # If interface is administratively down, check if Arnold is the source
        if interface.ifadminstatus == 2 and interface.identity_set.filter(
                status='disabled').count() > 0:
            interface.detained = True
        if interface.identity_set.filter(status='quarantined').count() > 0:
            interface.detained = True


def add_dot1x_info(interfaces, handler):
    """Add information about dot1x state for interfaces"""

    # Skip if port access control is not enabled (and thus not dot1x)
    if not handler.is_port_access_control_enabled():
        return

    dot1x_states = handler.get_dot1x_enabled_interfaces()

    url_template = CONFIG.get_dot1x_external_url()
    for interface in interfaces:
        interface.dot1xenabled = dot1x_states.get(interface.ifindex)
        if url_template:
            interface.dot1x_external_url = url_template.format(
                netbox=interface.netbox,
                interface=interface)


def is_cisco(netbox):
    """Returns true if netbox is of vendor cisco
    :type netbox: manage.Netbox
    """
    return netbox.type.get_enterprise_id() == VENDOR_ID_CISCOSYSTEMS
