#!/bin/bash
#
# Automated migration from v1 to v2 of nested-ova-ansible
#
# This script:
# 1. Backs up existing v1 files
# 2. Converts platform.yaml to vsphere_topology.yml
# 3. Sets up Ansible Vault
# 4. Installs dependencies
# 5. Validates the new configuration
#
# Usage:
#   ./migrate_from_v1.sh [--dry-run] [--skip-backup]

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKUP_DIR="${PROJECT_ROOT}/v1_backup_$(date +%Y%m%d_%H%M%S)"
DRY_RUN=false
SKIP_BACKUP=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --skip-backup)
            SKIP_BACKUP=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--dry-run] [--skip-backup]"
            echo ""
            echo "Options:"
            echo "  --dry-run      Show what would be done without making changes"
            echo "  --skip-backup  Skip backing up v1 files"
            echo "  -h, --help     Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

run_command() {
    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY-RUN]${NC} Would run: $*"
    else
        "$@"
    fi
}

# Validation functions
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "python3 not found. Please install Python 3.9 or later."
        exit 1
    fi

    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    log_success "Python ${PYTHON_VERSION} found"

    # Check Ansible
    if ! command -v ansible &> /dev/null; then
        log_error "ansible not found. Please install Ansible 11.0+ (includes ansible-core 2.18+)."
        exit 1
    fi

    ANSIBLE_VERSION=$(ansible --version | head -n1 | awk '{print $2}')
    log_success "Ansible ${ANSIBLE_VERSION} found"

    # Check ansible-galaxy
    if ! command -v ansible-galaxy &> /dev/null; then
        log_error "ansible-galaxy not found."
        exit 1
    fi

    # Check for required files
    if [ ! -f "${PROJECT_ROOT}/group_vars/all.yml" ]; then
        log_warning "group_vars/all.yml not found - may be starting fresh"
    fi
}

backup_v1_files() {
    if [ "$SKIP_BACKUP" = true ]; then
        log_info "Skipping backup (--skip-backup specified)"
        return
    fi

    log_info "Backing up v1 files to ${BACKUP_DIR}..."

    if [ "$DRY_RUN" = false ]; then
        mkdir -p "${BACKUP_DIR}"

        # Backup old playbook files
        local v1_files=(
            "esxinested.yml"
            "vcnested.yml"
            "addhosts_vcenter.yml"
            "dvs_hosts_vcenter.yml"
            "create_datastore.yml"
            "tagging.yml"
            "host_groups.yml"
            "getcerts.yml"
            "main.yml"
            "nfshostip.yml"
            "packlocal.yml"
            "vsphere_remove.yml"
            "group_vars/all.yml"
        )

        for file in "${v1_files[@]}"; do
            if [ -f "${PROJECT_ROOT}/${file}" ]; then
                run_command cp -v "${PROJECT_ROOT}/${file}" "${BACKUP_DIR}/"
            fi
        done

        # Backup platform.yaml if it exists
        if [ -f "${PROJECT_ROOT}/platform.yaml" ]; then
            run_command cp -v "${PROJECT_ROOT}/platform.yaml" "${BACKUP_DIR}/"
        fi

        log_success "Backup complete: ${BACKUP_DIR}"
    else
        log_info "Would create backup in: ${BACKUP_DIR}"
    fi
}

convert_topology() {
    log_info "Converting topology configuration..."

    local PLATFORM_FILE="${PROJECT_ROOT}/platform.yaml"
    local TOPOLOGY_FILE="${PROJECT_ROOT}/vsphere_topology.yml"

    if [ ! -f "${PLATFORM_FILE}" ]; then
        log_warning "platform.yaml not found - skipping conversion"
        log_info "You'll need to create vsphere_topology.yml manually"
        return
    fi

    if [ -f "${TOPOLOGY_FILE}" ]; then
        log_warning "vsphere_topology.yml already exists - skipping conversion"
        return
    fi

    run_command "${SCRIPT_DIR}/convert_topology.py" \
        "${PLATFORM_FILE}" \
        --output "${TOPOLOGY_FILE}" \
        --pretty

    if [ "$DRY_RUN" = false ]; then
        log_success "Topology converted: ${TOPOLOGY_FILE}"
        log_warning "Please review and adjust the converted topology file!"
    fi
}

setup_vault() {
    log_info "Setting up Ansible Vault..."

    local VAULT_FILE="${PROJECT_ROOT}/group_vars/all/vault.yml"

    if [ -f "${VAULT_FILE}" ]; then
        log_info "Vault file already exists - checking if encrypted..."

        if head -n1 "${VAULT_FILE}" | grep -q "ANSIBLE_VAULT"; then
            log_success "Vault file is encrypted"
            return
        else
            log_warning "Vault file exists but is not encrypted"
            log_info "Encrypt it with: ansible-vault encrypt ${VAULT_FILE}"
            return
        fi
    fi

    log_warning "Vault file not found at ${VAULT_FILE}"
    log_info "The template should already exist from v2 setup"
    log_info "Edit the file and replace CHANGE_ME values, then encrypt with:"
    log_info "  ansible-vault encrypt ${VAULT_FILE}"
}

