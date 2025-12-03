# Nested vSphere Ansible

**https://github.com/openshift-eng/nested-ova-ansible is now the canonical repo**

Production-ready Ansible automation for deploying nested vSphere environments to support OpenShift testing and development.

## Version 2.0 - Complete Rewrite

This is version 2.0 - a complete architectural rewrite following Ansible best practices:

- ✅ **Idempotent**: Re-run safely without delete/recreate
- ✅ **Modular**: 7 focused roles for maximum reusability
- ✅ **Tested**: Molecule unit tests + integration tests
- ✅ **Production-Ready**: Comprehensive error handling, retry logic, structured logging
- ✅ **Secrets Management**: Ansible Vault integration
- ✅ **CI/CD**: GitHub Actions workflows for automated testing

**Migrating from v1?** See [MIGRATION.md](docs/MIGRATION.md) for the automated migration guide.

## What Does This Do?

Provisions complete nested vSphere environments including:

- **ESXi Hosts**: Nested ESXi hypervisors deployed as VMs
- **vCenter Server**: vCenter appliance(s) deployed from OVA or content library
- **Infrastructure**: Datacenters, clusters, DRS, HA configuration
- **Networking**: Distributed vSwitch and port groups
- **Storage**: VMFS and NFS datastores
- **Topology Tags**: OpenShift region/zone tags for failure domain support
- **Host Groups**: DRS host groups for zone affinity (optional)

## Quick Start

### Prerequisites

- **Ansible**: ≥ 11.0.0 (includes ansible-core ≥ 2.18.0)
- **Python**: ≥ 3.9 with `pyvmomi` library
- **Parent vCenter**: Existing vSphere environment to host the nested infrastructure
- **Network**: DHCP server on the hosting environment port group
- **Host Configuration**: Parent ESXi hosts configured for nested virtualization:
  - Promiscuous mode: Accept
  - MAC address changes: Accept
  - Forged transmits: Accept
  - (For vSAN) `esxcli system settings advanced set -o /VSAN/FakeSCSIReservations -i 1`

### Installation

```bash
# Clone the repository
git clone https://github.com/openshift-eng/nested-ova-ansible.git
cd nested-ova-ansible

# Install Python dependencies
pip install -r requirements.txt

# Install Ansible collections
ansible-galaxy collection install -r collections/requirements.yml

# Set up Ansible Vault for secrets
cp group_vars/all/vault.yml group_vars/all/vault.yml.bak
# Edit group_vars/all/vault.yml and replace CHANGE_ME values
ansible-vault encrypt group_vars/all/vault.yml
```

### Configuration

1. **Configure Parent vCenter Connection**

   Edit `group_vars/all/connection.yml`:

   ```yaml
   vsphere_parent_vcenter:
     hostname: vcenter.example.com
     username: administrator@vsphere.local
     password: "{{ vault_parent_vcenter_password }}"
     datacenter: dc1
     cluster: cluster1
     esxi_host: esxi01.example.com
     datastore: datastore1
     validate_certs: false
   ```

   Or use environment variables:

   ```bash
   export GOVC_URL=vcenter.example.com
   export GOVC_USERNAME=administrator@vsphere.local
   export GOVC_PASSWORD=SuperSecret123
   export GOVC_DATACENTER=dc1
   export GOVC_CLUSTER=cluster1
   export GOVC_DATASTORE=datastore1
   ```

