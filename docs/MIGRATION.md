# Migration Guide: v1 to v2

This guide covers migrating from the v1 monolithic playbook structure to the v2 role-based architecture.

## Overview

**v1 → v2 Changes:**

| Aspect | v1 | v2 |
|--------|----|----|
| **Structure** | 12+ flat playbook files | 7 focused roles |
| **Lines of Code** | ~1,144 lines | Modular, reusable roles |
| **Idempotency** | Delete/recreate patterns | Check-before-create |
| **Testing** | None | Molecule + integration tests |
| **Secrets** | Hardcoded or env vars | Ansible Vault |
| **Configuration** | platform.yaml (OpenShift) | vsphere_topology.yml (deployment) |
| **Error Handling** | Basic | Comprehensive with retry |

## Should I Migrate?

**Migrate to v2 if:**
- ✅ You want idempotent deployments (safe re-runs)
- ✅ You need production-ready error handling
- ✅ You want to test infrastructure changes before deploying
- ✅ You need better secrets management
- ✅ You want to reuse roles in other projects

**Stay on v1 if:**
- ✅ Your current setup works and you don't need new features
- ✅ You need minimal changes to existing workflows
- ✅ You don't have time to test the migration

**Note:** v2 can manage infrastructure deployed by v1 (they're compatible).

## Migration Options

### Option 1: Automated Migration (Recommended)

Use the migration script for a guided, automated migration:

```bash
cd /path/to/nested-ova-ansible
./scripts/migrate_from_v1.sh
```

**What it does:**
1. ✅ Backs up v1 files to `v1_backup_YYYYMMDD_HHMMSS/`
2. ✅ Converts `platform.yaml` to `vsphere_topology.yml`
3. ✅ Sets up Ansible Vault template
4. ✅ Installs dependencies (collections, Python libs)
5. ✅ Validates configuration
6. ✅ Creates migration summary

**Dry-run mode** (see what would happen):
```bash
./scripts/migrate_from_v1.sh --dry-run
```

**Skip backup** (if you already have backups):
```bash
./scripts/migrate_from_v1.sh --skip-backup
```

### Option 2: Manual Migration

For more control, migrate manually:

#### Step 1: Backup v1 Files

```bash
# Create backup
mkdir -p v1_backup
cp *.yml v1_backup/
cp -r group_vars v1_backup/
```

#### Step 2: Convert Topology File

```bash
# Convert platform.yaml to vsphere_topology.yml
./scripts/convert_topology.py platform.yaml -o vsphere_topology.yml --pretty

# Review and adjust the converted file
vi vsphere_topology.yml
```

**Manual adjustments needed:**
- ESXi passwords (not in platform.yaml)
- vCenter credentials
- Resource allocations (CPU, memory, disk)
- HostGroup host lists (if using HostGroup zone type)
- Parent vCenter settings

#### Step 3: Set Up Secrets

```bash
# Create vault file from template
cp group_vars/all/vault.yml group_vars/all/vault.yml.new
vi group_vars/all/vault.yml.new

# Add your credentials:
#   vault_esxi_password: "YourESXiPassword"
#   vault_vcenter_password: "YourVCenterPassword"
#   vault_parent_vcenter_password: "YourParentVCenterPassword"

# Encrypt the vault
ansible-vault encrypt group_vars/all/vault.yml.new
mv group_vars/all/vault.yml.new group_vars/all/vault.yml
```

#### Step 4: Configure Parent vCenter

Edit `group_vars/all/connection.yml`:

```yaml
vsphere_parent_vcenter:
  hostname: "{{ lookup('env', 'GOVC_URL') }}"
  username: "{{ lookup('env', 'GOVC_USERNAME') | default('administrator@vsphere.local') }}"
  password: "{{ vault_parent_vcenter_password }}"
  datacenter: "{{ lookup('env', 'GOVC_DATACENTER') }}"
  cluster: "{{ lookup('env', 'GOVC_CLUSTER') }}"
  esxi_host: "{{ lookup('env', 'GOVC_HOST') | default('') }}"
  datastore: "{{ lookup('env', 'GOVC_DATASTORE') }}"
  validate_certs: false
```

This maintains environment variable compatibility while supporting Vault.

#### Step 5: Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Ansible collections
ansible-galaxy collection install -r collections/requirements.yml
```

#### Step 6: Validate

```bash
# Run preflight validation
ansible-playbook playbooks/preflight.yml \
  -e topology_file=vsphere_topology.yml \
  --vault-password-file=.vault_pass
```

## Topology Conversion Examples

### v1 platform.yaml

```yaml
platform:
  vsphere:
    vcenters:
      - server: vcenter-1
        datacenters:
        - dc1
    failureDomains:
      - server: vcenter-1
        name: "zone-a"
        zone: "zone-a"
        region: "region-1"
        topology:
          computeCluster: /dc1/host/cluster1
          datacenter: dc1
          datastore: /dc1/datastore/ds1
```

### v2 vsphere_topology.yml

```yaml
deployment_name: nested-vsphere
region: region-1

esxi_hosts:
  - name: esxi01
    ip: 192.168.1.10
    mask: 255.255.255.0
    gw: 192.168.1.1
    cpu: 8
    memory_mb: 65536
    disk_gb: 200
    username: root
    password: "{{ vault_esxi_password }}"
    datacenter: dc1
    cluster: cluster1
    parent_resource_pool: nested-vsphere
    parent_host: "{{ vsphere_parent_vcenter.esxi_host }}"
    parent_datastore: "{{ vsphere_parent_vcenter.datastore }}"

vcenter_vms:
  - name: vcsa01
    hostname: vcenter-1
    ip: 192.168.1.5
    mask: 255.255.255.0
    gw: 192.168.1.1
    dns: 192.168.1.1
    cpu: 8
    memory_mb: 24576
    username: administrator@vsphere.local
    password: "{{ vault_vcenter_password }}"
    datacenter: dc1
    datacenters:
      - name: dc1
        clusters:
          - name: cluster1
            drs_enabled: true
            ha_enabled: true
    esxi_hosts:
      - hostname: 192.168.1.10
        username: root
        password: "{{ vault_esxi_password }}"
        datacenter: dc1
        cluster: cluster1

failure_domains:
  - name: zone-a
    region: region-1
    zone: zone-a
    zone_type: ComputeCluster
    datacenter: dc1
    cluster: cluster1
    vcenter:
      hostname: vcenter-1
      username: administrator@vsphere.local
      password: "{{ vault_vcenter_password }}"
      validate_certs: false
```

## Testing the Migration

### Step 1: Test Against Existing Infrastructure

v2 is designed to be idempotent over v1 deployments:

```bash
# Deploy v2 over existing v1 infrastructure
ansible-playbook playbooks/deploy_nested_vsphere.yml \
  -e topology_file=vsphere_topology.yml \
  --vault-password-file=.vault_pass \
  --check  # Dry-run mode

# Review what would change (should be minimal or none)
```

### Step 2: Run Preflight Validation

```bash
ansible-playbook playbooks/preflight.yml \
  -e topology_file=vsphere_topology.yml \
  --vault-password-file=.vault_pass
```

**Expected output:**
- ✅ Ansible version check passed
- ✅ Python version check passed
- ✅ Collections installed
- ✅ Parent vCenter connection successful
- ✅ Topology structure validated
- ✅ Resource requirements calculated

### Step 3: Deploy (Idempotent Test)

```bash
# First run (should make minimal changes if v1 is deployed)
ansible-playbook playbooks/deploy_nested_vsphere.yml \
  -e topology_file=vsphere_topology.yml \
  --vault-password-file=.vault_pass

# Second run (should make NO changes - idempotency test)
ansible-playbook playbooks/deploy_nested_vsphere.yml \
  -e topology_file=vsphere_topology.yml \
  --vault-password-file=.vault_pass
```

## Breaking Changes

### Configuration Format

**v1:** `platform.yaml` (OpenShift-specific)
**v2:** `vsphere_topology.yml` (deployment-focused)

**Migration:** Use `./scripts/convert_topology.py` to convert

### Environment Variables

**v1 variables still supported** via environment lookup:

```yaml
vsphere_parent_vcenter:
  hostname: "{{ lookup('env', 'GOVC_URL') }}"
  username: "{{ lookup('env', 'GOVC_USERNAME') }}"
  # ...
```

**New v2 approach** (preferred):

```yaml
vsphere_parent_vcenter:
  hostname: vcenter.example.com
  password: "{{ vault_parent_vcenter_password }}"
```

### Playbook Entry Points

| v1 | v2 |
|----|---- |
| `ansible-playbook main.yml` | `ansible-playbook playbooks/deploy_nested_vsphere.yml` |
| `ansible-playbook vsphere_remove.yml` | `ansible-playbook playbooks/destroy_nested_vsphere.yml` |
| N/A | `ansible-playbook playbooks/preflight.yml` |

### Role Variables

v1 used global variables (e.g., `testingesxi`, `testingvc`).
v2 uses role-specific prefixed variables (e.g., `vsphere_vm_deploy_force_recreate`).

**Migration:** Remove `testingesxi` and `testingvc` flags. v2 is idempotent by default.

## Rollback Plan

If migration doesn't work:

### Option 1: Restore v1 Files

```bash
# Restore from backup
cp v1_backup/*.yml .
cp -r v1_backup/group_vars .

# Continue using v1
ansible-playbook main.yml
```

### Option 2: Use v1 Branch

```bash
# Switch to v1 branch (main)
git checkout main

# Continue using v1
ansible-playbook main.yml
```

## Post-Migration

### Update CI/CD Pipelines

If you have CI/CD pipelines using v1:

**v1 command:**
```bash
ansible-playbook main.yml --extra-var version="VC8.0.2.00100"
```

**v2 command:**
```bash
ansible-playbook playbooks/deploy_nested_vsphere.yml \
  -e topology_file=vsphere_topology.yml \
  --vault-password-file=.vault_pass
```

### Update Documentation

- Update runbooks to reference v2 playbooks
- Update team documentation with new topology file format
- Share migration guide with team

### Clean Up Old Files

After confirming v2 works:

```bash
# Remove v1 playbook files (or keep for reference)
rm -f esxinested.yml vcnested.yml addhosts_vcenter.yml \
      dvs_hosts_vcenter.yml create_datastore.yml \
      tagging.yml host_groups.yml main.yml

# Or move to archive
mkdir -p archive/v1
mv *.yml archive/v1/
```

## Troubleshooting Migration

### Issue: Convert script fails with "platform.yaml not found"

**Solution:** Ensure `platform.yaml` exists or specify path:
```bash
./scripts/convert_topology.py /path/to/platform.yaml -o vsphere_topology.yml
```

### Issue: Preflight fails with "vault file not encrypted"

**Solution:** Encrypt the vault file:
```bash
ansible-vault encrypt group_vars/all/vault.yml
```

### Issue: Deployment makes unexpected changes

**Solution:** Run in check mode first:
```bash
ansible-playbook playbooks/deploy_nested_vsphere.yml --check
```

### Issue: Missing Python dependencies

**Solution:** Install requirements:
```bash
pip install -r requirements.txt
```

### Issue: Collection not found

**Solution:** Install collections:
```bash
ansible-galaxy collection install -r collections/requirements.yml --force
```

## FAQ

### Q: Can I run v2 alongside v1?

**A:** Yes, they can coexist. v2 uses different playbook names and directory structure.

### Q: Will v2 delete my v1 deployment?

**A:** No, v2 is idempotent. It will check what exists and only create missing resources.

### Q: Do I need to redeploy everything?

**A:** No, v2 can manage infrastructure deployed with v1 without redeployment.

### Q: Can I go back to v1 after migrating?

**A:** Yes, restore v1 files from backup or use the `main` branch.

### Q: What happens to my existing VMs?

**A:** They remain untouched. v2 will detect them and skip creation.

### Q: How do I test migration safely?

**A:** Use `--check` mode for dry-run:
```bash
ansible-playbook playbooks/deploy_nested_vsphere.yml --check
```

## Getting Help

- **Issues:** https://github.com/openshift-eng/nested-ova-ansible/issues
- **Discussions:** https://github.com/openshift-eng/nested-ova-ansible/discussions
- **Documentation:** [README.md](../README.md) | [DEVELOPMENT.md](DEVELOPMENT.md) | [VARIABLES.md](VARIABLES.md)

## Next Steps

After successful migration:

1. ✅ Review [ROLES.md](ROLES.md) to understand the new architecture
2. ✅ Read [TESTING.md](TESTING.md) to learn testing workflows
3. ✅ Explore [VARIABLES.md](VARIABLES.md) for configuration options
4. ✅ Check [DEVELOPMENT.md](DEVELOPMENT.md) for development workflows
