# GambleGlee AWS Infrastructure Overview

This document provides a comprehensive overview of the GambleGlee AWS infrastructure, including architecture, components, costs, and management procedures.

## 🏗️ Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Internet Gateway                         │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────────┐
│                    Application Load Balancer                    │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────────┐
│                    Public Subnet (us-east-1a)                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   EC2 Instance  │  │   NAT Gateway   │  │   Elastic IP    │ │
│  │   (t3.micro)    │  │                 │  │                 │ │
│  │                 │  │                 │  │                 │ │
│  │  ┌───────────┐  │  │                 │  │                 │ │
│  │  │  Docker   │  │  │                 │  │                 │ │
│  │  │ Containers│  │  │                 │  │                 │ │
│  │  │           │  │  │                 │  │                 │ │
│  │  │ - Backend │  │  │                 │  │                 │ │
│  │  │ - Frontend│  │  │                 │  │                 │ │
│  │  │ - Nginx   │  │  │                 │  │                 │ │
│  │  └───────────┘  │  │                 │  │                 │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────────┐
│                   Private Subnet (us-east-1a)                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   RDS Instance  │  │ ElastiCache     │  │   S3 Buckets    │ │
│  │   (db.t3.micro) │  │ (cache.t3.micro)│  │                 │ │
│  │                 │  │                 │  │ - Main Storage  │ │
│  │  PostgreSQL 15  │  │     Redis 7     │  │ - Static Assets │ │
│  │                 │  │                 │  │ - User Uploads  │ │
│  │ - Encrypted     │  │ - Single Node   │  │                 │ │
│  │ - Backups       │  │ - LRU Eviction  │  │ - Lifecycle     │ │
│  │ - Monitoring    │  │ - Logging       │  │ - Encryption    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────────┐
│                   Private Subnet (us-east-1b)                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   RDS Replica   │  │ ElastiCache     │  │   S3 Buckets    │ │
│  │   (Optional)    │  │ (Optional)      │  │   (Replicated)  │ │
│  │                 │  │                 │  │                 │ │
│  │ - Read Replica  │  │ - Multi-AZ      │  │ - Cross-Region  │ │
│  │ - Failover      │  │ - Failover      │  │ - Backup        │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 📊 Component Details

### 1. Compute Layer

#### EC2 Instance

- **Type**: t3.micro (Free Tier eligible)
- **OS**: Amazon Linux 2
- **Storage**: 8GB EBS GP2 (encrypted)
- **Purpose**: Application hosting, Docker containers
- **Monitoring**: CloudWatch, Enhanced Monitoring

#### Docker Containers

- **Backend**: FastAPI application
- **Frontend**: React application
- **Nginx**: Reverse proxy and load balancer
- **Redis**: Local caching (if needed)

### 2. Database Layer

#### RDS PostgreSQL

- **Engine**: PostgreSQL 15.4
- **Instance**: db.t3.micro (Free Tier eligible)
- **Storage**: 20GB GP2 (encrypted)
- **Backups**: 7-day retention
- **Monitoring**: Performance Insights, Enhanced Monitoring

#### ElastiCache Redis

- **Engine**: Redis 7.x
- **Node Type**: cache.t3.micro (Free Tier eligible)
- **Configuration**: Single node, LRU eviction
- **Purpose**: Session storage, caching, real-time data

### 3. Storage Layer

#### S3 Buckets

- **Main Bucket**: Application data, logs
- **Static Bucket**: Frontend assets, CDN
- **Uploads Bucket**: User-generated content
- **Features**: Encryption, lifecycle policies, versioning

### 4. Networking Layer

#### VPC Configuration

- **CIDR**: 10.0.0.0/16
- **Public Subnets**: 10.0.1.0/24, 10.0.2.0/24
- **Private Subnets**: 10.0.10.0/24, 10.0.11.0/24
- **NAT Gateway**: Single gateway for cost optimization

#### Security Groups

- **ALB**: HTTP/HTTPS from internet
- **EC2**: HTTP from ALB, SSH from internet
- **RDS**: PostgreSQL from EC2
- **ElastiCache**: Redis from EC2

### 5. Monitoring Layer

#### CloudWatch

- **Metrics**: EC2, RDS, ElastiCache, S3
- **Logs**: Application, system, database
- **Alarms**: CPU, memory, disk, connections
- **Dashboard**: Real-time monitoring

#### Logging

- **Application Logs**: Structured logging with context
- **Access Logs**: Nginx access and error logs
- **System Logs**: OS and Docker logs
- **Database Logs**: PostgreSQL query logs

## 💰 Cost Analysis

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

### Cost Optimization Strategies

1. **Use Free Tier resources** for development and testing
2. **Implement S3 lifecycle policies** for cost reduction
3. **Monitor usage** with CloudWatch and billing alerts
4. **Use Spot Instances** for non-critical workloads
5. **Implement auto-scaling** for variable workloads

## 🔒 Security Features

### Network Security

