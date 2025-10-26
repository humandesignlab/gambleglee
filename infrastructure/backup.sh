#!/bin/bash
# Backup script for GambleGlee AWS infrastructure
# This script creates backups of important data and configurations

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

    print_success "All prerequisites are met"
}

# Function to create backup directory
create_backup_directory() {
    local backup_dir="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    echo "$backup_dir"
}

# Function to backup Terraform state
backup_terraform_state() {
    local backup_dir=$1
    print_status "Backing up Terraform state..."

    if [ -f "infrastructure/terraform/terraform.tfstate" ]; then
        cp infrastructure/terraform/terraform.tfstate "$backup_dir/"
        print_success "Terraform state backed up"
    else
        print_warning "Terraform state file not found"
    fi
}

# Function to backup RDS database
backup_rds_database() {
    local backup_dir=$1
    print_status "Backing up RDS database..."

    # Get RDS instance identifier
    if [ -f "infrastructure/terraform/terraform.tfstate" ]; then
        rds_instance_id=$(cd infrastructure/terraform && terraform output -raw rds_endpoint 2>/dev/null | cut -d. -f1 || echo "")

        if [ -n "$rds_instance_id" ]; then
            # Create manual snapshot
            snapshot_id="gambleglee-manual-backup-$(date +%Y%m%d-%H%M%S)"
            aws rds create-db-snapshot \
                --db-instance-identifier "$rds_instance_id" \
                --db-snapshot-identifier "$snapshot_id" \
                --tags Key=BackupType,Value=Manual Key=CreatedBy,Value=backup-script

            print_success "RDS snapshot created: $snapshot_id"
        else
            print_warning "RDS instance identifier not found"
        fi
    else
        print_warning "Terraform state file not found"
    fi
}

# Function to backup S3 buckets
backup_s3_buckets() {
    local backup_dir=$1
    print_status "Backing up S3 buckets..."

    # Get S3 bucket names
    if [ -f "infrastructure/terraform/terraform.tfstate" ]; then
        main_bucket=$(cd infrastructure/terraform && terraform output -raw s3_main_bucket 2>/dev/null || echo "")
        static_bucket=$(cd infrastructure/terraform && terraform output -raw s3_static_bucket 2>/dev/null || echo "")
        uploads_bucket=$(cd infrastructure/terraform && terraform output -raw s3_uploads_bucket 2>/dev/null || echo "")

        for bucket in $main_bucket $static_bucket $uploads_bucket; do
            if [ -n "$bucket" ]; then
                # Sync bucket to local directory
                local bucket_backup_dir="$backup_dir/s3_$bucket"
                mkdir -p "$bucket_backup_dir"

                aws s3 sync "s3://$bucket" "$bucket_backup_dir" --quiet
                print_success "S3 bucket $bucket backed up"
            fi
        done
    else
        print_warning "Terraform state file not found"
    fi
}

# Function to backup application code
backup_application_code() {
    local backup_dir=$1
    print_status "Backing up application code..."

    # Create application backup
    local app_backup_dir="$backup_dir/application"
    mkdir -p "$app_backup_dir"

    # Copy application files
    if [ -d "backend" ]; then
        cp -r backend "$app_backup_dir/"
        print_success "Backend code backed up"
    fi

    if [ -d "frontend" ]; then
        cp -r frontend "$app_backup_dir/"
        print_success "Frontend code backed up"
    fi

    if [ -d "infrastructure" ]; then
        cp -r infrastructure "$app_backup_dir/"
        print_success "Infrastructure code backed up"
    fi
}

# Function to backup configuration files
backup_configuration() {
    local backup_dir=$1
    print_status "Backing up configuration files..."

    # Create config backup directory
    local config_backup_dir="$backup_dir/config"
    mkdir -p "$config_backup_dir"

    # Copy configuration files
    if [ -f ".env" ]; then
        cp .env "$config_backup_dir/"
        print_success "Environment file backed up"
    fi

    if [ -f "docker-compose.yml" ]; then
        cp docker-compose.yml "$config_backup_dir/"
        print_success "Docker Compose file backed up"
    fi

    if [ -f "README.md" ]; then
        cp README.md "$config_backup_dir/"
        print_success "README file backed up"
    fi
}

