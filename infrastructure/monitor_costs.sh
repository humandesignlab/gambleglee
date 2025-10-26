#!/bin/bash
# Cost monitoring script for GambleGlee AWS infrastructure
# This script monitors AWS costs and provides usage insights

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

# Function to get current month costs
get_current_month_costs() {
    print_status "Getting current month costs..."

    # Get current month start date
    current_month=$(date +%Y-%m-01)

    # Get costs for current month
    aws ce get-cost-and-usage \
        --time-period Start=$current_month,End=$(date +%Y-%m-%d) \
        --granularity MONTHLY \
        --metrics BlendedCost \
        --query 'ResultsByTime[0].Total.BlendedCost.Amount' \
        --output text
}

# Function to get service costs
get_service_costs() {
    print_status "Getting service costs..."

    # Get current month start date
    current_month=$(date +%Y-%m-01)

    # Get costs by service
    aws ce get-cost-and-usage \
        --time-period Start=$current_month,End=$(date +%Y-%m-%d) \
        --granularity MONTHLY \
        --metrics BlendedCost \
        --group-by Type=DIMENSION,Key=SERVICE \
        --query 'ResultsByTime[0].Groups[*].[Keys[0],Metrics.BlendedCost.Amount]' \
        --output table
}

# Function to get resource usage
get_resource_usage() {
    print_status "Getting resource usage..."

    # EC2 instances
    print_status "EC2 Instances:"
    aws ec2 describe-instances \
        --query 'Reservations[*].Instances[*].[InstanceId,InstanceType,State.Name,LaunchTime]' \
        --output table

    # RDS instances
    print_status "RDS Instances:"
    aws rds describe-db-instances \
        --query 'DBInstances[*].[DBInstanceIdentifier,DBInstanceClass,DBInstanceStatus,AllocatedStorage]' \
        --output table

    # ElastiCache clusters
    print_status "ElastiCache Clusters:"
    aws elasticache describe-cache-clusters \
        --query 'CacheClusters[*].[CacheClusterId,CacheNodeType,CacheClusterStatus,NumCacheNodes]' \
        --output table

    # S3 buckets
    print_status "S3 Buckets:"
    aws s3 ls --human-readable --summarize
}

# Function to check Free Tier usage
check_free_tier_usage() {
    print_status "Checking Free Tier usage..."

    # Get Free Tier usage
    aws ce get-cost-and-usage \
        --time-period Start=$(date +%Y-%m-01),End=$(date +%Y-%m-%d) \
        --granularity MONTHLY \
        --metrics BlendedCost \
        --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon Elastic Compute Cloud - Compute","Amazon Relational Database Service","Amazon ElastiCache","Amazon Simple Storage Service"]}}' \
        --query 'ResultsByTime[0].Total.BlendedCost.Amount' \
        --output text
}

# Function to estimate monthly costs
estimate_monthly_costs() {
    print_status "Estimating monthly costs..."

    # Get current month costs
    current_costs=$(get_current_month_costs)

    # Calculate estimated monthly cost
    days_in_month=$(date -d "$(date +%Y-%m-01) +1 month -1 day" +%d)
    current_day=$(date +%d)
    estimated_monthly=$(echo "scale=2; $current_costs * $days_in_month / $current_day" | bc)

    print_status "Current month costs: \$$current_costs"
    print_status "Estimated monthly cost: \$$estimated_monthly"

    # Check if over Free Tier
    if (( $(echo "$estimated_monthly > 0" | bc -l) )); then
        print_warning "You are using paid resources. Consider optimizing to stay within Free Tier."
    else
        print_success "You are within Free Tier limits."
    fi
}

# Function to show cost optimization tips
show_optimization_tips() {
    print_status "Cost optimization tips:"
    echo ""
    echo "1. Use Free Tier resources:"
    echo "   - EC2 t3.micro: 750 hours/month"
    echo "   - RDS db.t3.micro: 750 hours/month"
    echo "   - ElastiCache cache.t3.micro: 750 hours/month"
    echo ""
    echo "2. Optimize storage:"
    echo "   - Use S3 lifecycle policies"
    echo "   - Delete unused snapshots"
    echo "   - Compress logs"
    echo ""
    echo "3. Monitor usage:"
    echo "   - Set up billing alerts"
    echo "   - Review costs regularly"
    echo "   - Use AWS Cost Explorer"
    echo ""
    echo "4. Consider alternatives:"
    echo "   - Use Spot Instances for non-critical workloads"
    echo "   - Use Reserved Instances for predictable workloads"
    echo "   - Use S3 Intelligent Tiering"
}

# Function to set up billing alerts
setup_billing_alerts() {
    print_status "Setting up billing alerts..."

    # Create SNS topic for billing alerts
    topic_arn=$(aws sns create-topic --name gambleglee-billing-alerts --query 'TopicArn' --output text)

    # Create CloudWatch alarm for billing
    aws cloudwatch put-metric-alarm \
        --alarm-name "GambleGlee-Billing-Alert" \
        --alarm-description "Alert when monthly costs exceed $50" \
        --metric-name EstimatedCharges \
        --namespace AWS/Billing \
        --statistic Maximum \
        --period 86400 \
        --threshold 50 \
        --comparison-operator GreaterThanThreshold \
        --evaluation-periods 1 \
        --alarm-actions $topic_arn

    print_success "Billing alerts set up"
    print_status "SNS Topic ARN: $topic_arn"
}

# Function to show cost breakdown
show_cost_breakdown() {
    print_status "Cost breakdown by service:"
    get_service_costs

    echo ""
    print_status "Resource usage:"
    get_resource_usage
}

# Main function
main() {
    echo "=========================================="
    echo "GambleGlee AWS Cost Monitoring"
    echo "=========================================="
    echo ""

    # Check prerequisites
    check_prerequisites

    # Show current costs
    show_cost_breakdown

    # Estimate monthly costs
    estimate_monthly_costs

    # Show optimization tips
    show_optimization_tips

    echo ""
    read -p "Do you want to set up billing alerts? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        setup_billing_alerts
    fi

    print_success "Cost monitoring completed!"
}

# Run main function
main "$@"
