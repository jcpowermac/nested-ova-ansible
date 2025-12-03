## Quick Start - DHCP Testing

This guide shows the **simplest way to test** the rewrite with DHCP (no static IPs).

### Prerequisites

1. **DHCP server** on your network
2. **Parent vCenter** with:
   - ESXi host
   - Datastore with free space
   - Network with DHCP enabled
   - ESXi and vCenter OVA templates uploaded
3. **Vault password** file

### Step 1: Set up vault (one time)

```bash
# Create vault password file
echo "your-secure-password" > .vault_pass
chmod 600 .vault_pass

# Create vault file
cat > group_vars/all/vault.yml << EOF
---
vault_esxi_password: "VMware1!"
vault_vcenter_password: "VMware1!"
vault_parent_vcenter_password: "your-parent-vcenter-password"
EOF

# Encrypt it
ansible-vault encrypt group_vars/all/vault.yml
```

### Step 2: Configure parent vCenter connection

```bash
cat > group_vars/all/connection.yml << EOF
---
vsphere_parent_vcenter:
  hostname: parent-vcenter.example.com
  username: administrator@vsphere.local
  password: "{{ vault_parent_vcenter_password }}"
  datacenter: YourDatacenter
  cluster: YourCluster
  esxi_host: esxi-host.example.com
  datastore: YourDatastore
  folder: /nested-lab
  network: "VM Network"  # Must have DHCP enabled
  validate_certs: false
EOF
```

### Step 3: Run preflight check

```bash
ansible-playbook playbooks/preflight.yml \
  -e topology_file=examples/vsphere_topology_dhcp_minimal.yml
```

### Step 4: Deploy!

```bash
ansible-playbook playbooks/deploy_nested_vsphere.yml \
  -e topology_file=examples/vsphere_topology_dhcp_minimal.yml
```

### How DHCP Works

1. **ESXi VMs**: Boot with no IP config → get DHCP → report IP via VMware Tools
2. **vCenter VMs**: Configured with `guestinfo.cis.appliance.net.mode=dhcp` → boot → get DHCP
3. **Playbook**: Waits for VMs to report their IPs (up to 15 minutes)
4. **Output**: IPs are displayed in debug mode and stored in hostvars

### Troubleshooting

**VMs not getting IPs:**
```bash
# Check if DHCP is working on the network
# Check VMware Tools is running in the VMs
# Increase timeout: -e vm_wait_timeout=1800
```

**Can't add ESXi to vCenter:**
```bash
# The playbook needs the DHCP IP of the ESXi host
# Check debug output for: "ESXi esxi01 got IP: 192.168.1.x"
# If IP is not detected, manually check in vCenter
```

**Inventory is complex:**
```bash
# The inventory is intentionally minimal - just localhost
# All deployed VMs are tracked in hostvars dynamically
# No need to manually manage inventory files
```

### Differences from Static IP

**Old (Static IP - examples/vsphere_topology_hostgroup.yml):**
- Every VM has `ip:`, `mask:`, `gw:`, `dns:` fields
- 9 ESXi hosts = 9 × 4 fields = 36 config lines just for IPs
- Complex, error-prone

**New (DHCP - examples/vsphere_topology_dhcp_minimal.yml):**
- Just `name:` and resource specs
- Network handles IP assignment
- Simple, matches your actual usage

### Converting Your Topology to DHCP

If you have an existing topology file with static IPs, just **remove** these fields:

```yaml
# REMOVE:
ip: 192.168.1.10
mask: 255.255.255.0
gw: 192.168.1.1
dns: 192.168.1.1
domain: lab.local
```

The VMs will automatically use DHCP instead.

### Cleaning Up

```bash
ansible-playbook playbooks/destroy_nested_vsphere.yml \
  -e deployment_name=dhcp-test
```
