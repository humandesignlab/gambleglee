#!/bin/bash
# GambleGlee AWS Free Tier Staging Environment Setup Script

set -e

echo "🚀 Setting up GambleGlee AWS Free Tier staging environment..."

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

# Check if AWS CLI is installed
check_aws_cli() {
    print_status "Checking AWS CLI installation..."
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed. Please install AWS CLI first."
        echo "Visit: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    print_success "AWS CLI is installed and configured"
}

# Check if Terraform is installed
check_terraform() {
    print_status "Checking Terraform installation..."
    if ! command -v terraform &> /dev/null; then
        print_error "Terraform is not installed. Please install Terraform first."
        echo "Visit: https://learn.hashicorp.com/tutorials/terraform/install-cli"
        exit 1
    fi
    
    print_success "Terraform is installed"
}

# Check if SSH key exists
check_ssh_key() {
    print_status "Checking SSH key..."
    if [ ! -f ~/.ssh/id_rsa.pub ]; then
        print_warning "SSH key not found. Generating new SSH key..."
        ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ""
        print_success "SSH key generated"
    else
        print_success "SSH key found"
    fi
}

# Create Terraform variables file
create_terraform_vars() {
    print_status "Creating Terraform variables file..."
    
    if [ ! -f terraform/terraform.tfvars ]; then
        cat > terraform/terraform.tfvars << EOF
# AWS Configuration
aws_region = "us-east-1"

# Environment Configuration
environment = "staging"
project_name = "gambleglee"

# Database Configuration
db_password = "your-secure-password-here"

# Application Configuration
app_secret_key = "your-app-secret-key-here"
jwt_secret_key = "your-jwt-secret-key-here"
EOF
        print_success "Terraform variables file created"
    else
        print_warning "Terraform variables file already exists"
    fi
}

# Initialize Terraform
init_terraform() {
    print_status "Initializing Terraform..."
    cd terraform
    terraform init
    cd ..
    print_success "Terraform initialized"
}

# Plan Terraform deployment
plan_terraform() {
    print_status "Planning Terraform deployment..."
    cd terraform
    terraform plan -out=tfplan
    cd ..
    print_success "Terraform plan created"
}

# Deploy infrastructure
deploy_infrastructure() {
    print_status "Deploying infrastructure to AWS..."
    cd terraform
    terraform apply tfplan
    cd ..
    print_success "Infrastructure deployed"
}

# Get deployment outputs
get_outputs() {
    print_status "Getting deployment outputs..."
    cd terraform
    terraform output -json > ../staging-outputs.json
    cd ..
    print_success "Deployment outputs saved"
}

