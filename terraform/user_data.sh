#!/bin/bash
# GambleGlee AWS EC2 User Data Script

# Update system
yum update -y

# Install Docker
yum install -y docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install Git
yum install -y git

# Install Node.js
curl -fsSL https://rpm.nodesource.com/setup_18.x | bash -
yum install -y nodejs

# Install Python 3.11
yum install -y python3 python3-pip

# Create application directory
mkdir -p /opt/gambleglee
cd /opt/gambleglee

# Clone repository (replace with your repository URL)
# git clone https://github.com/yourusername/gambleglee.git .

# Create environment files
cat > .env << EOF
# Database
DATABASE_URL=postgresql://postgres:your-secure-password-here@${rds_endpoint}:5432/gambleglee
REDIS_URL=redis://${elasticache_endpoint}:6379

# Environment
ENVIRONMENT=staging
DEBUG=false
LOG_LEVEL=INFO

# Security
SECRET_KEY=your-production-secret-key-here
JWT_SECRET_KEY=your-production-jwt-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
CORS_ORIGINS=["https://yourdomain.com"]

# Email
SMTP_HOST=your-smtp-host
SMTP_PORT=587
SMTP_USERNAME=your-smtp-username
SMTP_PASSWORD=your-smtp-password
SMTP_TLS=true

# Storage
S3_ENDPOINT_URL=https://s3.${aws_region}.amazonaws.com
S3_ACCESS_KEY_ID=your-s3-access-key
S3_SECRET_ACCESS_KEY=your-s3-secret-key
S3_BUCKET_NAME=${s3_bucket_name}

# Monitoring
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
EOF

# Create systemd service for the application
cat > /etc/systemd/system/gambleglee.service << EOF
[Unit]
Description=GambleGlee Application
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/gambleglee
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
User=ec2-user
Group=ec2-user

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
systemctl daemon-reload
systemctl enable gambleglee.service

# Install CloudWatch agent
yum install -y amazon-cloudwatch-agent

# Create CloudWatch agent configuration
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << EOF
{
    "logs": {
        "logs_collected": {
            "files": {
                "collect_list": [
                    {
                        "file_path": "/var/log/messages",
                        "log_group_name": "/aws/ec2/gambleglee-staging",
                        "log_stream_name": "{instance_id}/messages"
                    }
                ]
            }
        }
    },
    "metrics": {
        "namespace": "GambleGlee/Staging",
        "metrics_collected": {
            "cpu": {
                "measurement": [
                    "cpu_usage_idle",
                    "cpu_usage_iowait",
                    "cpu_usage_user",
                    "cpu_usage_system"
                ],
                "metrics_collection_interval": 60
            },
            "disk": {
                "measurement": [
                    "used_percent"
                ],
                "metrics_collection_interval": 60,
                "resources": [
                    "*"
                ]
            },
            "diskio": {
                "measurement": [
                    "io_time"
                ],
                "metrics_collection_interval": 60,
                "resources": [
                    "*"
                ]
            },
            "mem": {
                "measurement": [
                    "mem_used_percent"
                ],
                "metrics_collection_interval": 60
            }
        }
    }
}
EOF

# Start CloudWatch agent
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config \
    -m ec2 \
    -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json \
    -s

# Create log rotation configuration
cat > /etc/logrotate.d/gambleglee << EOF
/opt/gambleglee/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    notifempty
    create 644 ec2-user ec2-user
}
EOF

# Set up firewall
systemctl start firewalld
systemctl enable firewalld
firewall-cmd --permanent --add-port=80/tcp
firewall-cmd --permanent --add-port=443/tcp
firewall-cmd --permanent --add-port=8000/tcp
firewall-cmd --reload

# Create startup script
cat > /opt/gambleglee/start.sh << 'EOF'
#!/bin/bash
cd /opt/gambleglee

# Wait for database to be ready
echo "Waiting for database to be ready..."
while ! nc -z ${rds_endpoint} 5432; do
  sleep 1
done

# Wait for Redis to be ready
echo "Waiting for Redis to be ready..."
while ! nc -z ${elasticache_endpoint} 6379; do
  sleep 1
done

# Start the application
echo "Starting GambleGlee application..."
docker-compose up -d
EOF

chmod +x /opt/gambleglee/start.sh

# Install netcat for health checks
yum install -y nc

# Create health check script
cat > /opt/gambleglee/healthcheck.sh << 'EOF'
#!/bin/bash
# Health check script for GambleGlee

# Check if Docker is running
if ! systemctl is-active --quiet docker; then
    echo "Docker is not running"
    exit 1
fi

# Check if application is running
if ! docker-compose ps | grep -q "Up"; then
    echo "Application is not running"
    exit 1
fi

# Check if API is responding
if ! curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "API is not responding"
    exit 1
fi

echo "All services are healthy"
exit 0
EOF

chmod +x /opt/gambleglee/healthcheck.sh

# Create cron job for health checks
echo "*/5 * * * * /opt/gambleglee/healthcheck.sh >> /var/log/gambleglee-health.log 2>&1" | crontab -u ec2-user -

# Set up log monitoring
cat > /opt/gambleglee/log-monitor.sh << 'EOF'
#!/bin/bash
# Log monitoring script

LOG_FILE="/var/log/gambleglee-health.log"
ERROR_THRESHOLD=3

# Count errors in the last 5 minutes
ERROR_COUNT=$(tail -n 20 "$LOG_FILE" | grep -c "not running\|not responding" || true)

if [ "$ERROR_COUNT" -ge "$ERROR_THRESHOLD" ]; then
    echo "ALERT: GambleGlee health check failed $ERROR_COUNT times in the last 5 minutes"
    # Here you could send an alert to SNS, email, etc.
fi
EOF

chmod +x /opt/gambleglee/log-monitor.sh

# Add log monitoring to cron
echo "*/5 * * * * /opt/gambleglee/log-monitor.sh" | crontab -u ec2-user -

# Create backup script
cat > /opt/gambleglee/backup.sh << 'EOF'
#!/bin/bash
# Backup script for GambleGlee

BACKUP_DIR="/opt/gambleglee/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Backup database
pg_dump -h ${rds_endpoint} -U postgres -d gambleglee > "$BACKUP_DIR/db_backup_$DATE.sql"

# Backup application files
tar -czf "$BACKUP_DIR/app_backup_$DATE.tar.gz" /opt/gambleglee --exclude=backups

# Keep only last 7 days of backups
find "$BACKUP_DIR" -type f -mtime +7 -delete
EOF

chmod +x /opt/gambleglee/backup.sh

# Add backup to cron (daily at 2 AM)
echo "0 2 * * * /opt/gambleglee/backup.sh" | crontab -u ec2-user -

# Final setup
echo "GambleGlee setup completed successfully!" > /var/log/gambleglee-setup.log
