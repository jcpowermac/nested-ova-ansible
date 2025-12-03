# Variable Reference Guide

## Variable Precedence

Ansible uses the following precedence order (highest to lowest):

1. **Extra vars** (`-e` on command line)
2. **Task vars** (in playbook tasks)
3. **Block vars** (in playbook blocks)
4. **Role vars** (`roles/*/vars/main.yml`)
5. **Play vars** (in playbooks)
6. **Host vars** (`host_vars/*`)
7. **Group vars** (`group_vars/*`)
8. **Role defaults** (`roles/*/defaults/main.yml`)

### For This Project

- **Role defaults**: Role-specific settings (e.g., `vsphere_vm_deploy_timeout`)
- **Group vars**: Deployment-wide configuration (connection, credentials, global defaults)
- **Extra vars**: Runtime overrides (topology file, debug mode, version selection)
- **Ansible Vault**: All secrets

## Variable Categories

### 1. Parent vCenter Connection

**Location**: `group_vars/all/connection.yml`

These variables define how to connect to the physical vCenter where nested VMs will be deployed.

| Variable | Description | Default | Source |
|----------|-------------|---------|--------|
| `parent_vcenter_hostname` | Parent vCenter hostname/IP | `vcenter.example.com` | `GOVC_URL` env var |
| `parent_vcenter_username` | Parent vCenter username | `administrator@vsphere.local` | `GOVC_USERNAME` env var |
| `parent_vcenter_password` | Parent vCenter password | From vault | `GOVC_PASSWORD` env var or vault |
| `parent_vcenter_datacenter` | Datacenter name | `Datacenter` | `GOVC_DATACENTER` env var |
| `parent_vcenter_datastore` | Datastore name | `datastore1` | `GOVC_DATASTORE` env var |
| `parent_vcenter_cluster` | Cluster name | `Cluster` | `GOVC_CLUSTER` env var |
| `parent_vcenter_network` | Network name | `VM Network` | `GOVC_NETWORK` env var |
| `parent_vcenter_folder` | VM folder | `nested` | `GOVC_FOLDER` env var |
| `parent_vcenter_validate_certs` | Validate SSL certs | `false` | - |
| `parent_vcenter_port` | vCenter port | `443` | - |

**Example Override**:
```bash
ansible-playbook playbooks/deploy.yml \
  -e parent_vcenter_hostname=vcenter.lab.local \
  -e parent_vcenter_datacenter=Lab-DC
```

### 2. Deployment Configuration

**Location**: `group_vars/all/vsphere_defaults.yml`

| Variable | Description | Default | Source |
|----------|-------------|---------|--------|
| `deployment_name` | Deployment/cluster name | `nested-vsphere` | `CLUSTER_NAME` env var |
| `shared_dir` | Shared directory path | `/tmp` | `SHARED_DIR` env var |
| `hosts_per_failure_domain` | ESXi hosts per failure domain | `1` | `HOSTS_PER_FAILURE_DOMAIN` env var |
| `allocated_memory_mb` | Total memory allocation | `98304` (96GB) | `MEMORY` env var |
| `allocated_vcpus` | Total vCPU allocation | `24` | `VCPUS` env var |
| `allocated_disk_gb` | Total disk allocation | `1024` (1TB) | `DISKGB` env var |

### 3. Nested vSphere Configuration

**Location**: `group_vars/all/vsphere_defaults.yml`

| Variable | Description | Default |
|----------|-------------|---------|
| `nested_vsphere_domain` | vCenter SSO domain | `vsphere.local` |
| `nested_ntp_server` | NTP server for nested VMs | `time.google.com` |
| `nested_deployment_network` | Network for nested VMs | `VM Network` |

### 4. Credentials (Vault)

**Location**: `group_vars/all/vault.yml` (encrypted)

| Variable | Description | Referenced By |
|----------|-------------|---------------|
| `vault_nested_vcenter_password` | Nested vCenter password | `nested_vcenter_password` |
| `vault_nested_esxi_password` | Nested ESXi password | `nested_esxi_password` |
| `vault_parent_vcenter_password` | Parent vCenter password (optional) | `parent_vcenter_password` |

**Referenced in**: `group_vars/all/nested_credentials.yml`

| Variable | Description | Default |
|----------|-------------|---------|
| `nested_vcenter_username` | Nested vCenter username | `administrator@vsphere.local` |
| `nested_vcenter_password` | Nested vCenter password | From vault or `NESTED_PASSWORD` env var |
| `nested_esxi_username` | Nested ESXi username | `root` |
| `nested_esxi_password` | Nested ESXi password | From vault or `NESTED_PASSWORD` env var |

### 5. vSphere Assets/Versions

