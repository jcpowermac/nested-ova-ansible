# Role Documentation

This document provides detailed information about each role in the nested vSphere Ansible project.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Role Dependencies](#role-dependencies)
- [vsphere_vm_deploy](#vsphere_vm_deploy)
- [vsphere_datacenter_config](#vsphere_datacenter_config)
- [vsphere_host_config](#vsphere_host_config)
- [vsphere_networking](#vsphere_networking)
- [vsphere_storage](#vsphere_storage)
- [vsphere_tagging](#vsphere_tagging)
- [vsphere_host_groups](#vsphere_host_groups)

## Architecture Overview

The project is organized into 7 focused roles that execute in sequence:

```
Deployment Flow:
┌─────────────────────────────────────────────────────────────┐
│ 1. vsphere_vm_deploy                                        │
│    Deploy ESXi and vCenter VMs from OVA/content library     │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│ 2. vsphere_datacenter_config                                │
│    Create datacenters, clusters, configure DRS/HA           │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│ 3. vsphere_host_config                                      │
│    Add ESXi hosts to vCenter clusters                       │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│ 4. vsphere_networking                                       │
│    Create distributed vSwitch and port groups               │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│ 5. vsphere_storage                                          │
│    Configure VMFS and NFS datastores                        │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│ 6. vsphere_tagging                                          │
│    Create OpenShift region/zone tags                        │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│ 7. vsphere_host_groups                                      │
│    Create DRS host groups (if zone_type: HostGroup)         │
└─────────────────────────────────────────────────────────────┘
```

## Role Dependencies

| Role | Depends On | Optional |
|------|------------|----------|
| vsphere_vm_deploy | None (runs first) | No |
| vsphere_datacenter_config | vsphere_vm_deploy | No |
| vsphere_host_config | vsphere_datacenter_config | No |
| vsphere_networking | vsphere_host_config | Yes (if no dvSwitch) |
| vsphere_storage | vsphere_host_config | Yes (if no datastores) |
| vsphere_tagging | vsphere_datacenter_config | Yes (if tagging disabled) |
| vsphere_host_groups | vsphere_host_config, vsphere_tagging | Yes (only for HostGroup zones) |

---

## vsphere_vm_deploy

**Purpose:** Deploy ESXi and vCenter VMs from OVA files or content library templates

**Source Files:** `esxinested.yml`, `vcnested.yml`, `getcerts.yml` (v1)

### Key Features

- ✅ **Idempotent**: Checks if VMs exist before deploying
- ✅ **Flexible Sources**: Deploy from OVA URLs or content library
- ✅ **Hardware Customization**: Configure CPU, memory, disk per host
- ✅ **Network Configuration**: Static IP configuration with genmask support
- ✅ **Wait for Ready**: Polls for IP address and service availability

### Tasks

1. **Deploy ESXi Hosts** (`tasks/deploy_esxi.yml`)
   - Check if ESXi VM exists
   - Deploy from OVA template or content library
   - Configure hardware (CPU, memory, disk, nested HV)
   - Power on and wait for IP address
   - Wait for ESXi web UI to be ready

2. **Deploy vCenter VMs** (`tasks/deploy_vcenter.yml`)
   - Check if vCenter VM exists
   - Deploy from content library (recommended) or OVA
   - Configure vApp properties (IP, DNS, NTP, SSO)
   - Power on and wait for vCenter services
   - Retrieve and save vCenter certificates

3. **Get Certificates** (`tasks/get_certificates.yml`)
   - Retrieve vCenter SSL certificates
   - Save for later use in ESXi configuration

### Key Variables

```yaml
# Parent vCenter connection
vsphere_vm_deploy_parent_vcenter:
  hostname: vcenter.example.com
  username: administrator@vsphere.local
  password: "{{ vault_password }}"
  datacenter: dc1
  datastore: datastore1

# ESXi hosts to deploy
vsphere_vm_deploy_esxi_hosts:
  - name: esxi01
    ip: 192.168.1.10
    cpu: 8
    memory_mb: 65536
    disk_gb: 200

# vCenter VMs to deploy
vsphere_vm_deploy_vcenter_vms:
  - name: vcsa01
    hostname: vcsa01.lab.local
    ip: 192.168.1.5
    cpu: 8
    memory_mb: 24576

# Content library (recommended)
vsphere_vm_deploy_content_library:
  name: nested-templates
  esxi_template_item: Nested_ESXi8.0u2c
  vcenter_template_item: vCenter-8.0.2

# Timeout settings
vsphere_vm_deploy_wait_timeout: 900  # seconds
vsphere_vm_deploy_wait_for_ip: true
```

### Usage Example

```yaml
- name: Deploy VMs
  ansible.builtin.import_role:
    name: vsphere_vm_deploy
  vars:
    vsphere_vm_deploy_esxi_hosts: "{{ topology.esxi_hosts }}"
    vsphere_vm_deploy_vcenter_vms: "{{ topology.vcenter_vms }}"
```

### Files Modified

- Creates VMs on parent vCenter
- Writes certificates to `/tmp/` (if enabled)

---

## vsphere_datacenter_config

**Purpose:** Configure vCenter datacenters, clusters, DRS, and HA

**Source Files:** First half of `addhosts_vcenter.yml` (v1)

### Key Features

- ✅ **Idempotent**: Checks existence before creating
- ✅ **DRS Configuration**: Automated DRS with configurable automation level
- ✅ **HA Configuration**: vSphere HA with admission control
- ✅ **Resource Pools**: Create resource pools for organization
- ✅ **Graceful Degradation**: Continues if advanced HA settings fail

### Tasks

1. **Skip if Disabled** (`tasks/main.yml`)
   - Check if configuration is enabled

2. **Validate vCenter Connection** (`tasks/main.yml`)
   - Assert vCenter credentials exist

3. **Create Datacenters** (`tasks/create_datacenter.yml`)
   - Check if datacenter exists
   - Create if missing
   - Add to datacenter list

4. **Configure Clusters** (`tasks/configure_cluster.yml`)
   - Check if cluster exists
   - Create cluster with DRS/HA settings
   - Enable DRS (Distributed Resource Scheduler)
   - Enable HA (High Availability)
   - Configure advanced HA settings (best effort)
   - Create resource pools

### Key Variables

```yaml
# vCenter connection
vsphere_datacenter_config_vcenter:
  hostname: vcsa01.lab.local
  username: administrator@vsphere.local
  password: "{{ vault_password }}"

# Datacenters and clusters
vsphere_datacenter_config_datacenters:
  - name: dc1
    clusters:
      - name: cluster1
        drs_enabled: true
        drs_vmotion_rate: 3
        ha_enabled: true
        ha_admission_control: true
        ha_host_monitoring: enabled
        resource_pools:
          - name: test-pool
            cpu_shares: normal
            mem_shares: normal

# Feature flags
vsphere_datacenter_config_enabled: true
vsphere_datacenter_config_debug: false

# DRS defaults
vsphere_datacenter_config_drs_enabled: true
vsphere_datacenter_config_drs_vmotion_rate: 3
vsphere_datacenter_config_drs_default_vm_behavior: fullyAutomated

# HA defaults
vsphere_datacenter_config_ha_enabled: true
vsphere_datacenter_config_ha_admission_control: true
vsphere_datacenter_config_ha_host_monitoring: enabled
vsphere_datacenter_config_ha_vm_monitoring: vmMonitoringOnly
```

### Usage Example

```yaml
- name: Configure datacenter infrastructure
  ansible.builtin.import_role:
    name: vsphere_datacenter_config
  vars:
    vsphere_datacenter_config_vcenter: "{{ vcenter }}"
    vsphere_datacenter_config_datacenters: "{{ vcenter.datacenters }}"
```

---

## vsphere_host_config

**Purpose:** Add ESXi hosts to vCenter and configure host settings

**Source Files:** Second half of `addhosts_vcenter.yml` (v1)

### Key Features

- ✅ **Idempotent**: Checks if host already added
- ✅ **Retry Logic**: Configurable retries for flaky host addition
- ✅ **Lockdown Mode**: Configure lockdown mode (disabled by default)
- ✅ **Power Management**: Configure power management policies
- ✅ **vMotion**: Configure vMotion networking

### Tasks

1. **Skip if Disabled** (`tasks/main.yml`)
   - Check if host configuration is enabled

2. **Validate vCenter Connection** (`tasks/main.yml`)
   - Assert vCenter credentials exist

3. **Add Hosts to Cluster** (`tasks/add_host.yml`)
   - Check if host already in cluster
   - Add host to cluster with retries
   - Handle "already exists" gracefully
   - Configure lockdown mode
   - Set power management policy
   - Configure vMotion networking

### Key Variables

```yaml
# vCenter connection
vsphere_host_config_vcenter:
  hostname: vcsa01.lab.local
  username: administrator@vsphere.local
  password: "{{ vault_password }}"

# ESXi hosts to add
vsphere_host_config_esxi_hosts:
  - hostname: 192.168.1.10
    username: root
    password: "{{ vault_esxi_password }}"
    datacenter: dc1
    cluster: cluster1
    lockdown_mode: disabled
    power_policy: balanced

# Retry settings
vsphere_host_config_retry_count: 5
vsphere_host_config_retry_delay: 30  # seconds

# Feature flags
vsphere_host_config_enabled: true
vsphere_host_config_configure_lockdown: false
vsphere_host_config_configure_power_mgmt: false
vsphere_host_config_configure_vmotion: false
```

### Usage Example

```yaml
- name: Add ESXi hosts to vCenter
  ansible.builtin.import_role:
    name: vsphere_host_config
  vars:
    vsphere_host_config_vcenter: "{{ vcenter }}"
    vsphere_host_config_esxi_hosts: "{{ vcenter.esxi_hosts }}"
```

---

## vsphere_networking

**Purpose:** Configure distributed vSwitch and port groups

**Source Files:** `dvs_hosts_vcenter.yml` (v1)

### Key Features

- ✅ **Idempotent**: Checks if dvSwitch exists
- ✅ **Port Groups**: Create multiple port groups with VLAN tagging
- ✅ **Host Uplinks**: Add ESXi hosts to dvSwitch
- ✅ **Propagation Delay**: Configurable pause after creation

### Tasks

1. **Skip if Disabled** (`tasks/main.yml`)
   - Check if networking configuration is enabled

2. **Validate vCenter Connection** (`tasks/main.yml`)
   - Assert vCenter credentials exist

3. **Create Distributed vSwitch** (`tasks/create_dvswitch.yml`)
   - Check if dvSwitch exists
   - Create dvSwitch with settings
   - Configure MTU, uplinks, discovery protocol
   - Add ESXi hosts to dvSwitch
   - Create port groups
   - Pause for propagation

### Key Variables

```yaml
# vCenter connection
vsphere_networking_vcenter:
  hostname: vcsa01.lab.local
  username: administrator@vsphere.local
  password: "{{ vault_password }}"

# Distributed vSwitches
vsphere_networking_dvswitches:
  - name: dvSwitch
    datacenter: dc1
    version: 7.0.0
    mtu: 1500
    uplinks: 2
    discovery_protocol: lldp
    discovery_operation: listen
    port_groups:
      - name: VM Network
        vlan: 0
        num_ports: 128
      - name: Storage Network
        vlan: 100
        num_ports: 64
    hosts:
      - hostname: 192.168.1.10
        uplink1: vmnic1
        uplink2: vmnic2

# Timing settings
vsphere_networking_pause_after_dvs_create: 10  # seconds
```

### Usage Example

```yaml
- name: Configure networking
  ansible.builtin.import_role:
    name: vsphere_networking
  vars:
    vsphere_networking_vcenter: "{{ vcenter }}"
    vsphere_networking_dvswitches: "{{ vcenter.dvswitches }}"
```

---

## vsphere_storage

**Purpose:** Configure VMFS and NFS datastores

**Source Files:** `create_datastore.yml` (v1)

### Key Features

- ✅ **Idempotent**: Checks if datastore exists
- ✅ **VMFS Support**: Create local VMFS datastores
- ✅ **NFS Support**: Mount NFS v3/v4.1 shares
- ✅ **Per-Host Configuration**: Different datastores per host

### Tasks

1. **Skip if Disabled** (`tasks/main.yml`)
   - Check if storage configuration is enabled

2. **Validate vCenter Connection** (`tasks/main.yml`)
   - Assert vCenter credentials exist

3. **Create VMFS Datastores** (`tasks/create_vmfs_datastore.yml`)
   - Get ESXi disk information
   - Find target disk by CTD identifier
   - Check if datastore exists
   - Create VMFS datastore on disk

4. **Mount NFS Datastores** (`tasks/mount_nfs_datastore.yml`)
   - Check if NFS datastore exists
   - Mount NFS share to ESXi host
   - Configure read-only if specified

### Key Variables

```yaml
# vCenter connection
vsphere_storage_vcenter:
  hostname: vcsa01.lab.local
  username: administrator@vsphere.local
  password: "{{ vault_password }}"

# VMFS datastores
vsphere_storage_vmfs_datastores:
  - datastore_name: vmfs-local
    esxi_hostname: 192.168.1.10
    disk_ctd: "0:1"  # Controller:Target:Disk
    vmfs_version: 6

# NFS datastores
vsphere_storage_nfs_datastores:
  - datastore_name: nfs-storage
    nfs_server: 192.168.1.100
    nfs_path: /export/storage
    nfs_version: 3  # or nfs41
    esxi_hostname: 192.168.1.10
    read_only: false

# Defaults
vsphere_storage_vmfs_version: 6
vsphere_storage_nfs_version: 3
```

### Usage Example

```yaml
- name: Configure storage
  ansible.builtin.import_role:
    name: vsphere_storage
  vars:
    vsphere_storage_vcenter: "{{ fd.vcenter }}"
    vsphere_storage_vmfs_datastores: "{{ fd.vmfs_datastores }}"
    vsphere_storage_nfs_datastores: "{{ fd.nfs_datastores }}"
```

---

## vsphere_tagging

**Purpose:** Create and attach OpenShift region/zone tags

**Source Files:** `tagging.yml` (v1)

### Key Features

- ✅ **Idempotent**: Checks if tags exist
- ✅ **Skip Logic**: Skip tags starting with `-`
- ✅ **Flexible Types**: Support ComputeCluster and HostGroup zone types
- ✅ **Retry Logic**: Configurable retries for tag operations

### Tasks

1. **Skip if Disabled** (`tasks/main.yml`)
   - Check if tagging is enabled

2. **Validate vCenter Connection** (`tasks/main.yml`)
   - Assert vCenter credentials exist

3. **Create Tag Categories** (`tasks/create_categories.yml`)
   - Create `openshift-region` category
   - Create `openshift-zone` category
   - Set cardinality to SINGLE

4. **Create Region Tags** (`tasks/create_region_tags.yml`)
   - Check if region is defined and not skipped
   - Create region tag in region category

5. **Create Zone Tags** (`tasks/create_zone_tags.yml`)
   - Check if zone is defined and not skipped
   - Create zone tag in zone category

6. **Attach Zone Tags** (`tasks/attach_zone_tags.yml`)
   - Determine object type (ComputeCluster or HostGroup)
   - Attach zone tag to appropriate object
   - Skip if zone_type is HostGroup (handled by vsphere_host_groups)

### Key Variables

```yaml
# vCenter connection
vsphere_tagging_vcenter:
  hostname: vcsa01.lab.local
  username: administrator@vsphere.local
  password: "{{ vault_password }}"

# Region and failure domains
vsphere_tagging_region: region-1
vsphere_tagging_failure_domains:
  - name: zone-a
    region: region-1
    zone: zone-a
    zone_type: ComputeCluster  # or HostGroup
    datacenter: dc1
    cluster: cluster1

# Retry settings
vsphere_tagging_retry_count: 3
vsphere_tagging_retry_delay: 10

# Type mapping
vsphere_tagging_type_map:
  ComputeCluster: ClusterComputeResource
  HostGroup: ClusterComputeResource
  Datacenter: Datacenter
```

### Usage Example

```yaml
- name: Configure OpenShift tags
  ansible.builtin.import_role:
    name: vsphere_tagging
  vars:
    vsphere_tagging_vcenter: "{{ vcenter }}"
    vsphere_tagging_failure_domains: "{{ topology.failure_domains }}"
    vsphere_tagging_region: "{{ topology.region }}"
```

### Skip Tagging

To skip tagging for a specific failure domain, prefix region or zone with `-`:

```yaml
failure_domains:
  - name: zone-a
    region: "-us-east-1"  # Skip region tagging
    zone: "-zone-a"       # Skip zone tagging
```

---

## vsphere_host_groups

**Purpose:** Create DRS host groups for HostGroup zone affinity

**Source Files:** `host_groups.yml` (v1)

### Key Features

- ✅ **Idempotent**: Checks if host group exists
- ✅ **Filtered**: Only creates groups for zone_type: HostGroup
- ✅ **Zone Affinity**: Enables strict zone pinning for OpenShift VMs

### Tasks

1. **Skip if Disabled** (`tasks/main.yml`)
   - Check if host groups are enabled

2. **Validate vCenter Connection** (`tasks/main.yml`)
   - Assert vCenter credentials exist

3. **Filter Failure Domains** (`tasks/main.yml`)
   - Select only zone_type: HostGroup

4. **Create DRS Host Groups** (`tasks/main.yml`)
   - Create host group with zone name
   - Add specified ESXi hosts to group
   - Associate with cluster

### Key Variables

```yaml
# vCenter connection
vsphere_host_groups_vcenter:
  hostname: vcsa01.lab.local
  username: administrator@vsphere.local
  password: "{{ vault_password }}"

# Failure domains (only HostGroup type processed)
vsphere_host_groups_failure_domains:
  - name: zone-a
    zone: zone-a
    zone_type: HostGroup
    datacenter: dc1
    cluster: cluster1
    hosts:
      - 192.168.1.10
      - 192.168.1.11
      - 192.168.1.12

# Feature flags
vsphere_host_groups_enabled: true
vsphere_host_groups_debug: false
```

### Usage Example

```yaml
- name: Create DRS host groups
  ansible.builtin.import_role:
    name: vsphere_host_groups
  vars:
    vsphere_host_groups_vcenter: "{{ vcenter }}"
    vsphere_host_groups_failure_domains: "{{ topology.failure_domains }}"
```

### HostGroup vs ComputeCluster

**ComputeCluster** (default):
- Tags the entire cluster
- OpenShift distributes VMs across cluster
- Simpler configuration

**HostGroup**:
- Creates DRS host group with specific hosts
- Tags the host group (not cluster)
- OpenShift pins VMs to specific hosts
- Enables strict zone isolation

---

## Best Practices

### Variable Naming

All role variables use the pattern `<role_name>_<variable>`:

```yaml
# Good
vsphere_vm_deploy_wait_timeout: 900
vsphere_tagging_retry_count: 3

# Bad (global namespace pollution)
wait_timeout: 900
retry_count: 3
```

### Module Defaults

Roles use `module_defaults` to avoid repeating vCenter credentials:

```yaml
module_defaults:
  group/vmware:
    hostname: "{{ vsphere_tagging_vcenter.hostname }}"
    username: "{{ vsphere_tagging_vcenter.username }}"
    password: "{{ vsphere_tagging_vcenter.password }}"
    validate_certs: "{{ vsphere_tagging_vcenter.validate_certs }}"
```

### Idempotency Pattern

All roles follow this pattern:

```yaml
- name: Check if resource exists
  community.vmware.vmware_*_info:
    ...
  register: resource_info
  failed_when: false
  changed_when: false

- name: Create resource
  community.vmware.vmware_*:
    state: present
  when: resource_info.* is not defined or resource_info.* | length == 0
```

### Error Handling

Use retry logic for flaky operations:

```yaml
- name: Add host
  community.vmware.vmware_host:
    ...
  retries: "{{ vsphere_host_config_retry_count }}"
  delay: "{{ vsphere_host_config_retry_delay }}"
  register: result
  until: result is succeeded
```

## See Also

- [VARIABLES.md](VARIABLES.md) - Complete variable reference
- [TESTING.md](TESTING.md) - Testing each role
- [DEVELOPMENT.md](DEVELOPMENT.md) - Development workflow