install_dependencies() {
    log_info "Installing dependencies..."

    # Install Python dependencies
    if [ -f "${PROJECT_ROOT}/requirements.txt" ]; then
        log_info "Installing Python dependencies..."
        run_command pip3 install -r "${PROJECT_ROOT}/requirements.txt"
        if [ "$DRY_RUN" = false ]; then
            log_success "Python dependencies installed"
        fi
    fi

    # Install Ansible collections
    if [ -f "${PROJECT_ROOT}/collections/requirements.yml" ]; then
        log_info "Installing Ansible collections..."
        run_command ansible-galaxy collection install \
            -r "${PROJECT_ROOT}/collections/requirements.yml" \
            --force
        if [ "$DRY_RUN" = false ]; then
            log_success "Ansible collections installed"
        fi
    fi
}

validate_configuration() {
    log_info "Validating configuration..."

    # Check required files exist
    local required_files=(
        "ansible.cfg"
        "collections/requirements.yml"
        "requirements.txt"
        "group_vars/all/vsphere_defaults.yml"
        "playbooks/deploy_nested_vsphere.yml"
    )

    local missing_files=()
    for file in "${required_files[@]}"; do
        if [ ! -f "${PROJECT_ROOT}/${file}" ]; then
            missing_files+=("${file}")
        fi
    done

    if [ ${#missing_files[@]} -gt 0 ]; then
        log_error "Missing required files:"
        for file in "${missing_files[@]}"; do
            echo "  - ${file}"
        done
        return 1
    fi

    log_success "All required files present"

    # Check roles exist
    local required_roles=(
        "vsphere_vm_deploy"
        "vsphere_datacenter_config"
        "vsphere_host_config"
        "vsphere_networking"
        "vsphere_storage"
        "vsphere_tagging"
        "vsphere_host_groups"
    )

    local missing_roles=()
    for role in "${required_roles[@]}"; do
        if [ ! -d "${PROJECT_ROOT}/roles/${role}" ]; then
            missing_roles+=("${role}")
        fi
    done

    if [ ${#missing_roles[@]} -gt 0 ]; then
        log_error "Missing required roles:"
        for role in "${missing_roles[@]}"; do
            echo "  - ${role}"
        done
        return 1
    fi

    log_success "All required roles present"

    # Run ansible-lint if available
    if command -v ansible-lint &> /dev/null; then
        log_info "Running ansible-lint..."
        if run_command ansible-lint "${PROJECT_ROOT}" --quiet; then
            log_success "ansible-lint passed"
        else
            log_warning "ansible-lint found issues (non-fatal)"
        fi
    fi

    return 0
}

create_migration_summary() {
    log_info "Creating migration summary..."

    local SUMMARY_FILE="${PROJECT_ROOT}/MIGRATION_SUMMARY.txt"

    if [ "$DRY_RUN" = false ]; then
        cat > "${SUMMARY_FILE}" << EOF
Nested vSphere Ansible - Migration Summary
==========================================

Migration Date: $(date)
Backup Location: ${BACKUP_DIR}

Next Steps:
-----------

1. Review the converted topology file:
   ${PROJECT_ROOT}/vsphere_topology.yml

2. Update credentials in vault file:
   ${PROJECT_ROOT}/group_vars/all/vault.yml

   a. Edit the file and replace all CHANGE_ME values
   b. Encrypt the file:
      ansible-vault encrypt group_vars/all/vault.yml

3. (Optional) Set vault password file:
   echo "your-vault-password" > .vault_pass
   chmod 600 .vault_pass

4. Review and update example topologies in:
   ${PROJECT_ROOT}/examples/

5. Run preflight validation:
   ansible-playbook playbooks/preflight.yml \\
     -e topology_file=vsphere_topology.yml

6. Deploy your nested environment:
   ansible-playbook playbooks/deploy_nested_vsphere.yml \\
     -e topology_file=vsphere_topology.yml \\
     --vault-password-file=.vault_pass

Documentation:
--------------
- DEVELOPMENT.md: Local development guide
- VARIABLES.md: Variable reference
- MIGRATION.md: Detailed migration guide
- README.md: Project overview

Support:
--------
If you encounter issues, check the logs in:
- Backup: ${BACKUP_DIR}
- Documentation: ${PROJECT_ROOT}/docs/

EOF

        log_success "Migration summary created: ${SUMMARY_FILE}"
        cat "${SUMMARY_FILE}"
    fi
}

# Main migration flow
main() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Nested vSphere Ansible v1 → v2 Migration${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    if [ "$DRY_RUN" = true ]; then
        log_warning "Running in DRY-RUN mode - no changes will be made"
        echo ""
    fi

    # Step 1: Prerequisites
    check_prerequisites

    # Step 2: Backup
    backup_v1_files

    # Step 3: Convert topology
    convert_topology

    # Step 4: Setup vault
    setup_vault

    # Step 5: Install dependencies
    install_dependencies

    # Step 6: Validate
    if ! validate_configuration; then
        log_error "Configuration validation failed"
        exit 1
    fi

    # Step 7: Create summary
    create_migration_summary

    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Migration Complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    log_info "Review MIGRATION_SUMMARY.txt for next steps"
}

# Run main function
main "$@"