2. **Create Topology File**

   Choose an example from `examples/` or create your own:

   ```bash
   cp examples/vsphere_topology_single_fd.yml vsphere_topology.yml
   # Edit vsphere_topology.yml to match your environment
   ```

   See [Example Topologies](#example-topologies) below for different scenarios.

3. **Configure Secrets**

   Add credentials to `group_vars/all/vault.yml` (encrypted):

   ```yaml
   vault_esxi_password: "VMware1!"
   vault_vcenter_password: "VMware1!"
   vault_parent_vcenter_password: "SuperSecret123"
   ```

### Deployment

```bash
# Run preflight validation
ansible-playbook playbooks/preflight.yml \
  -e topology_file=vsphere_topology.yml \
  --vault-password-file=.vault_pass

# Deploy the environment
ansible-playbook playbooks/deploy_nested_vsphere.yml \
  -e topology_file=vsphere_topology.yml \
  --vault-password-file=.vault_pass

# Destroy the environment (when done)
ansible-playbook playbooks/destroy_nested_vsphere.yml \
  -e deployment_name=nested-vsphere \
  --vault-password-file=.vault_pass
```

## Example Topologies

The `examples/` directory contains ready-to-use topology files for common scenarios:

| File | Description | ESXi Hosts | vCenters | Use Case |
|------|-------------|------------|----------|----------|
| [vsphere_topology_single_fd.yml](examples/vsphere_topology_single_fd.yml) | Single failure domain | 3 | 1 | Development, basic testing |
| [vsphere_topology_multi_fd.yml](examples/vsphere_topology_multi_fd.yml) | Multiple failure domains | 6 | 1 | Multi-AZ OpenShift |
| [vsphere_topology_hostgroup.yml](examples/vsphere_topology_hostgroup.yml) | HostGroup zone affinity | 9 | 1 | Strict zone isolation |
| [vsphere_topology_multi_vcenter.yml](examples/vsphere_topology_multi_vcenter.yml) | Multiple vCenters | 6 | 2 | Multi-region, vCenter HA |

## Architecture

### Role-Based Design

```
playbooks/deploy_nested_vsphere.yml
├── vsphere_vm_deploy              # Deploy ESXi and vCenter VMs
├── vsphere_datacenter_config      # Configure datacenters, clusters, DRS, HA
├── vsphere_host_config            # Add hosts to vCenter
├── vsphere_networking             # Configure distributed vSwitch
├── vsphere_storage                # Configure VMFS/NFS datastores
├── vsphere_tagging                # Apply OpenShift region/zone tags
└── vsphere_host_groups            # Create DRS host groups (HostGroup zone_type)
```

Each role is:
- **Independent**: Can be run standalone or as part of full deployment
- **Idempotent**: Safe to re-run without side effects
- **Tested**: Includes Molecule tests and integration tests
- **Documented**: Comprehensive README and variable documentation

### Key Features

#### Idempotency
All roles use check-before-create patterns:
```yaml
- name: Check if resource exists
  community.vmware.vmware_*_info: ...
  register: resource_info

- name: Create resource
  community.vmware.vmware_*: ...
  when: resource_info.* is not defined
```

#### Error Handling
- Configurable retry logic for flaky operations
- Graceful degradation for non-critical failures
- Structured error messages with context

#### Secrets Management
- Ansible Vault for encrypted credentials
- Environment variable fallback for CI/CD
- No hardcoded passwords or IPs

#### Backward Compatibility
- Filter plugin converts old `platform.yaml` format
- Can manage infrastructure deployed with v1
- Migration tool automates v1 → v2 upgrade

## Topology File Format

The new `vsphere_topology.yml` format is deployment-focused (vs the OpenShift-specific `platform.yaml`):

```yaml
deployment_name: my-lab
region: us-east-1

esxi_hosts:
  - name: esxi01
    ip: 192.168.1.10
    cpu: 8
    memory_mb: 65536
    disk_gb: 200
    datacenter: dc1
    cluster: cluster1
    # ... more settings

vcenter_vms:
  - name: vcsa01
    hostname: vcsa01.lab.local
    ip: 192.168.1.5
    cpu: 8
    memory_mb: 24576
    datacenters:
      - name: dc1
        clusters:
          - name: cluster1
            drs_enabled: true
    # ... more settings

failure_domains:
  - name: zone-a
    region: us-east-1
    zone: zone-a
    zone_type: ComputeCluster  # or HostGroup
    datacenter: dc1
    cluster: cluster1
```

See [VARIABLES.md](docs/VARIABLES.md) for the complete variable reference.

## Zone Types

Two zone types are supported for failure domains:

### ComputeCluster (Default)
- Tags the entire compute cluster with the zone tag
- OpenShift distributes workloads across the cluster
- Best for: Development, basic multi-AZ testing

### HostGroup (Strict Affinity)
- Creates DRS host groups with specific ESXi hosts
- Tags the host group (not cluster) with the zone tag
- OpenShift pins VMs to specific zones
- Best for: Strict failure domain isolation, zone-specific failure testing

Example HostGroup configuration:
```yaml
failure_domains:
  - name: zone-a
    zone_type: HostGroup
    hosts:
      - 192.168.1.10
      - 192.168.1.11
      - 192.168.1.12
```

## Media Assets

### Content Library (Recommended)
Deploy vCenter from content library items:
```yaml
content_library:
  name: nested-vsphere-templates
  datastore: datastore1
  esxi_template_item: Nested_ESXi8.0u2c_Appliance_Template_v1
  vcenter_template_item: VMware-vCenter-Server-Appliance-8.0.2.00100
```

### OVA Files (Legacy)
Define OVA locations in `group_vars/all/vsphere_defaults.yml`:
```yaml
vsphere_assets:
  - name: "VC8.0.2.00100-22617221-ESXi8.0u2c"
    esxi_ova: "Nested_ESXi8.0u2c_Appliance_Template_v1.ova"
    esxi_ova_path: "http://10.0.1.100:8000/Nested_ESXi8.0u2c_Appliance_Template_v1.ova"
    vcenter_ova: "VMware-vCenter-Server-Appliance-8.0.2.00100-22617221_OVF10.ova"
    vcenter_ova_path: "http://10.0.1.100:8000/VMware-vCenter-Server-Appliance-8.0.2.00100-22617221_OVF10.ova"
    default: true
```

## Documentation

- **[DEVELOPMENT.md](docs/DEVELOPMENT.md)**: Local development setup, testing workflow
- **[VARIABLES.md](docs/VARIABLES.md)**: Complete variable reference and precedence rules
- **[MIGRATION.md](docs/MIGRATION.md)**: v1 to v2 migration guide
- **[ROLES.md](docs/ROLES.md)**: Detailed role documentation
- **[TESTING.md](docs/TESTING.md)**: Testing strategy and guide

## Development

```bash
# Install development dependencies
pip install -r requirements.txt
pip install molecule molecule-plugins[docker] ansible-lint

# Lint the project
ansible-lint
yamllint .

# Test a specific role with Molecule
cd roles/vsphere_vm_deploy
molecule test

# Run integration tests (requires vcsim or real vSphere)
ansible-playbook tests/integration/full_deployment/test_single_fd.yml
```

See [DEVELOPMENT.md](docs/DEVELOPMENT.md) for the complete development guide.

## CI/CD

GitHub Actions workflows automatically test all changes:

- **Linting**: `ansible-lint`, `yamllint`
- **Molecule Tests**: All 7 roles tested with vcsim
- **Syntax Checks**: Playbook syntax validation
- **Security**: Trivy vulnerability scanning
- **Documentation**: Markdown link checking

See [.github/workflows/test.yml](.github/workflows/test.yml) for the complete CI configuration.

## Troubleshooting

### Enable Debug Mode
```yaml
# In your topology file or as -e flag
vsphere_debug_mode: true
```

### Check Deployment State
```bash
# View saved deployment state
cat state/my-deployment_deployment.yml
```

### Common Issues

**Issue**: VMs not getting IP addresses
- **Solution**: Verify DHCP is enabled on the parent port group

**Issue**: vCenter deployment times out
- **Solution**: Increase `vm_wait_timeout` in topology file (default: 900s)

**Issue**: Host addition fails
- **Solution**: Check ESXi hosts are accessible and credentials are correct

See [DEVELOPMENT.md](docs/DEVELOPMENT.md#troubleshooting) for more troubleshooting tips.

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `ansible-lint` and `molecule test`
5. Submit a pull request

All PRs must pass CI checks before merging.

## License

Apache 2.0

## Acknowledgments

- OpenShift SPLAT Team
- Community VMware Ansible Collection maintainers
- William Lam's nested ESXi appliance
- All contributors to this project

## Support

- **Issues**: https://github.com/openshift-eng/nested-ova-ansible/issues
- **Discussions**: https://github.com/openshift-eng/nested-ova-ansible/discussions
- **Documentation**: [docs/](docs/)

---

**Previous Version (v1)**: The v1 monolithic playbooks are available in the `main` branch (deprecated). New deployments should use v2 (this branch).
