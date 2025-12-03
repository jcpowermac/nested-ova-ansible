# Development Guide

## Prerequisites

- **Python**: 3.9 or higher
- **Ansible**: 2.15 or higher
- **Docker**: For vcsim testing (optional but recommended)
- **Git**: For version control

## Initial Setup

### 1. Clone and Setup Repository

```bash
git clone https://github.com/openshift-splat-team/nested-ova-ansible.git
cd nested-ova-ansible
git checkout rewrite  # Or your development branch
```

### 2. Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Linux/Mac
# Or on Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Ansible collections
ansible-galaxy collection install -r collections/requirements.yml
```

### 4. Setup Vault Password

For local development, create a `.vault_pass` file:

```bash
echo "your-vault-password" > .vault_pass
chmod 600 .vault_pass
```

**Important**: Add `.vault_pass` to `.gitignore` (already done)

### 5. Configure Vault

Edit the vault file with your secrets:

```bash
# If vault is not yet encrypted
ansible-vault encrypt group_vars/all/vault.yml --vault-password-file=.vault_pass

# To edit encrypted vault
ansible-vault edit group_vars/all/vault.yml --vault-password-file=.vault_pass
```

## Development Workflow

### Testing a Single Role

#### Using vcsim (vCenter Simulator)

vcsim is a vCenter simulator that allows testing without a real vSphere environment.

1. **Start vcsim**:

```bash
docker compose -f tests/vcsim/docker-compose.yml up -d
```

2. **Test a role**:

```bash
cd roles/vsphere_vm_deploy
molecule test -s vcsim
```

3. **Cleanup**:

```bash
docker compose -f tests/vcsim/docker-compose.yml down
```

#### Using Real vSphere

If you have access to a real vSphere environment:

```bash
# Set environment variables
export MOLECULE_VSPHERE_HOSTNAME="vcenter.example.com"
export MOLECULE_VSPHERE_USERNAME="administrator@vsphere.local"
export MOLECULE_VSPHERE_PASSWORD="password"

# Test role
cd roles/vsphere_vm_deploy
molecule test -s default
```

### Running Integration Tests

Integration tests validate the full deployment workflow.

#### With vcsim:

```bash
# Start vcsim
docker compose -f tests/vcsim/docker-compose.yml up -d

# Run integration test
ansible-playbook tests/integration/full_deployment/test_single_fd.yml \
  -e topology_file=examples/vsphere_topology_single_fd.yml \
  -e parent_vcenter_hostname=localhost:8989 \
  -e parent_vcenter_username=user \
  -e parent_vcenter_password=pass
```

#### With real vSphere:

```bash
ansible-playbook tests/integration/full_deployment/test_single_fd.yml \
  -e topology_file=examples/vsphere_topology_single_fd.yml \
  --vault-password-file=.vault_pass
```

### Linting and Code Quality

#### Run ansible-lint:

```bash
ansible-lint playbooks/ roles/
```

#### Run yamllint:

```bash
yamllint .
```

#### Auto-fix common issues:

```bash
ansible-lint --fix playbooks/ roles/
```

### Testing the Full Deployment

1. **Create a topology file**:

```bash
cp examples/vsphere_topology_single_fd.yml my_topology.yml
# Edit my_topology.yml with your environment details
```

2. **Run preflight checks**:

```bash
ansible-playbook playbooks/preflight.yml \
  -e topology_file=my_topology.yml \
  --vault-password-file=.vault_pass
```

3. **Deploy**:

```bash
ansible-playbook playbooks/deploy_nested_vsphere.yml \
  -e topology_file=my_topology.yml \
  --vault-password-file=.vault_pass
```

4. **Verify idempotency**:

```bash
# Run again - should show no changes
ansible-playbook playbooks/deploy_nested_vsphere.yml \
  -e topology_file=my_topology.yml \
  --vault-password-file=.vault_pass
```

5. **Destroy (cleanup)**:

```bash
ansible-playbook playbooks/destroy_nested_vsphere.yml \
  -e deployment_name=my-deployment-name \
  --vault-password-file=.vault_pass
