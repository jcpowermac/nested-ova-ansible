# vsphere_vm_deploy

Deploy nested ESXi and vCenter VMs on vSphere infrastructure.

## Description

This role deploys nested ESXi hosts and vCenter appliances on a parent vSphere environment. It handles:

- ESXi VM deployment from templates
- vCenter appliance deployment from content library
- Network configuration
- Resource allocation (CPU, memory, disk)
- SSL certificate retrieval
- Idempotent operations (check-before-create)

## Requirements

- Ansible 2.15 or higher
- Python 3.9 or higher
- Collections:
  - `community.vmware >= 3.10.0`
  - `vmware.vmware >= 1.2.0`
- Parent vSphere environment with:
  - ESXi template or clone source
  - vCenter OVA in content library
  - Sufficient resources (CPU, memory, storage)
  - Network connectivity

## Role Variables

### Required Variables

```yaml
# Parent vCenter connection (typically from group_vars)
vsphere_vm_deploy_parent_vcenter:
  hostname: "vcenter.example.com"
  username: "administrator@vsphere.local"
  password: "secure_password"
  datacenter: "Datacenter"
  datastore: "datastore1"
  cluster: "Cluster1"
  folder: "nested"
  network: "VM Network"
```

### Optional Variables

#### ESXi Deployment

```yaml
# List of ESXi VMs to deploy
vsphere_vm_deploy_esxi_hosts:
  - name: "esxi-1"
    memory_mb: 8192  # Optional, defaults to vsphere_vm_deploy_esxi_memory_mb
    cpu: 4  # Optional, defaults to vsphere_vm_deploy_esxi_cpu
    disk_gb: 100  # Optional, defaults to vsphere_vm_deploy_esxi_disk_gb
    networks:  # Optional
      - name: "VM Network"
        connected: true

# ESXi defaults
vsphere_vm_deploy_esxi_cpu: 4
vsphere_vm_deploy_esxi_memory_mb: 8192
vsphere_vm_deploy_esxi_disk_gb: 100
```

#### vCenter Deployment

```yaml
# List of vCenter VMs to deploy
vsphere_vm_deploy_vcenter_vms:
  - name: "vcenter-1"
    deployment_size: "tiny"  # tiny, small, medium, large, infrastructure
    memory_mb: 12288  # Optional override
    cpu: 2  # Optional override
    network: "VM Network"  # Optional

# vCenter defaults
vsphere_vm_deploy_vcenter_cpu: 2
vsphere_vm_deploy_vcenter_memory_mb: 12288
vsphere_vm_deploy_vcenter_deployment_size: "tiny"
```

#### Credentials

```yaml
# Nested ESXi/vCenter password
vsphere_vm_deploy_nested_password: "{{ nested_esxi_password }}"
vsphere_vm_deploy_nested_vcenter_domain: "vsphere.local"
```

#### Timeouts

```yaml
vsphere_vm_deploy_wait_timeout: 900  # 15 minutes
vsphere_vm_deploy_wait_for_ip_timeout: 600  # 10 minutes
vsphere_vm_deploy_wait_for_service_timeout: 900  # 15 minutes
```

#### Advanced Options

```yaml
# Force VM recreation (anti-pattern, use with caution)
vsphere_vm_deploy_force_recreate: false

# VM hardware version
vsphere_vm_deploy_vm_version: 21  # vSphere 8.0

# Disk configuration
vsphere_vm_deploy_disk_controller_type: "paravirtual"
vsphere_vm_deploy_disk_type: "thin"

# Debug logging
vsphere_vm_deploy_debug: false
```

## Dependencies

This role has no dependencies on other roles.

## Example Playbook

### Deploy ESXi Hosts Only

```yaml
- name: Deploy nested ESXi hosts
  hosts: localhost
  gather_facts: false
  roles:
    - role: vsphere_vm_deploy
      vars:
        vsphere_vm_deploy_esxi_hosts:
          - name: "esxi-1"
            memory_mb: 16384
            cpu: 8
            disk_gb: 200
          - name: "esxi-2"
            memory_mb: 16384
            cpu: 8
            disk_gb: 200
```

### Deploy vCenter Only

