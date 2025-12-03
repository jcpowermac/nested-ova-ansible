# Testing Guide

Comprehensive testing strategy for the nested vSphere Ansible project.

## Table of Contents

- [Testing Philosophy](#testing-philosophy)
- [Test Types](#test-types)
- [Molecule Testing](#molecule-testing)
- [Integration Testing](#integration-testing)
- [CI/CD Testing](#cicd-testing)
- [Manual Testing](#manual-testing)
- [Troubleshooting Tests](#troubleshooting-tests)

## Testing Philosophy

The project follows a multi-layered testing approach:

```
┌─────────────────────────────────────────────────────────┐
│ Layer 4: Manual Testing                                 │
│ - Full deployment to real vSphere                       │
│ - OpenShift installation validation                     │
└─────────────────────────────────────────────────────────┘
                         ▲
┌─────────────────────────────────────────────────────────┐
│ Layer 3: Integration Tests                              │
│ - Full deployment scenarios                             │
│ - Idempotency verification                              │
│ - Multi-FD, Multi-vCenter, HostGroup                    │
└─────────────────────────────────────────────────────────┘
                         ▲
┌─────────────────────────────────────────────────────────┐
│ Layer 2: Molecule Tests (per role)                      │
│ - Role functionality with vcsim                          │
│ - Idempotency checks                                     │
│ - Variable validation                                    │
└─────────────────────────────────────────────────────────┘
                         ▲
┌─────────────────────────────────────────────────────────┐
│ Layer 1: Linting                                         │
│ - ansible-lint (syntax, best practices)                 │
│ - yamllint (YAML formatting)                             │
│ - Python linting (filter plugins)                        │
└─────────────────────────────────────────────────────────┘
```

**Goals:**
- ✅ Catch errors early (lint → molecule → integration → manual)
- ✅ Fast feedback loop (molecule tests < 5 minutes)
- ✅ Comprehensive coverage (all roles, all scenarios)
- ✅ Automated in CI/CD (GitHub Actions)

## Test Types

### 1. Linting

**Purpose:** Catch syntax errors and style violations

**Tools:**
- `ansible-lint`: Ansible best practices
- `yamllint`: YAML formatting
- `pylint`: Python code (filter plugins)

**Run locally:**
```bash
# Lint all Ansible files
ansible-lint

# Lint YAML files
yamllint .

# Lint Python filter plugins
pylint filter_plugins/*.py
```

**Configuration:**
- `.ansible-lint` - ansible-lint rules
- `.yamllint` - yamllint rules

### 2. Molecule Tests

**Purpose:** Unit test each role independently

**What it tests:**
- Role functionality
- Idempotency (run twice, no changes on second run)
- Variable validation
- Error handling

**Driver:** `delegated` (allows vcsim or real vSphere)

**Scenarios:**
- `default`: Real vSphere testing (requires credentials)
- `vcsim`: vCenter simulator for CI (no credentials needed)

### 3. Integration Tests

**Purpose:** Test full deployment scenarios

**What it tests:**
- End-to-end deployment
- Multiple failure domains
- Multiple vCenters
- HostGroup affinity
- Migration from v1

**Test files:**
- `tests/integration/full_deployment/test_single_fd.yml`
- `tests/integration/full_deployment/test_multi_fd.yml`
- `tests/integration/full_deployment/test_multi_vcenter.yml`
- `tests/integration/full_deployment/test_hostgroup_affinity.yml`
- `tests/integration/upgrade/test_upgrade_from_v1.yml`
- `tests/integration/idempotency/test_idempotency.yml`

### 4. Manual Testing

**Purpose:** Validate in production-like environment

**What it tests:**
- Real vSphere deployment
- OpenShift installation
- Zone affinity behavior
- Failure scenarios

---

## Molecule Testing

### Prerequisites

```bash
# Install Molecule and dependencies
pip install molecule molecule-plugins[docker] ansible-lint

# Install Ansible collections
ansible-galaxy collection install -r collections/requirements.yml
```

### Molecule Directory Structure

Each role has a `molecule/` directory:

```
roles/vsphere_vm_deploy/
├── molecule/
│   ├── default/           # Real vSphere scenario
│   │   ├── molecule.yml
│   │   ├── converge.yml
│   │   ├── verify.yml
│   │   └── prepare.yml (optional)
│   └── vcsim/             # vCenter simulator scenario
│       ├── molecule.yml
│       ├── converge.yml
│       └── verify.yml
```

### Running Molecule Tests

**Test a single role:**
```bash
cd roles/vsphere_vm_deploy
molecule test
```

**Test with vcsim (CI mode):**
```bash
cd roles/vsphere_vm_deploy
molecule test -s vcsim
```

**Test all roles:**
```bash
for role in roles/*/; do
  cd "$role"
  molecule test -s vcsim
  cd -
done
```

**Molecule workflow:**
```bash
# Step-by-step workflow (useful for debugging)
molecule create      # Create test environment
molecule converge    # Run the role
molecule idempotence # Run again, verify no changes
molecule verify      # Run verification tasks
molecule destroy     # Clean up
```

### Molecule Configuration

**molecule.yml** (vcsim scenario):
```yaml
---
driver:
  name: delegated  # Use existing infrastructure (vcsim)

platforms:
  - name: vcsim
    groups:
      - vsphere

provisioner:
  name: ansible
  env:
    ANSIBLE_VERBOSITY: 1
  inventory:
    group_vars:
      vsphere:
        ansible_connection: local
        vsphere_vcenter_hostname: localhost
        vsphere_vcenter_port: 8989
        vsphere_vcenter_username: user
        vsphere_vcenter_password: pass
        vsphere_vcenter_validate_certs: false

verifier:
  name: ansible
```

**converge.yml** - Run the role:
```yaml
---
- name: Converge
  hosts: all
  gather_facts: false
  tasks:
    - name: Include role
      ansible.builtin.include_role:
        name: vsphere_vm_deploy
      vars:
        vsphere_vm_deploy_parent_vcenter:
          hostname: "{{ vsphere_vcenter_hostname }}"
          username: "{{ vsphere_vcenter_username }}"
          password: "{{ vsphere_vcenter_password }}"
```

**verify.yml** - Verify results:
```yaml
---
- name: Verify
  hosts: all
  gather_facts: false
  tasks:
    - name: Check ESXi VM exists
      community.vmware.vmware_guest_info:
        hostname: "{{ vsphere_vcenter_hostname }}"
        username: "{{ vsphere_vcenter_username }}"
        password: "{{ vsphere_vcenter_password }}"
        name: esxi01
      register: vm_info
      failed_when: vm_info.instance is not defined
```

### Using vcsim

**Start vcsim with Docker:**
```bash
docker run -d --name vcsim \
  -p 8989:8989 \
  -e VCSIM_STANDALONE_PORT=8989 \
  nimmis/vcsim:latest

# Wait for vcsim to be ready
sleep 10
```

**Connect to vcsim:**
```bash
# vcsim defaults
HOSTNAME: localhost:8989
USERNAME: user
PASSWORD: pass
```

**Stop vcsim:**
```bash
docker stop vcsim
docker rm vcsim
```

### Idempotency Testing

Molecule automatically tests idempotency with the `idempotence` step:

```bash
molecule idempotence
```

This runs the role twice and verifies the second run makes no changes.

**Manual idempotency test:**
```bash
# First run
molecule converge

# Second run (should make no changes)
molecule converge

# Check for changes
# If "changed=0" on second run, role is idempotent
```

---

## Integration Testing

Integration tests validate full deployment scenarios.

### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt
ansible-galaxy collection install -r collections/requirements.yml

# Set up vcsim OR configure real vSphere
docker run -d --name vcsim -p 8989:8989 nimmis/vcsim:latest
```

### Running Integration Tests

**Single failure domain test:**
```bash
ansible-playbook tests/integration/full_deployment/test_single_fd.yml \
  -e vsphere_parent_vcenter='{"hostname":"localhost","port":"8989","username":"user","password":"pass"}' \
  -v
```

**Idempotency test:**
```bash
ansible-playbook tests/integration/idempotency/test_idempotency.yml \
  -e topology_file=examples/vsphere_topology_single_fd.yml \
  -v
```

**All integration tests:**
```bash
for test in tests/integration/**/*.yml; do
  ansible-playbook "$test" -v
done
```

### Integration Test Structure

```yaml
---
# tests/integration/full_deployment/test_single_fd.yml
- name: Test Single Failure Domain Deployment
  hosts: localhost
  gather_facts: false

  tasks:
    - name: Set test topology
      ansible.builtin.set_fact:
        test_topology_file: "{{ playbook_dir }}/../../../examples/vsphere_topology_single_fd.yml"

    - name: Run preflight
      ansible.builtin.import_playbook:
        playbook: playbooks/preflight.yml
      vars:
        topology_file: "{{ test_topology_file }}"

    - name: Deploy environment
      ansible.builtin.import_playbook:
        playbook: playbooks/deploy_nested_vsphere.yml
      vars:
        topology_file: "{{ test_topology_file }}"

    - name: Verify deployment
      block:
        - name: Check vCenter is accessible
          community.vmware.vmware_about_info:
            hostname: vcsa01.lab.local
          register: vcenter_info

        - name: Assert vCenter is running
          ansible.builtin.assert:
            that:
              - vcenter_info is succeeded
              - vcenter_info.about_info.fullName is defined

    - name: Test idempotency
      block:
        - name: Run deployment again
          ansible.builtin.import_playbook:
            playbook: playbooks/deploy_nested_vsphere.yml
          vars:
            topology_file: "{{ test_topology_file }}"
          register: second_run

        - name: Assert no changes on second run
          ansible.builtin.assert:
            that:
              - second_run.changed == false
            fail_msg: "Deployment is not idempotent - made changes on second run"

    - name: Cleanup
      ansible.builtin.import_playbook:
        playbook: playbooks/destroy_nested_vsphere.yml
      vars:
        deployment_name: single-fd-lab
        destroy_mode: hard
```

---

## CI/CD Testing

GitHub Actions automatically runs tests on every push and pull request.

### Workflow: `.github/workflows/test.yml`

**Jobs:**

1. **lint**: Run ansible-lint and yamllint
2. **molecule**: Test all 7 roles with vcsim
3. **playbook-syntax**: Syntax check all playbooks
4. **integration**: Full deployment test (main branch only)
5. **security**: Trivy vulnerability scan
6. **docs**: Validate documentation
7. **test-summary**: Aggregate results

### Triggering CI

**On push:**
```bash
git add .
git commit -m "Add new feature"
git push
# CI runs automatically
```

**On pull request:**
```bash
# Create PR on GitHub
# CI runs automatically
```

**Manual trigger:**
```bash
# Via GitHub Actions UI
# Actions → Test → Run workflow
```

### Viewing CI Results

**GitHub UI:**
1. Go to repository on GitHub
2. Click "Actions" tab
3. Select workflow run
4. View job logs

**Badges:**
```markdown
![CI](https://github.com/openshift-eng/nested-ova-ansible/workflows/test/badge.svg)
```

---

## Manual Testing

Manual testing validates the full deployment in a real environment.

### Test Plan

#### 1. Fresh Deployment

**Objective:** Deploy from scratch

**Steps:**
```bash
# 1. Prepare
cp examples/vsphere_topology_single_fd.yml vsphere_topology.yml
# Edit vsphere_topology.yml with your environment details

# 2. Run preflight
ansible-playbook playbooks/preflight.yml \
  -e topology_file=vsphere_topology.yml \
  --vault-password-file=.vault_pass

# 3. Deploy
ansible-playbook playbooks/deploy_nested_vsphere.yml \
  -e topology_file=vsphere_topology.yml \
  --vault-password-file=.vault_pass

# 4. Verify
# - Log into vCenter UI
# - Check all hosts are in cluster
# - Check tags are created
# - Check dvSwitch is configured
```

**Expected Results:**
- ✅ All ESXi VMs deployed and powered on
- ✅ vCenter deployed and accessible
- ✅ Hosts added to cluster
- ✅ DRS and HA enabled
- ✅ dvSwitch created with port groups
- ✅ Tags created and attached
- ✅ (If HostGroup) DRS host groups created

#### 2. Idempotency Test

**Objective:** Verify re-running makes no changes

**Steps:**
```bash
# 1. First deployment (above)

# 2. Second deployment (should make no changes)
ansible-playbook playbooks/deploy_nested_vsphere.yml \
  -e topology_file=vsphere_topology.yml \
  --vault-password-file=.vault_pass \
  -vv | tee second-run.log

# 3. Check for changes
grep "changed=" second-run.log
# Should show "changed=0" for all tasks
```

**Expected Results:**
- ✅ No tasks report "changed"
- ✅ All "Check if X exists" tasks find resources
- ✅ No new VMs created
- ✅ No configuration changes

#### 3. Partial Failure Recovery

**Objective:** Verify role can recover from failures

**Steps:**
```bash
# 1. Deploy with intentional failure
# (e.g., invalid vCenter password)

# 2. Fix the issue

# 3. Re-run deployment
ansible-playbook playbooks/deploy_nested_vsphere.yml \
  -e topology_file=vsphere_topology.yml \
  --vault-password-file=.vault_pass

# 4. Verify recovery
# Check that deployment completes successfully
```

**Expected Results:**
- ✅ Deployment continues from failure point
- ✅ No duplicate resources created
- ✅ Final state matches expected topology

#### 4. Destroy and Redeploy

**Objective:** Verify cleanup and redeployment

**Steps:**
```bash
# 1. Deploy (as above)

# 2. Destroy
ansible-playbook playbooks/destroy_nested_vsphere.yml \
  -e deployment_name=single-fd-lab \
  -e destroy_mode=hard \
  --vault-password-file=.vault_pass

# 3. Verify cleanup
# - VMs deleted
# - Datacenters removed
# - Tags removed

# 4. Redeploy
ansible-playbook playbooks/deploy_nested_vsphere.yml \
  -e topology_file=vsphere_topology.yml \
  --vault-password-file=.vault_pass
```

**Expected Results:**
- ✅ All resources removed
- ✅ State file deleted
- ✅ Redeployment succeeds
- ✅ Final state matches topology

#### 5. OpenShift Installation

**Objective:** Validate nested environment for OpenShift

**Steps:**
```bash
# 1. Deploy nested environment (as above)

# 2. Create OpenShift install-config.yaml using the deployed topology

# 3. Run OpenShift installer
openshift-install create cluster --dir=./install-dir

# 4. Verify
# - Cluster installs successfully
# - Nodes are in correct zones
# - Zone affinity working (if HostGroup)
```

**Expected Results:**
- ✅ OpenShift installer succeeds
- ✅ Control plane and worker nodes created
- ✅ Nodes tagged with correct zones
- ✅ Workloads respect zone affinity

---

## Troubleshooting Tests

### Molecule Test Failures

**Issue: "Connection to vcsim failed"**

**Solution:**
```bash
# Check vcsim is running
docker ps | grep vcsim

# Restart vcsim
docker restart vcsim

# Check logs
docker logs vcsim
```

**Issue: "Role not found"**

**Solution:**
```bash
# Ensure you're in the role directory
cd roles/vsphere_vm_deploy

# Check molecule.yml points to correct role
cat molecule/default/molecule.yml
```

**Issue: "Idempotence test failed"**

**Solution:**
```bash
# Run with verbose output
molecule --debug idempotence

# Check for resources not being detected
# Add debug tasks to verify resource existence
```

### Integration Test Failures

**Issue: "vCenter connection timeout"**

**Solution:**
```bash
# Increase timeout
# In topology file:
vm_wait_timeout: 1200  # 20 minutes

# Or environment variable
export VSPHERE_WAIT_TIMEOUT=1200
```

**Issue: "Host addition failed"**

**Solution:**
```bash
# Check ESXi hosts are accessible
ping 192.168.1.10

# Check credentials
# Verify vault_esxi_password is correct

# Increase retries
# In topology or role vars:
vsphere_host_config_retry_count: 10
vsphere_host_config_retry_delay: 60
```

### CI/CD Failures

**Issue: "ansible-lint errors"**

**Solution:**
```bash
# Run locally
ansible-lint

# Fix issues or add skip_ansible_lint
# In task:
  tags:
    - skip_ansible_lint
```

**Issue: "Molecule test timeout in CI"**

**Solution:**
```bash
# Check GitHub Actions logs
# Increase timeout in .github/workflows/test.yml:
timeout-minutes: 30
```

---

## Test Coverage Goals

### Current Coverage

- ✅ **Linting**: 100% (all files linted)
- ✅ **Molecule**: 100% (all 7 roles have tests)
- ⏳ **Integration**: 80% (4/5 scenarios)
- ⏳ **Manual**: Ad-hoc (no automation)

### Future Improvements

- [ ] Integration test automation in CI
- [ ] Performance benchmarking tests
- [ ] Chaos engineering tests (random failures)
- [ ] Multi-version compatibility tests (ESXi 7.0, 8.0, etc.)
- [ ] Upgrade path tests (v1 → v2 automated)

---

## See Also

- [DEVELOPMENT.md](DEVELOPMENT.md) - Development workflow
- [ROLES.md](ROLES.md) - Role documentation
- [VARIABLES.md](VARIABLES.md) - Variable reference
- [CI Workflow](.github/workflows/test.yml) - GitHub Actions configuration
