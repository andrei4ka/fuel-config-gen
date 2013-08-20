#!/usr/bin/python

import json
import urllib2
import pprint
import re
import pprint
from math import floor

#######################################################################
######################### CONFIGURATION ###############################
#######################################################################

# Provisioning
default_cobbler_profile = "centos-x86_64"

# Choose boot device
# sda for VirtualBox and vda KVM
boot_dev = "sda"

# Networking
# eth0: the internal management network, used for communication with Puppet & Cobbler
# eth1: the public network, and floating IPs assigned to VMs
# eth2: the private network, for communication between OpenStack VMs, and the bridge interface (VLANs)  

fuel_master_ip = "10.20.0.2"

public_if_name = "eth1"
public_net = "192.168.0."
public_net_mask = "255.255.255.0"
public_net_gw = "192.168.0.1"

manage_if_name = "eth0"
management_net = "10.20.0."
management_net_mask = "255.255.255.0"

private_if_name = "eth2"
private_net = "10.0.0."
private_net_mask = "255.255.255.0"

quantum = "true"

# Hostnames and Domains
domain_name = "domain.tld"

# Mapping OpenStack roles to servers IDs
# NOTE !!! if mode non HA, then you need to set server id for 'controller' role, not for 'primary-controller'
role = { 'primary-controller': '', 'controller': '1', 'compute': '2', 'quantum': '', 'storage': '' }
# Counting number of nodes with specific role. No need to edit this line
counter = { 'primary-controller': 0, 'controller': 0, 'compute': 0, 'quantum': 0, 'storage': 0 }
# Deployment scenario
# deployment_mode = "multinode" in this case /etc/puppet/modules/osnailyfacter/manifests/cluster_simple.pp will be used as template
deployment_mode = "multinode"

# Puppet master domain or IP
puppet_master = "fuel.domain.tld"

# Partitions
boot_part_size = 200
swap_size = 1024

# Logging
debug_flag=1
debug_log="debug.log"

#######################################################################
###################### FUNCTIONS DEFINITION ###########################
#######################################################################
def get_interfaces(node):
	r_if = {}
	for interface in node["meta"]["interfaces"]:
		if interface.has_key("ip") and interface.has_key("netmask"):
			r_if[interface["name"]] = {	"ip": interface["ip"], 
							"netmask": interface["netmask"], 
							"mac": interface["mac"], 
							"current_speed": interface["current_speed"],
							"max_speed": interface["max_speed"]
						}
		else:
			r_if[interface["name"]] = {	"mac": interface["mac"],
							"current_speed": interface["current_speed"],
							"max_speed": interface["max_speed"]
						}
	return r_if


		

#######################################################################
############################## MAIN ###################################
#######################################################################
response = urllib2.urlopen('http://%s:8000/api/nodes/' % fuel_master_ip)
nodes = json.load(response)
if debug_flag:
	f_handler = open(debug_log,'w')

print "nodes:"
for node in nodes:
	print "- id: %s" % node["id"]
	print "  uid: %s" % node["id"]
# Determine node hostname/fqdn/role depending on ID
	if str(node["id"]) in role['primary-controller']:
		node_role = "primary-controller"
		counter[node_role] +=1		
	elif str(node["id"]) in role['controller']:
		node_role = "controller"
		counter[node_role] +=1
	elif str(node["id"]) in role['compute']:
		node_role = "compute"
		counter[node_role] +=1
	elif str(node["id"]) in role['quantum']:
		node_role = "quantum"
		counter[node_role] +=1
	elif str(node["id"]) in role['storage']:
		node_role = "storage"
		counter[node_role] +=1
# Getting networling information
        iface = get_interfaces(node)
        last_octet = re.search(r'[0-9]{1,3}$', iface[manage_if_name]["ip"])
        if last_octet:
                last_octet = last_octet.group()
# Generic settings 
        print "  role: %s" % node_role
        print "  name: %s-%d" % (node_role,counter[node_role])
        print "  profile: %s" % default_cobbler_profile
        print "  fqdn: %s-%d.%s" % (node_role,counter[node_role],domain_name)
        print "  power_type: ssh"
        print "  power_user: root"
        print "  power_pass: /root/.ssh/bootstrap.rsa"
        print "  power_address: %s" % iface[manage_if_name]["ip"]
        print "  netboot_enabled: '1'"
        print "  puppet_master: %s" % puppet_master