```yaml
- name: Deploy nested vCenter
  hosts: localhost
  gather_facts: false
  roles:
    - role: vsphere_vm_deploy
      vars:
        vsphere_vm_deploy_vcenter_vms:
          - name: "vcenter-1"
            deployment_size: "small"
            memory_mb: 16384
            cpu: 4
```

### Deploy Both ESXi and vCenter

```yaml
- name: Deploy complete nested environment
  hosts: localhost
  gather_facts: false
  roles:
    - role: vsphere_vm_deploy
      vars:
        vsphere_vm_deploy_esxi_hosts:
          - name: "esxi-1"
          - name: "esxi-2"
          - name: "esxi-3"
        vsphere_vm_deploy_vcenter_vms:
          - name: "vcenter-1"
            deployment_size: "tiny"
```

## Idempotency

This role is designed to be fully idempotent:

- Checks if VMs exist before creating
- Updates existing VMs if configuration changes
- Skips deployment if VM already exists with correct configuration
- Never deletes and recreates VMs (unless `vsphere_vm_deploy_force_recreate: true`)

**Running the role twice with the same variables will not create duplicate resources.**

## Dynamic Inventory

Deployed VMs are automatically added to dynamic inventory groups:

- `deployed_esxi`: All deployed ESXi hosts
- `deployed_vcenter`: All deployed vCenter appliances

Each host includes:
- `ansible_host`: IP address
- `esxi_ip` or `vcenter_ip`: VM IP address
- Credentials for connecting to the VM

Example usage:

```yaml
- name: Configure deployed ESXi hosts
  hosts: deployed_esxi
  tasks:
    - name: Check ESXi status
      ansible.builtin.debug:
        msg: "ESXi host {{ inventory_hostname }} at {{ esxi_ip }}"
```

## Outputs

### Variables Set

The role sets the following facts for each deployed VM:

- ESXi: `hostvars[esxi_name].esxi_ip`
- vCenter: `hostvars[vcenter_name].vcenter_ip`

### Files Created

If `vsphere_vm_deploy_retrieve_certificates: true` (default):

- `{{ vsphere_vm_deploy_certificate_download_path }}/{{ vcenter_name }}-ca-cert.pem`

## Error Handling

The role includes robust error handling:

- Retries for network operations (3 attempts)
- Configurable timeouts for all wait operations
- Failed VM deployments do not stop subsequent deployments
- Clear error messages for common issues

## Troubleshooting

### VM deployment fails with "template not found"

**Solution**: Ensure the ESXi template name matches the expected format:
```
{{ deployment_version }}-{{ cluster_name }}
```

Example: `VC8.0.2.00100-22617221-ESXi8.0u2c-Cluster1`

### vCenter deployment fails with "library item not found"

**Solution**: Verify the content library contains the vCenter OVA:
1. Check content library name: `{{ vsphere_vm_deploy_content_library }}`
2. Check OVA name in library (without `.ova` extension)

### VM gets IP but times out waiting for service

**Solution**: Increase timeout:
```yaml
vsphere_vm_deploy_wait_for_service_timeout: 1800  # 30 minutes
```

### Deployment is slow

**Causes**:
- Parent vCenter is slow
- Storage is slow (use SSD-backed datastores)
- Network latency

**Solutions**:
- Use faster storage
- Deploy fewer VMs in parallel
- Adjust timeout values

## Testing

### Molecule

Test the role with Molecule:

```bash
cd roles/vsphere_vm_deploy
molecule test -s vcsim  # Using vCenter simulator
molecule test -s default  # Using real vSphere
```

### Manual Testing

```bash
ansible-playbook test_playbook.yml \
  -e vsphere_vm_deploy_esxi_hosts='[{"name": "test-esxi-1"}]' \
  --vault-password-file=.vault_pass
```

## License

Apache-2.0

## Author Information

OpenShift SPLAT Team

## See Also

- [DEVELOPMENT.md](../../docs/DEVELOPMENT.md) - Development guide
- [VARIABLES.md](../../docs/VARIABLES.md) - Complete variable reference
- [community.vmware](https://docs.ansible.com/ansible/latest/collections/community/vmware/) - Collection documentation