**Location**: `group_vars/all/vsphere_defaults.yml`

| Variable | Description | Default |
|----------|-------------|---------|
| `vsphere_assets` | List of available vSphere versions | See below |
| `deployment_version` | Version to deploy | Latest default from assets |

**Asset Structure**:
```yaml
vsphere_assets:
  - name: "VC8.0.2.00100-22617221-ESXi8.0u2c"
    esxi_ova: "Nested_ESXi8.0u2c_Appliance_Template_v1.ova"
    vcenter_ova: "VMware-vCenter-Server-Appliance-8.0.2.00100-22617221_OVF10.ova"
    http_server: "${OVA_HTTP_SERVER}"
    default: true
```

### 6. Feature Flags

**Location**: `group_vars/all/vsphere_defaults.yml`

| Variable | Description | Default | Source |
|----------|-------------|---------|--------|
| `skip_failure_domain_tagging` | Skip OpenShift tagging | `false` | `SKIP_FAILURE_DOMAIN_TAGGING` env var |
| `enable_debug_mode` | Enable verbose debug output | `false` | `VSPHERE_DEBUG` env var |

### 7. Role-Specific Variables

Each role has its own defaults in `roles/<role_name>/defaults/main.yml`.

#### vsphere_vm_deploy

| Variable | Description | Default |
|----------|-------------|---------|
| `vsphere_vm_deploy_esxi_hosts` | List of ESXi VMs to deploy | `[]` |
| `vsphere_vm_deploy_vcenter_vms` | List of vCenter VMs to deploy | `[]` |
| `vsphere_vm_deploy_wait_timeout` | Timeout for VM deployment | `900` (15 min) |
| `vsphere_vm_deploy_vm_version` | VM hardware version | `21` (vSphere 8.0) |

#### vsphere_datacenter_config

| Variable | Description | Default |
|----------|-------------|---------|
| `vsphere_datacenter_config_drs_enabled` | Enable DRS | `true` |
| `vsphere_datacenter_config_drs_behavior` | DRS automation level | `fullyAutomated` |
| `vsphere_datacenter_config_ha_enabled` | Enable HA | `true` |

#### vsphere_host_config

| Variable | Description | Default |
|----------|-------------|---------|
| `vsphere_host_config_power_policy` | Power management policy | `high-performance` |
| `vsphere_host_config_enable_vmotion` | Enable vMotion | `true` |
| `vsphere_host_config_retry_count` | Retry count for host operations | `3` |
| `vsphere_host_config_retry_delay` | Delay between retries (seconds) | `30` |

#### vsphere_networking

| Variable | Description | Default |
|----------|-------------|---------|
| `vsphere_networking_dvswitches` | List of dvSwitches to create | `[]` |
| `vsphere_networking_portgroups` | List of port groups | `[]` |
| `vsphere_networking_host_nics` | NICs to add to dvSwitch | `['vmnic1']` |

#### vsphere_storage

| Variable | Description | Default |
|----------|-------------|---------|
| `vsphere_storage_vmfs_datastores` | VMFS datastores to create | Auto-detected |
| `vsphere_storage_nfs_shares` | NFS shares to mount | `[]` |
| `vsphere_storage_vmfs_version` | VMFS version | `6` |
| `vsphere_storage_target_disk_ctd` | Disk identifier | `vmhba0:C0:T2:L0` |

#### vsphere_tagging

| Variable | Description | Default |
|----------|-------------|---------|
| `vsphere_tagging_enabled` | Enable tagging | `true` |
| `vsphere_tagging_region_category` | Region tag category | `openshift-region` |
| `vsphere_tagging_zone_category` | Zone tag category | `openshift-zone` |

#### vsphere_host_groups

| Variable | Description | Default |
|----------|-------------|---------|
| `vsphere_host_groups_enabled` | Enable host groups | `true` |
| `vsphere_host_groups_failure_domains` | Failure domains for host groups | `[]` |

## Topology File Variables

**Location**: Provided via `-e topology_file=path/to/topology.yml`

See `examples/vsphere_topology_single_fd.yml` for full structure.

### Top-Level Structure

```yaml
deployment:
  name: "my-deployment"
  version: "VC8.0.2.00100-22617221-ESXi8.0u2c"

parent_vcenter:
  hostname: "${GOVC_URL}"
  # ... other parent vCenter settings

resources:
  total_vcpus: 24
  total_memory_mb: 98304
  total_disk_gb: 1024
  hosts_per_failure_domain: 1

nested_vcenters:
  - name: "vcenter-1"
    datacenters:
      - name: "dc1"
        region: "region1"
        clusters:
          - name: "cluster1"
            zone: "zone1"
            # ... cluster configuration
```

## Environment Variable Reference