```

## Adding a New Role

### 1. Generate Role Structure

```bash
cd roles
ansible-galaxy role init my_new_role
```

### 2. Add Molecule Test

```bash
cd my_new_role
molecule init scenario -d delegated
```

### 3. Implement Role

Edit the following files:
- `defaults/main.yml`: Default variables
- `tasks/main.yml`: Main task file
- `meta/main.yml`: Role metadata and dependencies
- `README.md`: Role documentation

### 4. Write Tests

Edit molecule scenario files:
- `molecule/default/molecule.yml`: Molecule configuration
- `molecule/default/converge.yml`: Test playbook
- `molecule/default/verify.yml`: Verification assertions

### 5. Test Role

```bash
molecule test -s default
```

### 6. Document Role

Update `docs/ROLES.md` with:
- Role purpose
- Required variables
- Optional variables
- Example usage
- Dependencies

## Debugging

### Enable Debug Mode

```bash
export VSPHERE_DEBUG=true
ansible-playbook playbooks/deploy_nested_vsphere.yml \
  -e topology_file=my_topology.yml \
  -vvv \
  --vault-password-file=.vault_pass
```

### Check Ansible Logs

```bash
tail -f ansible.log
```

### Inspect Deployment State

```bash
cat state/my-deployment-name.yml
```

### Test Individual Tasks

```bash
# Create a test playbook
cat > test_task.yml <<EOF
---
- name: Test Task
  hosts: localhost
  tasks:
    - name: Include role
      include_role:
        name: vsphere_vm_deploy
        tasks_from: deploy_esxi.yml
      vars:
        # Your test variables
EOF

# Run it
ansible-playbook test_task.yml --vault-password-file=.vault_pass
```

## Common Issues and Solutions

### Issue: Collection not found

**Solution**:
```bash
ansible-galaxy collection install -r collections/requirements.yml --force
```

### Issue: Vault decryption failed

**Solution**:
- Verify `.vault_pass` file exists and has correct password
- Check `ansible.cfg` vault_password_file setting

### Issue: vcsim connection refused

**Solution**:
```bash
# Check if vcsim is running
docker ps | grep vcsim

# Restart vcsim
docker compose -f tests/vcsim/docker-compose.yml restart
```

### Issue: Module vmware_guest not found

**Solution**:
```bash
# Install community.vmware collection
ansible-galaxy collection install community.vmware --force

# Verify installation
ansible-galaxy collection list | grep vmware
```

## Best Practices

### Code Style

- Use descriptive task names: "Deploy ESXi VM" not "vmware_guest"
- Group related tasks in separate files
- Use YAML anchors for repeated configuration
- Always use FQCN for modules: `community.vmware.vmware_guest`
- Add comments for complex logic

### Variable Naming

- Prefix role variables with role name: `vsphere_vm_deploy_timeout`
- Use snake_case for all variables
- Document all variables in `defaults/main.yml`
- Use meaningful names: `esxi_memory_mb` not `mem`

### Idempotency

- Always check before create: Use `*_info` modules
- Use `state: present` instead of create/delete
- Set `changed_when: false` for info-gathering tasks
- Test idempotency: Run role twice, assert no changes

### Error Handling

- Use `retries` and `until` for flaky operations
- Provide meaningful error messages with `fail_msg`
- Use `failed_when` for conditional failures
- Log warnings for non-critical failures

### Testing

- Write molecule tests for every role
- Test both success and failure scenarios
- Verify idempotency in tests
- Use vcsim for CI, real vSphere for thorough testing

## Git Workflow

### Branch Naming

- Feature branches: `feature/add-storage-role`
- Bug fixes: `fix/tagging-retry-logic`
- Documentation: `docs/update-development-guide`

### Commit Messages

Follow conventional commits:

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`

Example:
```
feat(vsphere_vm_deploy): add support for custom disk controllers

- Allow specifying disk controller type in topology
- Default to paravirtual for backward compatibility
- Add tests for PVSCSI and LSI Logic controllers

Closes #123
```

### Pull Request Process

1. Create feature branch from `main` or `rewrite`
2. Make changes with descriptive commits
3. Run tests locally (linting, molecule, integration)
4. Update documentation
5. Submit PR with:
   - Clear description of changes
   - Test results
   - Related issue links
   - Breaking changes (if any)

## Resources

- [Ansible Best Practices](https://docs.ansible.com/ansible/latest/user_guide/playbooks_best_practices.html)
- [Molecule Documentation](https://molecule.readthedocs.io/)
- [community.vmware Collection](https://docs.ansible.com/ansible/latest/collections/community/vmware/)
- [vcsim Documentation](https://github.com/vmware/govmomi/tree/master/vcsim)
