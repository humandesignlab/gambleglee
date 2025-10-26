#!/bin/bash
# Restore script for GambleGlee AWS infrastructure
# This script restores infrastructure from backups

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."

    # Check if AWS CLI is installed
    if ! command_exists aws; then
        print_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi

    # Check if AWS credentials are configured
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        print_error "AWS credentials are not configured. Please run 'aws configure' first."
        exit 1
    fi

    # Check if Terraform is installed
    if ! command_exists terraform; then
        print_error "Terraform is not installed. Please install it first."
        exit 1
    fi

    print_success "All prerequisites are met"
}

# Function to list available backups
list_backups() {
    print_status "Available backups:"

    if [ -d "backups" ]; then
        ls -la backups/ | grep -E "\.tar\.gz$|^d" | awk '{print $9}' | grep -v "^\.$" | grep -v "^\.\.$"
    else
        print_warning "No backups directory found"
    fi
}

# Function to extract backup
extract_backup() {
    local backup_file=$1
    local restore_dir="restore_$(date +%Y%m%d_%H%M%S)"

    print_status "Extracting backup: $backup_file"

    if [ -f "$backup_file" ]; then
        mkdir -p "$restore_dir"
        tar -xzf "$backup_file" -C "$restore_dir"
        print_success "Backup extracted to: $restore_dir"
        echo "$restore_dir"
    else
        print_error "Backup file not found: $backup_file"
        exit 1
    fi
}

# Function to restore Terraform state
restore_terraform_state() {
    local restore_dir=$1
    print_status "Restoring Terraform state..."

    if [ -f "$restore_dir/terraform.tfstate" ]; then
        cp "$restore_dir/terraform.tfstate" infrastructure/terraform/
        print_success "Terraform state restored"
    else
        print_warning "Terraform state file not found in backup"
    fi
}

# Function to restore S3 buckets
restore_s3_buckets() {
    local restore_dir=$1
    print_status "Restoring S3 buckets..."

    # Find S3 backup directories
    local s3_backups=$(find "$restore_dir" -name "s3_*" -type d)

    for s3_backup in $s3_backups; do
        local bucket_name=$(basename "$s3_backup" | sed 's/s3_//')
        print_status "Restoring S3 bucket: $bucket_name"

        # Check if bucket exists
        if aws s3 ls "s3://$bucket_name" >/dev/null 2>&1; then
            # Sync backup to bucket
            aws s3 sync "$s3_backup" "s3://$bucket_name" --quiet
            print_success "S3 bucket $bucket_name restored"
        else
            print_warning "S3 bucket $bucket_name does not exist, skipping"
        fi
    done
}

# Function to restore application code
restore_application_code() {
    local restore_dir=$1
    print_status "Restoring application code..."

    if [ -d "$restore_dir/application" ]; then
        # Restore backend
        if [ -d "$restore_dir/application/backend" ]; then
            cp -r "$restore_dir/application/backend" ./
            print_success "Backend code restored"
        fi

        # Restore frontend
        if [ -d "$restore_dir/application/frontend" ]; then
            cp -r "$restore_dir/application/frontend" ./
            print_success "Frontend code restored"
        fi

        # Restore infrastructure
        if [ -d "$restore_dir/application/infrastructure" ]; then
            cp -r "$restore_dir/application/infrastructure" ./
            print_success "Infrastructure code restored"
        fi
    else
        print_warning "Application code not found in backup"
    fi
}

# Function to restore configuration
restore_configuration() {
    local restore_dir=$1
    print_status "Restoring configuration files..."

    if [ -d "$restore_dir/config" ]; then
        # Restore environment file
        if [ -f "$restore_dir/config/.env" ]; then
            cp "$restore_dir/config/.env" ./
            print_success "Environment file restored"
        fi

        # Restore Docker Compose file
        if [ -f "$restore_dir/config/docker-compose.yml" ]; then
            cp "$restore_dir/config/docker-compose.yml" ./
            print_success "Docker Compose file restored"
        fi

        # Restore README
        if [ -f "$restore_dir/config/README.md" ]; then
            cp "$restore_dir/config/README.md" ./
            print_success "README file restored"
        fi
    else
        print_warning "Configuration files not found in backup"
    fi
}