# Gathering infomation about main interface (in most cases eth0)
	print "  mac: %s" % iface[manage_if_name]["mac"]
	print "  ip: %s" % iface[manage_if_name]["ip"]
	print "  network_data:"
	print "  - name: public"
	print "    ip: %s%s" % (public_net,last_octet)
	print "    dev: %s" % public_if_name
	print "    netmask: %s" % public_net_mask
	print "    gateway: %s" % public_net_gw
	print "  - name:"
	print "    - management"
	print "    - storage"
	print "    ip: %s%s" % (management_net,last_octet) 
	print "    netmask: %s" % management_net_mask
	print "    dev: %s" % manage_if_name
	print "  - name: fixed"
	print "    dev: %s" % private_if_name
	print "  public_br: br-ex"
	print "  internal_br: br-mgmt"
	print "  default_gateway: %s" % public_net_gw
	print "  name_servers: ! '\"%s\"'" % fuel_master_ip
#############################################
	print "  ks_meta:"
	print "    ks_spaces: '\"["
        print "                  {"
	print "                   \\\"type\\\": \\\"disk\\\","
	# Creating /boot on sda disk
	for disk in node["meta"]["disks"]:
		# Partitioning /dev/sda as primary boot disk
		if disk["name"] == boot_dev :
			MiB=1048576
			MB=1000000
			system_disk_size=int(disk["size"]/MiB)
			f_handler.write("System disk size MiB = %s\n" % system_disk_size)
			f_handler.write("server ID = %s\n" % node["id"])
			f_handler.write("boot_part_size = %s\n" % boot_part_size)
			pv_size = system_disk_size - boot_part_size - 2
			f_handler.write("pv_size = %s\n" % pv_size)
			free_extents = int((pv_size - swap_size)/32)
			root_lv_size = free_extents * 32
			f_handler.write("root_lv_size = %d\n" % root_lv_size)
			# Filling up json for Cobbler API
			print "                   \\\"id\\\": \\\"%s\\\"," % disk["disk"]
			print "                   \\\"volumes\\\":"
			print "                    ["
			print "                     {"
			print "                      \\\"mount\\\": \\\"/boot\\\","
			print "                      \\\"type\\\": \\\"partition\\\","
			print "                      \\\"size\\\": %d" % boot_part_size
			print "                     },"
			print "                     {"
			print "                      \\\"type\\\": \\\"mbr\\\""
			print "                     },"
			print "                     {"
			print "                      \\\"size\\\": %d," % pv_size
			print "                      \\\"type\\\": \\\"pv\\\","
			print "                      \\\"vg\\\": \\\"os\\\""
			print "                     }"
			print "                    ],"
			print "                   \\\"size\\\": %d" % system_disk_size
			print "                  },"
			print "                  {"
			print "                   \\\"type\\\": \\\"vg\\\","
			print "                   \\\"id\\\": \\\"os\\\","
			print "                   \\\"volumes\\\":"
			print "                    ["
			print "                     {"
			print "                      \\\"mount\\\":\\\"/\\\","
			print "                      \\\"type\\\": \\\"lv\\\","
			print "                      \\\"name\\\": \\\"root\\\","
			print "                      \\\"size\\\": %d" % root_lv_size 
			print "                     },"
			print "                     {"
			print "                      \\\"mount\\\": \\\"swap\\\","
			print "                      \\\"type\\\": \\\"lv\\\","
			print "                      \\\"name\\\": \\\"swap\\\","
			print "                      \\\"size\\\": %d" % int(swap_size)
			print "                     }"
			print "                    ]"
			print "                  }"
			print "                 ]\"'"
	# Generic node parameters
	print "    mco_enable: 1"
	print "    mco_vhost: mcollective"
	print "    mco_pskey: unset"
	print "    mco_user: mcollective"
	print "    puppet_enable: 0"
	print "    install_log_2_syslog: 1"
	print "    mco_password: marionette"
	print "    puppet_auto_setup: 1"
	print "    puppet_master: %s" % puppet_master
	print "    mco_auto_setup: 1"
	print "    auth_key: ! '\"\"'"
	print "    puppet_version: 2.7.19"
	print "    mco_connector: rabbitmq"
	print "    mco_host: %s" % fuel_master_ip
	print "  interfaces:"
	print "    %s:" % manage_if_name
	print "      ip_address: %s" % iface[manage_if_name]["ip"]
	print "      netmask: %s" % iface[manage_if_name]["netmask"] 
	print "      dns_name: %s-%d.%s" % (node_role,counter[node_role],domain_name)
	print "      static: '1'"
	print "      mac_address: %s" % iface[manage_if_name]["mac"] 
	print "  interfaces_extra:"
	for interface in node["meta"]["interfaces"]:
		if interface["name"] == manage_if_name:
			print "    %s:" % manage_if_name
			print "      onboot: 'yes'"
			print "      peerdns: 'no'"
		else:
			print "    %s:" % interface["name"]
			print "      onboot: 'no'"
			print "      peerdns: 'no'"
	print "  meta:"
	print "    interfaces:"
