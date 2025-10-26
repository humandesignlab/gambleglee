#!/bin/bash
# Deployment script for GambleGlee AWS infrastructure
# This script deploys the infrastructure using Terraform

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

# Function to initialize Terraform
init_terraform() {
    print_status "Initializing Terraform..."
    cd infrastructure/terraform
    terraform init
    print_success "Terraform initialized"
}

# Function to plan Terraform deployment
plan_terraform() {
    print_status "Planning Terraform deployment..."
    terraform plan -out=tfplan
    print_success "Terraform plan created"
}

# Function to apply Terraform deployment
apply_terraform() {
    print_status "Applying Terraform deployment..."
    terraform apply tfplan
    print_success "Terraform deployment completed"
}

# Function to show outputs
show_outputs() {
    print_status "Infrastructure outputs:"
    terraform output
}

# Function to create SSH key if it doesn't exist
create_ssh_key() {
    if [ ! -f ~/.ssh/id_rsa.pub ]; then
        print_status "Creating SSH key pair..."
        ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ""
        print_success "SSH key pair created"
    else
        print_status "SSH key pair already exists"
    fi
}

# Function to check Free Tier usage
check_free_tier() {
    print_status "Checking AWS Free Tier usage..."

    # Check EC2 instances
    ec2_count=$(aws ec2 describe-instances --query 'Reservations[*].Instances[*].[InstanceId,State.Name]' --output text | grep -c "running" || echo "0")
    if [ "$ec2_count" -gt 0 ]; then
        print_warning "You have $ec2_count running EC2 instances. Free Tier allows 750 hours/month."
    fi

    # Check RDS instances
    rds_count=$(aws rds describe-db-instances --query 'DBInstances[*].[DBInstanceIdentifier,DBInstanceStatus]' --output text | grep -c "available" || echo "0")
    if [ "$rds_count" -gt 0 ]; then
        print_warning "You have $rds_count running RDS instances. Free Tier allows 750 hours/month."
    fi

    # Check ElastiCache clusters
    cache_count=$(aws elasticache describe-cache-clusters --query 'CacheClusters[*].[CacheClusterId,CacheClusterStatus]' --output text | grep -c "available" || echo "0")
    if [ "$cache_count" -gt 0 ]; then
        print_warning "You have $cache_count running ElastiCache clusters. Free Tier allows 750 hours/month."
    fi

    print_success "Free Tier usage check completed"
}

# Function to estimate costs
estimate_costs() {
    print_status "Estimating monthly costs..."

    # Free Tier resources (0 cost for 12 months)
    print_status "Free Tier resources (0 cost for 12 months):"
    echo "  - EC2 t3.micro: 750 hours/month"
    echo "  - RDS db.t3.micro: 750 hours/month"
    echo "  - ElastiCache cache.t3.micro: 750 hours/month"
    echo "  - S3: 5GB storage, 20,000 GET requests"
    echo "  - CloudFront: 1TB data transfer out"
    echo "  - Route53: 1 hosted zone"
    echo "  - CloudWatch: 10 custom metrics, 1GB log ingestion"

    # Paid resources
    print_status "Paid resources (estimated monthly cost):"
    echo "  - NAT Gateway: ~$45/month"
    echo "  - EIP: ~$3.65/month"
    echo "  - RDS Storage: ~$2.30/month (20GB)"
    echo "  - S3 Storage: ~$0.50/month (additional storage)"
    echo "  - CloudWatch Logs: ~$0.50/month (additional logs)"
    echo "  - IVS: ~$0.50/hour (if used)"

    print_warning "Total estimated monthly cost: ~$50-100 (after Free Tier)"
}

# Function to show next steps
show_next_steps() {
    print_success "Infrastructure deployment completed!"
    echo ""
    print_status "Next steps:"
    echo "1. Get the EC2 public IP from the outputs above"
    echo "2. SSH into the instance: ssh -i ~/.ssh/id_rsa ec2-user@<EC2_IP>"
    echo "3. Check the application status: sudo systemctl status gambleglee"
    echo "4. View application logs: docker-compose logs -f"
    echo "5. Access the application at: http://<EC2_IP>"
    echo ""
    print_status "Important files:"
    echo "  - Application directory: /opt/gambleglee"
    echo "  - Environment file: /opt/gambleglee/.env"
    echo "  - Docker Compose: /opt/gambleglee/docker-compose.yml"
    echo "  - Nginx config: /opt/gambleglee/nginx.conf"
    echo ""
    print_status "Monitoring:"
    echo "  - CloudWatch Dashboard: Check the dashboard URL in outputs"
    echo "  - Application logs: /opt/gambleglee/logs/"
    echo "  - System logs: /var/log/"
}

# Main function
main() {
    echo "=========================================="
    echo "GambleGlee AWS Infrastructure Deployment"
    echo "=========================================="
    echo ""

    # Check prerequisites
    check_prerequisites

    # Create SSH key if needed
    create_ssh_key

    # Check Free Tier usage
    check_free_tier

    # Estimate costs
    estimate_costs

    echo ""
    read -p "Do you want to continue with the deployment? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Deployment cancelled"
        exit 0
    fi

    # Initialize Terraform
    init_terraform

    # Plan deployment
    plan_terraform

    echo ""
    read -p "Do you want to apply this plan? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Deployment cancelled"
        exit 0
    fi

    # Apply deployment
    apply_terraform

    # Show outputs
    show_outputs

    # Show next steps
    show_next_steps
}

# Run main function
main "$@"