All environment variables that can be used:

| Environment Variable | Maps To | Description |
|---------------------|---------|-------------|
| `GOVC_URL` | `parent_vcenter_hostname` | Parent vCenter URL |
| `GOVC_USERNAME` | `parent_vcenter_username` | Parent vCenter username |
| `GOVC_PASSWORD` | `parent_vcenter_password` | Parent vCenter password |
| `GOVC_DATACENTER` | `parent_vcenter_datacenter` | Parent datacenter name |
| `GOVC_DATASTORE` | `parent_vcenter_datastore` | Parent datastore name |
| `GOVC_CLUSTER` | `parent_vcenter_cluster` | Parent cluster name |
| `GOVC_NETWORK` | `parent_vcenter_network` | Network name |
| `GOVC_FOLDER` | `parent_vcenter_folder` | VM folder |
| `NESTED_PASSWORD` | `nested_vcenter_password`, `nested_esxi_password` | Nested credentials |
| `CLUSTER_NAME` | `deployment_name` | Deployment name |
| `SHARED_DIR` | `shared_dir` | Shared directory path |
| `HOSTS_PER_FAILURE_DOMAIN` | `hosts_per_failure_domain` | Hosts per FD |
| `MEMORY` | `allocated_memory_mb` | Total memory MB |
| `VCPUS` | `allocated_vcpus` | Total vCPUs |
| `DISKGB` | `allocated_disk_gb` | Total disk GB |
| `VERSION` | `deployment_version` | vSphere version to deploy |
| `SKIP_FAILURE_DOMAIN_TAGGING` | `skip_failure_domain_tagging` | Skip tagging |
| `VSPHERE_DEBUG` | `enable_debug_mode` | Enable debug mode |
| `OVA_HTTP_SERVER` | `vsphere_assets[].http_server` | OVA HTTP server |
| `NTP_SERVER` | `nested_ntp_server` | NTP server |

## Variable Override Examples

### Command Line Overrides

```bash
# Override single variable
ansible-playbook playbooks/deploy.yml -e deployment_name=my-test

# Override multiple variables
ansible-playbook playbooks/deploy.yml \
  -e deployment_name=my-test \
  -e enable_debug_mode=true \
  -e hosts_per_failure_domain=2

# Override with topology file
ansible-playbook playbooks/deploy.yml \
  -e topology_file=examples/vsphere_topology_multi_fd.yml
```

### Environment Variable Overrides

```bash
export GOVC_URL="vcenter.lab.local"
export GOVC_USERNAME="admin@vsphere.local"
export GOVC_PASSWORD="SecurePass123"
export CLUSTER_NAME="my-nested-cluster"

ansible-playbook playbooks/deploy.yml \
  -e topology_file=my_topology.yml
```

### Group Vars File Override

Create `group_vars/all/custom.yml`:

```yaml
---
# Custom overrides for my environment
deployment_name: my-custom-deployment
allocated_vcpus: 32
allocated_memory_mb: 131072  # 128 GB
enable_debug_mode: true
```

## Secret Management

### Using Vault

1. **Edit vault**:
```bash
ansible-vault edit group_vars/all/vault.yml
```

2. **View vault**:
```bash
ansible-vault view group_vars/all/vault.yml
```

3. **Encrypt vault**:
```bash
ansible-vault encrypt group_vars/all/vault.yml
```

4. **Decrypt vault** (not recommended):
```bash
ansible-vault decrypt group_vars/all/vault.yml
```

### Using Environment Variables

For CI/CD, you can use environment variables instead of vault:

```bash
export NESTED_PASSWORD="MySecurePassword123"
export GOVC_PASSWORD="ParentVCPassword"

ansible-playbook playbooks/deploy.yml \
  -e topology_file=topology.yml
```

## Best Practices

1. **Use vault for secrets**: Never commit plain-text passwords
2. **Use role defaults**: Set sensible defaults in role defaults, not group_vars
3. **Use topology file**: Define deployment topology in a dedicated file
4. **Document overrides**: Comment why you're overriding a variable
5. **Test precedence**: Verify which variable value is being used with debug mode
6. **Keep it DRY**: Use variable references, not duplication

## Troubleshooting Variables

### See All Variables

```bash
ansible-playbook playbooks/deploy.yml \
  -e topology_file=topology.yml \
  --list-vars \
  --vault-password-file=.vault_pass
```

### Debug Specific Variable

Add to your playbook:

```yaml
- name: Debug variable
  debug:
    var: parent_vcenter_hostname
```

### Check Variable Precedence

```bash
ansible-playbook playbooks/deploy.yml \
  -e topology_file=topology.yml \
  -e enable_debug_mode=true \
  -vvv
```
