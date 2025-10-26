# GambleGlee AWS Infrastructure

This directory contains the Terraform configuration for deploying GambleGlee's AWS infrastructure. The infrastructure is optimized for AWS Free Tier usage and includes all necessary components for a production-ready social betting platform.

## 🏗️ Architecture Overview

The infrastructure includes:

- **VPC**: Custom VPC with public and private subnets
- **EC2**: Application server running Docker containers
- **RDS**: PostgreSQL database with encryption and backups
- **ElastiCache**: Redis cluster for caching and sessions
- **S3**: Multiple buckets for file storage and static assets
- **IVS**: Interactive Video Service for live streaming
- **CloudWatch**: Monitoring, logging, and alerting
- **Security**: Comprehensive security groups and IAM roles

## 📋 Prerequisites

Before deploying, ensure you have:

1. **AWS CLI** installed and configured

   ```bash
   aws configure
   ```

2. **Terraform** installed (version 1.0+)

   ```bash
   # macOS
   brew install terraform

   # Linux
   wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
   unzip terraform_1.6.0_linux_amd64.zip
   sudo mv terraform /usr/local/bin/
   ```

3. **SSH Key Pair** (will be created automatically if not exists)

   ```bash
   ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ""
   ```

4. **AWS Account** with appropriate permissions

## 🚀 Quick Start

### 1. Deploy Infrastructure

```bash
# Make scripts executable
chmod +x deploy.sh cleanup.sh

# Deploy the infrastructure
./deploy.sh
```

The deployment script will:

- Check prerequisites
- Create SSH key if needed
- Check Free Tier usage
- Estimate costs
- Initialize Terraform
- Plan and apply the infrastructure

### 2. Access Your Application

After deployment, you'll get:

- **EC2 Public IP**: SSH access to the server
- **Application URL**: `http://<EC2_IP>`
- **CloudWatch Dashboard**: Monitoring and logs

### 3. SSH into the Server

```bash
ssh -i ~/.ssh/id_rsa ec2-user@<EC2_IP>
```

## 🏷️ Resource Naming

All resources follow the naming convention:

```
<project_name>-<environment>-<resource_type>
```

Example: `gambleglee-staging-postgres`

## 💰 Cost Optimization

### Free Tier Resources (0 cost for 12 months)

- **EC2 t3.micro**: 750 hours/month
- **RDS db.t3.micro**: 750 hours/month
- **ElastiCache cache.t3.micro**: 750 hours/month
- **S3**: 5GB storage, 20,000 GET requests
- **CloudFront**: 1TB data transfer out
- **Route53**: 1 hosted zone
- **CloudWatch**: 10 custom metrics, 1GB log ingestion

### Paid Resources (estimated monthly cost)

- **NAT Gateway**: ~$45/month
- **EIP**: ~$3.65/month
- **RDS Storage**: ~$2.30/month (20GB)
- **S3 Storage**: ~$0.50/month (additional)
- **CloudWatch Logs**: ~$0.50/month (additional)
- **IVS**: ~$0.50/hour (if used)

**Total estimated cost: ~$50-100/month (after Free Tier)**

## 🔧 Configuration

### Environment Variables

The infrastructure creates environment variables for:

- Database connection
- Redis connection
- S3 bucket names
- AWS region
- IVS configuration
- Stripe/MercadoPago keys

### Customization

Edit `variables.tf` to customize:

- AWS region
- Instance types
- Backup retention
- Log retention
- Tags

## 📊 Monitoring

### CloudWatch Dashboard

- EC2 metrics (CPU, memory, network)
- RDS metrics (CPU, connections, storage)
- ElastiCache metrics (CPU, connections, memory)
- Custom application metrics

### Alarms

- High CPU utilization
- High database connections
- High memory usage
- Disk space warnings

### Logs

- Application logs
- Nginx access/error logs
- System logs
- Database logs

## 🔒 Security

### Network Security

- VPC with public/private subnets
- Security groups with minimal access
- NAT Gateway for private subnet internet access
- No direct database access from internet

### Data Security

- Database encryption at rest
- S3 bucket encryption
- Secure parameter storage
- IAM roles with least privilege

### Application Security

- Security headers
- Rate limiting
- Input validation
- Audit logging

## 🗂️ File Structure

```
infrastructure/
├── terraform/
│   ├── main.tf              # Main configuration
│   ├── variables.tf         # Input variables
│   ├── outputs.tf          # Output values
│   ├── vpc.tf              # VPC configuration
│   ├── security.tf         # Security groups
│   ├── rds.tf              # Database configuration
│   ├── elasticache.tf      # Redis configuration
│   ├── s3.tf               # S3 buckets
│   ├── ec2.tf              # EC2 instance
│   ├── ivs.tf              # IVS streaming
│   ├── cloudwatch.tf       # Monitoring
│   └── user_data.sh        # EC2 initialization
├── deploy.sh               # Deployment script
├── cleanup.sh              # Cleanup script
└── README.md               # This file
```

## 🧹 Cleanup

To destroy the infrastructure:

```bash
./cleanup.sh
```

This will:

- Destroy all AWS resources
- Clean up local Terraform files
- Show cost savings
- Confirm before destruction

## 🔍 Troubleshooting

### Common Issues

1. **Terraform state lock**

   ```bash
   terraform force-unlock <lock_id>
   ```

2. **Permission denied errors**

   ```bash
   chmod +x deploy.sh cleanup.sh
   ```

3. **AWS credentials not found**

   ```bash
   aws configure
   ```

4. **SSH key not found**
   ```bash
   ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ""
   ```

### Logs

Check logs in:

- **Application**: `/opt/gambleglee/logs/`
- **System**: `/var/log/`
- **CloudWatch**: AWS Console → CloudWatch → Logs

### Health Checks

```bash
# Check application status
sudo systemctl status gambleglee

# Check Docker containers
docker-compose ps

# Check application health
/opt/gambleglee/health_check.sh
```

## 📚 Additional Resources

- [AWS Free Tier](https://aws.amazon.com/free/)
- [Terraform Documentation](https://terraform.io/docs/)
- [AWS CLI Documentation](https://docs.aws.amazon.com/cli/)
- [Docker Documentation](https://docs.docker.com/)

## 🤝 Support

For issues with the infrastructure:

1. Check the troubleshooting section
2. Review CloudWatch logs
3. Check AWS service status
4. Contact the development team

## 📄 License

This infrastructure configuration is part of the GambleGlee project and follows the same license terms.
