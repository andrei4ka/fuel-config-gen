fuel-config-gen
======

It's simple python script that is used to generate yaml configuration file for deployment of OpenStack using Fuel 3.1 

##Requirements
- Brain to get the stuff working )))

##Installation
1. Download the script on Fuel-PM node
2. Ensure that Fuel API is accessible by running the following command from Fuel-PM node:
```
curl http://127.0.0.1:8000/api/nodes/
```

##Configuration
To change provisioning/deployment mode you need to modify the script itself. The script has a lot of comments and in most cases you should have no questions.

**1.** Once you boot your Fuel slave nodes in bootstrap mode, you need to get a list of discovered nodes by running the following command from your Fuel-PM
<pre>
for i in `cat /var/lib/dnsmasq/dnsmasq.leases | awk '{print $3}'`;do echo -n "$i "; \
ssh $i 'grep identity' /etc/mcollective/server.cfg 2>/dev/null;done
</pre>
**2.** Open the script using desired text editor:
```
vim fuel-config-gen.py
```
**3.** Now you need to modify **role** array and assign servers roles using IDs of discovered servers. 
Here is example how it should look like if you have:
<pre>
  1 x Controller (ID=1)
  3 x Compute nodes (IDs=2,3,4)
</pre>
<pre>
# Mapping OpenStack roles to servers IDs
# NOTE !!! if mode non HA, then you need to sed server id for 'controller' role, not for 'primary-controller'
role = { 'primary-controller': '', 'controller': '1', 'compute': '2,3,4', 'quantum': '', 'storage': '' }
</pre>
4. If you are going to deploy OpenStack on virtual machines running under VirtualBox you need to set:
<pre>
boot_dev = "sda"
</pre>
if you use KVM then it should be:
<pre>
boot_dev = "vda"
</pre>

##Basic usage examples

**1.** Generate config:
```
python fuel-config-gen.py > example.yaml
```
**2.** Provisioning servers:
```
astute -f example.yaml -c provision
```
**3.** Deploy OpenStack:
```
astute -f example.yaml -c deploy
```

##Limitations
**1.** HA mode isn't supported yet
**2.** Servers with multiple hardrives probably won't boot
**3.** Nova network isn't supported yet (OpenStack will be deployed successfully, but instances creation will fail due to networking) and Quantum is used by default
**4.** A lot of other stuff...))
