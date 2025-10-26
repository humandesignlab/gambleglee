#!/bin/bash
# Health check script for GambleGlee AWS infrastructure
# This script checks the health of all infrastructure components

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

# Function to check EC2 instance
check_ec2() {
    print_status "Checking EC2 instance..."

    # Get instance ID from Terraform output
    if [ -f "infrastructure/terraform/terraform.tfstate" ]; then
        instance_id=$(cd infrastructure/terraform && terraform output -raw ec2_instance_id 2>/dev/null || echo "")

        if [ -n "$instance_id" ]; then
            # Check instance status
            status=$(aws ec2 describe-instances --instance-ids $instance_id --query 'Reservations[0].Instances[0].State.Name' --output text)

            if [ "$status" = "running" ]; then
                print_success "EC2 instance is running"

                # Get public IP
                public_ip=$(aws ec2 describe-instances --instance-ids $instance_id --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
                print_status "Public IP: $public_ip"

                # Check if instance is reachable
                if ping -c 1 $public_ip >/dev/null 2>&1; then
                    print_success "EC2 instance is reachable"
                else
                    print_warning "EC2 instance is not reachable via ping"
                fi
            else
                print_error "EC2 instance is not running (status: $status)"
            fi
        else
            print_warning "EC2 instance ID not found in Terraform state"
        fi
    else
        print_warning "Terraform state file not found"
    fi
}

# Function to check RDS instance
check_rds() {
    print_status "Checking RDS instance..."

    # Get RDS endpoint from Terraform output
    if [ -f "infrastructure/terraform/terraform.tfstate" ]; then
        rds_endpoint=$(cd infrastructure/terraform && terraform output -raw rds_endpoint 2>/dev/null || echo "")

        if [ -n "$rds_endpoint" ]; then
            # Check RDS status
            status=$(aws rds describe-db-instances --query "DBInstances[?Endpoint.Address=='$rds_endpoint'].DBInstanceStatus" --output text)

            if [ "$status" = "available" ]; then
                print_success "RDS instance is available"
            else
                print_error "RDS instance is not available (status: $status)"
            fi
        else
            print_warning "RDS endpoint not found in Terraform state"
        fi
    else
        print_warning "Terraform state file not found"
    fi
}

# Function to check ElastiCache cluster
check_elasticache() {
    print_status "Checking ElastiCache cluster..."

    # Get Redis endpoint from Terraform output
    if [ -f "infrastructure/terraform/terraform.tfstate" ]; then
        redis_endpoint=$(cd infrastructure/terraform && terraform output -raw redis_endpoint 2>/dev/null || echo "")

        if [ -n "$redis_endpoint" ]; then
            # Check ElastiCache status
            status=$(aws elasticache describe-cache-clusters --query "CacheClusters[?Endpoint.Address=='$redis_endpoint'].CacheClusterStatus" --output text)

            if [ "$status" = "available" ]; then
                print_success "ElastiCache cluster is available"
            else
                print_error "ElastiCache cluster is not available (status: $status)"
            fi
        else
            print_warning "Redis endpoint not found in Terraform state"
        fi
    else
        print_warning "Terraform state file not found"
    fi
}

# Function to check S3 buckets
check_s3() {
    print_status "Checking S3 buckets..."

    # Get S3 bucket names from Terraform output
    if [ -f "infrastructure/terraform/terraform.tfstate" ]; then
        main_bucket=$(cd infrastructure/terraform && terraform output -raw s3_main_bucket 2>/dev/null || echo "")
        static_bucket=$(cd infrastructure/terraform && terraform output -raw s3_static_bucket 2>/dev/null || echo "")
        uploads_bucket=$(cd infrastructure/terraform && terraform output -raw s3_uploads_bucket 2>/dev/null || echo "")

        for bucket in $main_bucket $static_bucket $uploads_bucket; do
            if [ -n "$bucket" ]; then
                if aws s3 ls s3://$bucket >/dev/null 2>&1; then
                    print_success "S3 bucket $bucket is accessible"
                else
                    print_error "S3 bucket $bucket is not accessible"
                fi
            fi
        done
    else
        print_warning "Terraform state file not found"
    fi
}

# Function to check application health
check_application() {
    print_status "Checking application health..."

    # Get EC2 public IP
    if [ -f "infrastructure/terraform/terraform.tfstate" ]; then
        public_ip=$(cd infrastructure/terraform && terraform output -raw ec2_public_ip 2>/dev/null || echo "")

        if [ -n "$public_ip" ]; then
            # Check if application is responding
            if curl -f http://$public_ip/health >/dev/null 2>&1; then
                print_success "Application is responding"
            else
                print_warning "Application is not responding (this is normal if not deployed yet)"
            fi
        else
            print_warning "EC2 public IP not found in Terraform state"
        fi
    else
        print_warning "Terraform state file not found"
    fi
}

# Function to check CloudWatch logs
check_cloudwatch() {
    print_status "Checking CloudWatch logs..."

    # Check if log groups exist
    log_groups=$(aws logs describe-log-groups --query 'logGroups[?contains(logGroupName, `gambleglee`)].logGroupName' --output text)

    if [ -n "$log_groups" ]; then
        print_success "CloudWatch log groups found:"
        for group in $log_groups; do
            print_status "  - $group"
        done
    else
        print_warning "No CloudWatch log groups found"
    fi
}

# Function to check security groups
check_security_groups() {
    print_status "Checking security groups..."

    # Get security groups
    security_groups=$(aws ec2 describe-security-groups --query 'SecurityGroups[?contains(GroupName, `gambleglee`)].GroupName' --output text)

    if [ -n "$security_groups" ]; then
        print_success "Security groups found:"
        for group in $security_groups; do
            print_status "  - $group"
        done
    else
        print_warning "No security groups found"
    fi
}

# Function to check IAM roles
check_iam_roles() {
    print_status "Checking IAM roles..."

    # Get IAM roles
    iam_roles=$(aws iam list-roles --query 'Roles[?contains(RoleName, `gambleglee`)].RoleName' --output text)

    if [ -n "$iam_roles" ]; then
        print_success "IAM roles found:"
        for role in $iam_roles; do
            print_status "  - $role"
        done
    else
        print_warning "No IAM roles found"
    fi
}

# Function to show summary
show_summary() {
    print_status "Health check summary:"
    echo ""
    echo "✅ Infrastructure components checked:"
    echo "  - EC2 instance"
    echo "  - RDS database"
    echo "  - ElastiCache cluster"
    echo "  - S3 buckets"
    echo "  - Application health"
    echo "  - CloudWatch logs"
    echo "  - Security groups"
    echo "  - IAM roles"
    echo ""
    print_status "For detailed monitoring, check the CloudWatch dashboard"
}

# Main function
main() {
    echo "=========================================="
    echo "GambleGlee AWS Infrastructure Health Check"
    echo "=========================================="
    echo ""

    # Check prerequisites
    check_prerequisites

    # Check infrastructure components
    check_ec2
    check_rds
    check_elasticache
    check_s3
    check_application
    check_cloudwatch
    check_security_groups
    check_iam_roles

    # Show summary
    show_summary

    print_success "Health check completed!"
}

# Run main function
main "$@"