################################
	for interface in node["meta"]["interfaces"]:
		if interface["name"] == manage_if_name:
			print "    - mac: %s" % interface["mac"]
			print "      max_speed: %s" % interface["max_speed"]
			print "      name: %s" % manage_if_name
			print "      ip: %s" % interface["ip"]
			print "      netmask: %s" % interface["netmask"]
			print "      current_speed: %s" % interface["current_speed"]
		elif interface["name"] == public_if_name: 
                        print "    - mac: %s" % interface["mac"]
                        print "      max_speed: %s" % interface["max_speed"]
                        print "      name: %s" % public_if_name
                        print "      ip: %s%s" %  (public_net, last_octet)
                        print "      netmask: %s" % public_net_mask
                        print "      current_speed: %s" % interface["current_speed"]
		elif interface["name"] == private_if_name:
                        print "    - mac: %s" % interface["mac"]
                        print "      max_speed: %s" % interface["max_speed"]
                        print "      name: %s" % private_if_name
                        print "      ip: %s%s" %  (private_net, last_octet)
                        print "      netmask: %s" % private_net_mask
                        print "      current_speed: %s" % interface["current_speed"]
	print "    disks:"
	for disk in node["meta"]["disks"]:
		print "    - model: %s" % disk["model"]
		print "      disk: %s" % disk["disk"]
		print "      name: %s" % disk["name"]
		print "      size: %s" % disk["size"]
	print "    system:"
	print "      serial: '0'"
	print "      version: '1.2'"
	print "      fqdn: bootstrap"
	print "      family: Virtual Machine"
	print "      manufacturer: VirtualBox"
	print "  error_type:"
	
# Attributes:
print "attributes:"
## Deployment parameters
print "  master_ip: %s" % fuel_master_ip
print "  deployment_id: 1"
print "  deployment_source: cli"
print "  deployment_engine: nailyfact"
print "  deployment_mode: %s" % deployment_mode
## Nova compute and Hypervisor related staff
print "  start_guests_on_host_boot: true"
print "  compute_scheduler_driver: nova.scheduler.multi.MultiSchedule"
print "  use_cow_images: true"
print "  libvirt_type: qemu"
## Network parameters
print "  management_vip: %s200" % management_net
print "  public_vip: %s200" % public_net
print "  auto_assign_floating_ip: false"
print "  create_networks: true"
print "  dns_nameservers: %s" % fuel_master_ip 
### Nova network related staff
print "  novanetwork_parameters:"
print "    vlan_start: 500"
print "    network_manager: VlanManager"
print "    network_size: 24"
print "  floating_network_range: %s0/24" % public_net
print "  fixed_network_range: 10.20.2.0/24"
### Quantum related staff
print "  quantum: %s" % quantum
print "  quantum_parameters:"
print "    tenant_network_type: gre"
print "    segment_range: ! '300:500'"
print "    metadata_proxy_shared_secret: quantum"
## OpenStack related staff
print "  mysql:"
print "    root_password: root"
print "  glance:"
print "    db_password: glance"
print "    user_password: glance"
print "  swift:"
print "    user_password: swift_pass"
print "  nova:"
print "    db_password: nova"
print "    user_password: nova"
print "  access:"
print "    password: admin"
print "    user: admin"
print "    tenant: admin"
print "    email: admin@example.org"
print "  keystone:"
print "    db_password: keystone"
print "    admin_token: nova"
print "  quantum_access:"
print "    user_password: quantum"
print "    db_password: quantum"
print "  rabbit:"
print "    password: nova"
print "    user: nova"
print "  cinder:"
print "    password: cinder"
print "    user: cinder"
print "  ntp_servers:"
print "  - pool.ntp.org"
## Cinder
print "  cinder_nodes:"
print "  - controller"
## Syslog Parameters
print "  base_syslog:"
print "    syslog_port: '514'"
print "    syslog_server: %s" % fuel_master_ip
print "  syslog:"
print "    syslog_port: '514'"
print "    syslog_transport: udp"
print "    syslog_server: ''"
# Engine:
print "engine:"
print "  url: http://localhost/cobbler_api"
print "  username: cobbler"
print "  password: cobbler"