# Create deployment summary
create_summary() {
    print_status "Creating deployment summary..."
    
    # Read outputs
    EC2_IP=$(jq -r '.ec2_public_ip.value' staging-outputs.json)
    RDS_ENDPOINT=$(jq -r '.rds_endpoint.value' staging-outputs.json)
    ELASTICACHE_ENDPOINT=$(jq -r '.elasticache_endpoint.value' staging-outputs.json)
    S3_BUCKET=$(jq -r '.s3_bucket_name.value' staging-outputs.json)
    
    cat > staging-deployment-summary.md << EOF
# GambleGlee Staging Environment Deployment Summary

## 🎉 Deployment Successful!

Your GambleGlee staging environment has been deployed to AWS Free Tier.

## 📊 Infrastructure Details

### **EC2 Instance**
- **Public IP**: $EC2_IP
- **Instance Type**: t2.micro (Free Tier)
- **SSH Access**: \`ssh -i ~/.ssh/id_rsa ec2-user@$EC2_IP\`

### **Database (RDS)**
- **Endpoint**: $RDS_ENDPOINT
- **Engine**: PostgreSQL 15.4
- **Instance Type**: db.t3.micro (Free Tier)
- **Storage**: 20 GB

### **Cache (ElastiCache)**
- **Endpoint**: $ELASTICACHE_ENDPOINT
- **Engine**: Redis 7
- **Instance Type**: cache.t3.micro (Free Tier)

### **Storage (S3)**
- **Bucket Name**: $S3_BUCKET
- **Region**: us-east-1
- **Storage Class**: Standard

## 🔧 Access Information

### **Application URLs**
- **Frontend**: http://$EC2_IP:3000
- **Backend API**: http://$EC2_IP:8000
- **API Documentation**: http://$EC2_IP:8000/docs

### **Monitoring**
- **CloudWatch Logs**: /aws/ec2/gambleglee-staging
- **CloudWatch Metrics**: GambleGlee/Staging namespace

## 🚀 Next Steps

### **1. Deploy Application**
\`\`\`bash
# SSH into the instance
ssh -i ~/.ssh/id_rsa ec2-user@$EC2_IP

# Clone your repository
git clone https://github.com/yourusername/gambleglee.git /opt/gambleglee
cd /opt/gambleglee

# Update environment variables
nano .env

# Start the application
docker-compose up -d
\`\`\`

### **2. Configure Domain (Optional)**
- Point your domain to $EC2_IP
- Update CORS settings in the application
- Configure SSL certificate

### **3. Monitor Application**
- Check CloudWatch logs: /aws/ec2/gambleglee-staging
- Monitor metrics in CloudWatch console
- Set up alarms for critical metrics

## 💰 Cost Information

### **Free Tier Usage**
- **EC2**: 750 hours/month (t2.micro)
- **RDS**: 750 hours/month (db.t3.micro)
- **ElastiCache**: 750 hours/month (cache.t3.micro)
- **S3**: 5 GB storage
- **Data Transfer**: 1 GB/month

### **Estimated Monthly Cost**
- **Free Tier**: $0 (for 12 months)
- **After Free Tier**: ~$50-100/month

## 🛠️ Management Commands

### **Start Application**
\`\`\`bash
ssh -i ~/.ssh/id_rsa ec2-user@$EC2_IP
cd /opt/gambleglee
docker-compose up -d
\`\`\`

### **Stop Application**
\`\`\`bash
ssh -i ~/.ssh/id_rsa ec2-user@$EC2_IP
cd /opt/gambleglee
docker-compose down
\`\`\`

### **View Logs**
\`\`\`bash
ssh -i ~/.ssh/id_rsa ec2-user@$EC2_IP
cd /opt/gambleglee
docker-compose logs -f
\`\`\`

### **Update Application**
\`\`\`bash
ssh -i ~/.ssh/id_rsa ec2-user@$EC2_IP
cd /opt/gambleglee
git pull
docker-compose down
docker-compose up -d --build
\`\`\`

## 🗑️ Cleanup

To destroy the infrastructure:
\`\`\`bash
cd terraform
terraform destroy
\`\`\`

## 📞 Support

If you encounter any issues:
1. Check CloudWatch logs
2. Verify security group rules
3. Ensure all services are running
4. Check application logs

---

**Deployment completed successfully!** 🎉
EOF

    print_success "Deployment summary created"
}

# Main execution
main() {
    print_status "Starting GambleGlee AWS Free Tier staging environment setup..."
    
    check_aws_cli
    check_terraform
    check_ssh_key
    create_terraform_vars
    init_terraform
    plan_terraform
    
    print_warning "This will deploy infrastructure to AWS. Continue? (y/N)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        deploy_infrastructure
        get_outputs
        create_summary
        print_success "🎉 Staging environment deployed successfully!"
        echo ""
        echo "📋 Next steps:"
        echo "  1. Review staging-deployment-summary.md"
        echo "  2. SSH into your instance: ssh -i ~/.ssh/id_rsa ec2-user@<EC2_IP>"
        echo "  3. Deploy your application code"
        echo "  4. Access your application at http://<EC2_IP>:8000"
        echo ""
    else
        print_warning "Deployment cancelled"
    fi
}

# Run main function
main "$@"