- **VPC isolation** with private subnets
- **Security groups** with minimal access
- **NAT Gateway** for private subnet internet access
- **No direct database access** from internet

### Data Security

- **Encryption at rest** for all storage
- **Encryption in transit** for all communications
- **Secure parameter storage** with AWS Secrets Manager
- **IAM roles** with least privilege access

### Application Security

- **Security headers** in Nginx configuration
- **Rate limiting** and DDoS protection
- **Input validation** and sanitization
- **Audit logging** for all operations

## 📈 Scalability

### Horizontal Scaling

- **Auto Scaling Groups** for EC2 instances
- **RDS Read Replicas** for database scaling
- **ElastiCache Clusters** for cache scaling
- **S3 with CloudFront** for content delivery

### Vertical Scaling

- **Instance type upgrades** (t3.small, t3.medium)
- **Storage scaling** for RDS and EBS
- **Memory optimization** for Redis
- **CPU optimization** for application

### Performance Optimization

- **Redis caching** for frequently accessed data
- **S3 with CloudFront** for static content
- **Database indexing** and query optimization
- **Connection pooling** for database connections

## 🛠️ Management Tools

### Deployment Scripts

- **deploy.sh**: Automated infrastructure deployment
- **cleanup.sh**: Infrastructure destruction
- **health_check.sh**: Infrastructure health monitoring
- **backup.sh**: Data backup and snapshot creation
- **restore.sh**: Data restoration from backups

### Monitoring Scripts

- **monitor_costs.sh**: Cost monitoring and optimization
- **health_check.sh**: Component health verification
- **backup.sh**: Automated backup creation

### Terraform Configuration

- **Modular structure** for easy maintenance
- **Variable configuration** for different environments
- **State management** with remote backend
- **Output values** for integration

## 🔄 Backup and Recovery

### Backup Strategy

- **RDS automated backups** with 7-day retention
- **Manual snapshots** for point-in-time recovery
- **S3 versioning** for object-level recovery
- **Terraform state** backup for infrastructure

### Recovery Procedures

- **RDS restore** from snapshots
- **S3 restore** from versions
- **Infrastructure restore** from Terraform state
- **Application restore** from code backups

### Disaster Recovery

- **Multi-AZ deployment** for high availability
- **Cross-region replication** for S3 buckets
- **Automated failover** for RDS and ElastiCache
- **Backup verification** and testing

## 📋 Maintenance Procedures

### Regular Maintenance

- **Security updates** for EC2 instances
- **Database maintenance** windows
- **Log rotation** and cleanup
- **Cost optimization** reviews

### Monitoring and Alerting

- **CloudWatch alarms** for critical metrics
- **SNS notifications** for alerts
- **Cost monitoring** and optimization
- **Performance monitoring** and tuning

### Troubleshooting

- **Log analysis** with CloudWatch Logs
- **Performance profiling** with CloudWatch Insights
- **Database query analysis** with Performance Insights
- **Network troubleshooting** with VPC Flow Logs

## 🚀 Deployment Process

### Initial Deployment

1. **Prerequisites check** (AWS CLI, Terraform)
2. **Infrastructure deployment** with Terraform
3. **Application deployment** with Docker
4. **Configuration setup** and testing
5. **Monitoring setup** and verification

### Updates and Changes

1. **Code changes** in Git repository
2. **Infrastructure changes** in Terraform
3. **Testing** in staging environment
4. **Deployment** to production
5. **Verification** and monitoring

### Rollback Procedures

1. **Identify** the issue and impact
2. **Stop** the deployment process
3. **Restore** from previous backup
4. **Verify** the restoration
5. **Monitor** for stability

## 📚 Documentation

### Infrastructure Documentation

- **README.md**: Quick start guide
- **INFRASTRUCTURE_OVERVIEW.md**: This document
- **Terraform documentation**: Inline code comments
- **Deployment guides**: Step-by-step procedures

### API Documentation

- **OpenAPI/Swagger**: Backend API documentation
- **Frontend documentation**: Component and usage guides
- **Integration guides**: Third-party service integration

### Troubleshooting Guides

- **Common issues**: Known problems and solutions
- **Debug procedures**: Step-by-step debugging
- **Performance tuning**: Optimization guidelines
- **Security procedures**: Security best practices

## 🤝 Support and Maintenance

### Support Channels

- **Documentation**: Comprehensive guides and references
- **Monitoring**: Real-time alerts and notifications
- **Logs**: Detailed logging for troubleshooting
- **Community**: Open source community support

### Maintenance Schedule

- **Daily**: Health checks and monitoring
- **Weekly**: Cost reviews and optimization
- **Monthly**: Security updates and patches
- **Quarterly**: Architecture reviews and improvements

### Escalation Procedures

1. **Level 1**: Automated monitoring and alerts
2. **Level 2**: Manual investigation and resolution
3. **Level 3**: Expert consultation and support
4. **Level 4**: Vendor support and escalation

This infrastructure provides a solid foundation for GambleGlee's social betting platform, with room for growth and optimization as the business scales.