# Function to backup CloudWatch logs
backup_cloudwatch_logs() {
    local backup_dir=$1
    print_status "Backing up CloudWatch logs..."

    # Get log groups
    local log_groups=$(aws logs describe-log-groups --query 'logGroups[?contains(logGroupName, `gambleglee`)].logGroupName' --output text)

    if [ -n "$log_groups" ]; then
        local logs_backup_dir="$backup_dir/cloudwatch_logs"
        mkdir -p "$logs_backup_dir"

        for log_group in $log_groups; do
            # Export logs to S3 (requires additional setup)
            print_status "Log group $log_group found (manual export required)"
        done

        print_success "CloudWatch log groups identified"
    else
        print_warning "No CloudWatch log groups found"
    fi
}

# Function to create backup manifest
create_backup_manifest() {
    local backup_dir=$1
    print_status "Creating backup manifest..."

    local manifest_file="$backup_dir/BACKUP_MANIFEST.txt"

    cat > "$manifest_file" << EOF
GambleGlee Infrastructure Backup
Created: $(date)
Backup Directory: $backup_dir

Contents:
- terraform.tfstate: Terraform state file
- s3_*: S3 bucket backups
- application/: Application code
- config/: Configuration files
- cloudwatch_logs/: CloudWatch log information

Restore Instructions:
1. Restore Terraform state: cp terraform.tfstate infrastructure/terraform/
2. Restore S3 buckets: aws s3 sync s3_backup/ s3://bucket-name/
3. Restore application: cp -r application/* ./
4. Restore configuration: cp -r config/* ./

Notes:
- RDS snapshots are stored in AWS (check RDS console)
- CloudWatch logs require manual export
- Test restore process in a separate environment first
EOF

    print_success "Backup manifest created"
}

# Function to compress backup
compress_backup() {
    local backup_dir=$1
    print_status "Compressing backup..."

    local backup_name=$(basename "$backup_dir")
    local backup_archive="${backup_name}.tar.gz"

    tar -czf "$backup_archive" -C "$(dirname "$backup_dir")" "$(basename "$backup_dir")"

    print_success "Backup compressed: $backup_archive"
    echo "$backup_archive"
}

# Function to show backup summary
show_backup_summary() {
    local backup_dir=$1
    local backup_archive=$2

    print_success "Backup completed successfully!"
    echo ""
    print_status "Backup details:"
    echo "  - Directory: $backup_dir"
    echo "  - Archive: $backup_archive"
    echo "  - Size: $(du -h "$backup_archive" | cut -f1)"
    echo ""
    print_status "Next steps:"
    echo "1. Store the backup archive in a secure location"
    echo "2. Test the restore process in a separate environment"
    echo "3. Set up automated backups for production"
    echo "4. Consider using AWS Backup for enterprise-grade backups"
}

# Main function
main() {
    echo "=========================================="
    echo "GambleGlee AWS Infrastructure Backup"
    echo "=========================================="
    echo ""

    # Check prerequisites
    check_prerequisites

    # Create backup directory
    backup_dir=$(create_backup_directory)
    print_status "Backup directory: $backup_dir"

    # Perform backups
    backup_terraform_state "$backup_dir"
    backup_rds_database "$backup_dir"
    backup_s3_buckets "$backup_dir"
    backup_application_code "$backup_dir"
    backup_configuration "$backup_dir"
    backup_cloudwatch_logs "$backup_dir"

    # Create manifest
    create_backup_manifest "$backup_dir"

    # Compress backup
    backup_archive=$(compress_backup "$backup_dir")

    # Show summary
    show_backup_summary "$backup_dir" "$backup_archive"
}

# Run main function
main "$@"
