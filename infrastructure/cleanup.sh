#!/bin/bash
# Cleanup script for GambleGlee AWS infrastructure
# This script destroys the infrastructure using Terraform

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

    # Check if Terraform is installed
    if ! command_exists terraform; then
        print_error "Terraform is not installed. Please install it first."
        exit 1
    fi

    # Check if AWS credentials are configured
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        print_error "AWS credentials are not configured. Please run 'aws configure' first."
        exit 1
    fi

    print_success "All prerequisites are met"
}

# Function to show what will be destroyed
show_destroy_plan() {
    print_status "Showing what will be destroyed..."
    cd infrastructure/terraform
    terraform plan -destroy
}

# Function to destroy infrastructure
destroy_infrastructure() {
    print_status "Destroying infrastructure..."
    terraform destroy -auto-approve
    print_success "Infrastructure destroyed"
}

# Function to clean up local files
cleanup_local_files() {
    print_status "Cleaning up local files..."

    # Remove Terraform state files
    if [ -f "infrastructure/terraform/terraform.tfstate" ]; then
        rm -f infrastructure/terraform/terraform.tfstate*
        print_status "Removed Terraform state files"
    fi

    # Remove Terraform plan files
    if [ -f "infrastructure/terraform/tfplan" ]; then
        rm -f infrastructure/terraform/tfplan
        print_status "Removed Terraform plan files"
    fi

    # Remove .terraform directory
    if [ -d "infrastructure/terraform/.terraform" ]; then
        rm -rf infrastructure/terraform/.terraform
        print_status "Removed .terraform directory"
    fi

    print_success "Local files cleaned up"
}

# Function to show cost savings
show_cost_savings() {
    print_status "Cost savings from cleanup:"
    echo "  - EC2 t3.micro: ~$8.50/month"
    echo "  - RDS db.t3.micro: ~$15/month"
    echo "  - ElastiCache cache.t3.micro: ~$15/month"
    echo "  - NAT Gateway: ~$45/month"
    echo "  - EIP: ~$3.65/month"
    echo "  - RDS Storage: ~$2.30/month"
    echo "  - S3 Storage: ~$0.50/month"
    echo "  - CloudWatch Logs: ~$0.50/month"
    echo "  - IVS: ~$0.50/hour (if used)"
    echo ""
    print_success "Total monthly savings: ~$90-100"
}

# Function to show what to keep
show_what_to_keep() {
    print_status "Resources that will be kept (if you want to keep them):"
    echo "  - S3 buckets (if they contain important data)"
    echo "  - CloudWatch logs (if you want to keep them)"
    echo "  - IAM roles and policies"
    echo "  - VPC (if you want to keep it for other resources)"
    echo ""
    print_warning "You may want to manually delete these resources if you don't need them"
}

# Main function
main() {
    echo "=========================================="
    echo "GambleGlee AWS Infrastructure Cleanup"
    echo "=========================================="
    echo ""

    # Check prerequisites
    check_prerequisites

    # Show what will be destroyed
    show_destroy_plan

    # Show cost savings
    show_cost_savings

    # Show what to keep
    show_what_to_keep

    echo ""
    print_warning "This will permanently destroy all infrastructure resources!"
    print_warning "Make sure you have backed up any important data."
    echo ""
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Cleanup cancelled"
        exit 0
    fi

    # Destroy infrastructure
    destroy_infrastructure

    # Clean up local files
    cleanup_local_files

    print_success "Cleanup completed successfully!"
    echo ""
    print_status "What was destroyed:"
    echo "  - EC2 instance and associated resources"
    echo "  - RDS PostgreSQL database"
    echo "  - ElastiCache Redis cluster"
    echo "  - S3 buckets (if empty)"
    echo "  - VPC and networking resources"
    echo "  - Security groups and IAM roles"
    echo "  - CloudWatch alarms and dashboards"
    echo "  - IVS channel and stream key"
    echo ""
    print_status "You can now safely close your AWS account or use the resources for other projects."
}

# Run main function
main "$@"