# Function to restore RDS from snapshot
restore_rds_from_snapshot() {
    local restore_dir=$1
    print_status "Restoring RDS from snapshot..."

    # List available snapshots
    local snapshots=$(aws rds describe-db-snapshots --query 'DBSnapshots[?contains(DBSnapshotIdentifier, `gambleglee-manual-backup`)].DBSnapshotIdentifier' --output text)

    if [ -n "$snapshots" ]; then
        print_status "Available RDS snapshots:"
        echo "$snapshots"

        # Get the most recent snapshot
        local latest_snapshot=$(echo "$snapshots" | tr ' ' '\n' | sort -r | head -n1)
        print_status "Using latest snapshot: $latest_snapshot"

        # Create new RDS instance from snapshot
        local new_instance_id="gambleglee-restored-$(date +%Y%m%d-%H%M%S)"

        print_warning "This will create a new RDS instance from the snapshot."
        print_warning "You may need to update your Terraform state and configuration."

        read -p "Do you want to continue? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            aws rds restore-db-instance-from-db-snapshot \
                --db-instance-identifier "$new_instance_id" \
                --db-snapshot-identifier "$latest_snapshot" \
                --db-instance-class db.t3.micro

            print_success "RDS instance restored: $new_instance_id"
        else
            print_status "RDS restore cancelled"
        fi
    else
        print_warning "No RDS snapshots found"
    fi
}

# Function to validate restore
validate_restore() {
    local restore_dir=$1
    print_status "Validating restore..."

    # Check if Terraform state is valid
    if [ -f "infrastructure/terraform/terraform.tfstate" ]; then
        cd infrastructure/terraform
        if terraform validate >/dev/null 2>&1; then
            print_success "Terraform state is valid"
        else
            print_warning "Terraform state validation failed"
        fi
        cd - >/dev/null
    fi

    # Check if application files exist
    if [ -d "backend" ] && [ -d "frontend" ]; then
        print_success "Application files restored"
    else
        print_warning "Application files may be incomplete"
    fi

    # Check if configuration files exist
    if [ -f ".env" ]; then
        print_success "Configuration files restored"
    else
        print_warning "Configuration files may be incomplete"
    fi
}

# Function to show restore summary
show_restore_summary() {
    local restore_dir=$1

    print_success "Restore completed!"
    echo ""
    print_status "Restored components:"
    echo "  - Terraform state"
    echo "  - S3 buckets"
    echo "  - Application code"
    echo "  - Configuration files"
    echo ""
    print_status "Next steps:"
    echo "1. Review and update configuration files"
    echo "2. Update Terraform state if needed"
    echo "3. Deploy infrastructure: ./infrastructure/deploy.sh"
    echo "4. Test the application"
    echo "5. Update DNS records if needed"
    echo ""
    print_warning "Important: Test the restore in a separate environment first!"
}

# Main function
main() {
    echo "=========================================="
    echo "GambleGlee AWS Infrastructure Restore"
    echo "=========================================="
    echo ""

    # Check prerequisites
    check_prerequisites

    # List available backups
    list_backups

    echo ""
    read -p "Enter backup file name (or path): " backup_file

    if [ -z "$backup_file" ]; then
        print_error "Backup file name is required"
        exit 1
    fi

    # Extract backup
    restore_dir=$(extract_backup "$backup_file")

    # Restore components
    restore_terraform_state "$restore_dir"
    restore_s3_buckets "$restore_dir"
    restore_application_code "$restore_dir"
    restore_configuration "$restore_dir"
    restore_rds_from_snapshot "$restore_dir"

    # Validate restore
    validate_restore "$restore_dir"

    # Show summary
    show_restore_summary "$restore_dir"
}

# Run main function
main "$@"
