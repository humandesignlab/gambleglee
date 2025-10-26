#!/bin/bash
# User data script for EC2 instance initialization
# This script sets up the GambleGlee application environment

set -e

# Update system
yum update -y

# Install required packages
yum install -y \
    docker \
    git \
    htop \
    nginx \
    postgresql15 \
    python3 \
    python3-pip \
    awscli \
    jq

# Start and enable Docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Start and enable Nginx
systemctl start nginx
systemctl enable nginx

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Create application directory
mkdir -p /opt/gambleglee
cd /opt/gambleglee

# Clone the repository (you'll need to update this with your actual repo)
# git clone https://github.com/yourusername/gambleglee.git .

# For now, create a basic structure
mkdir -p {backend,frontend,infrastructure}

# Create environment file
cat > /opt/gambleglee/.env << EOF
# Database Configuration
DATABASE_URL=postgresql://${db_username}:${db_password}@${db_endpoint}:5432/${db_name}
REDIS_URL=redis://${redis_endpoint}:6379

# AWS Configuration
AWS_REGION=${region}
S3_BUCKET=${s3_bucket}
S3_STATIC_BUCKET=${s3_static_bucket}
S3_UPLOADS_BUCKET=${s3_uploads_bucket}

# IVS Configuration
IVS_CHANNEL_ARN=${ivs_channel_arn}
IVS_PLAYBACK_URL=${ivs_playback_url}
IVS_INGEST_ENDPOINT=${ivs_ingest_endpoint}

# Application Configuration
ENVIRONMENT=staging
DEBUG=true
SECRET_KEY=your-secret-key-change-in-production
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production

# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=noreply@gambleglee.com
FROM_NAME=GambleGlee

# Stripe Configuration
STRIPE_PUBLISHABLE_KEY=pk_test_your_key
STRIPE_SECRET_KEY=sk_test_your_key
STRIPE_WEBHOOK_SECRET=whsec_your_secret

# MercadoPago Configuration
MERCADOPAGO_ACCESS_TOKEN=your_access_token
MERCADOPAGO_PUBLIC_KEY=your_public_key
MERCADOPAGO_WEBHOOK_SECRET=your_webhook_secret
EOF

# Create Docker Compose file
cat > /opt/gambleglee/docker-compose.yml << 'EOF'
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - AWS_REGION=${AWS_REGION}
      - S3_BUCKET=${S3_BUCKET}
      - S3_STATIC_BUCKET=${S3_STATIC_BUCKET}
      - S3_UPLOADS_BUCKET=${S3_UPLOADS_BUCKET}
      - IVS_CHANNEL_ARN=${IVS_CHANNEL_ARN}
      - IVS_PLAYBACK_URL=${IVS_PLAYBACK_URL}
      - IVS_INGEST_ENDPOINT=${IVS_INGEST_ENDPOINT}
      - ENVIRONMENT=${ENVIRONMENT}
      - DEBUG=${DEBUG}
      - SECRET_KEY=${SECRET_KEY}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - SMTP_HOST=${SMTP_HOST}
      - SMTP_PORT=${SMTP_PORT}
      - SMTP_USERNAME=${SMTP_USERNAME}
      - SMTP_PASSWORD=${SMTP_PASSWORD}
      - FROM_EMAIL=${FROM_EMAIL}
      - FROM_NAME=${FROM_NAME}
      - STRIPE_PUBLISHABLE_KEY=${STRIPE_PUBLISHABLE_KEY}
      - STRIPE_SECRET_KEY=${STRIPE_SECRET_KEY}
      - STRIPE_WEBHOOK_SECRET=${STRIPE_WEBHOOK_SECRET}
      - MERCADOPAGO_ACCESS_TOKEN=${MERCADOPAGO_ACCESS_TOKEN}
      - MERCADOPAGO_PUBLIC_KEY=${MERCADOPAGO_PUBLIC_KEY}
      - MERCADOPAGO_WEBHOOK_SECRET=${MERCADOPAGO_WEBHOOK_SECRET}
    volumes:
      - ./backend:/app
      - /var/run/docker.sock:/var/run/docker.sock
    depends_on:
      - redis
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_API_URL=http://localhost:8000
      - REACT_APP_WS_URL=ws://localhost:8000
    volumes:
      - ./frontend:/app
      - /app/node_modules
    depends_on:
      - backend
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - backend
      - frontend
    restart: unless-stopped

volumes:
  redis_data:
EOF

# Create Nginx configuration
cat > /opt/gambleglee/nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    upstream backend {
        server backend:8000;
    }

    upstream frontend {
        server frontend:3000;
    }

    server {
        listen 80;
        server_name _;

        # Security headers
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

        # API routes
        location /api/ {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # WebSocket support
        location /ws/ {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Frontend routes
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
EOF

# Create systemd service for the application
cat > /etc/systemd/system/gambleglee.service << 'EOF'
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
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
systemctl daemon-reload
systemctl enable gambleglee.service

# Create log rotation configuration
cat > /etc/logrotate.d/gambleglee << 'EOF'
/opt/gambleglee/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 ec2-user ec2-user
}
EOF

# Set up CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
rpm -U ./amazon-cloudwatch-agent.rpm

# Create CloudWatch agent configuration
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'EOF'
{
    "logs": {
        "logs_collected": {
            "files": {
                "collect_list": [
                    {
                        "file_path": "/opt/gambleglee/logs/*.log",
                        "log_group_name": "/aws/ec2/gambleglee-staging",
                        "log_stream_name": "{instance_id}/application.log"
                    },
                    {
                        "file_path": "/var/log/nginx/access.log",
                        "log_group_name": "/aws/ec2/gambleglee-staging",
                        "log_stream_name": "{instance_id}/nginx-access.log"
                    },
                    {
                        "file_path": "/var/log/nginx/error.log",
                        "log_group_name": "/aws/ec2/gambleglee-staging",
                        "log_stream_name": "{instance_id}/nginx-error.log"
                    }
                ]
            }
        }
    },
    "metrics": {
        "namespace": "GambleGlee/EC2",
        "metrics_collected": {
            "cpu": {
                "measurement": ["cpu_usage_idle", "cpu_usage_iowait", "cpu_usage_user", "cpu_usage_system"],
                "metrics_collection_interval": 60
            },
            "disk": {
                "measurement": ["used_percent"],
                "metrics_collection_interval": 60,
                "resources": ["*"]
            },
            "diskio": {
                "measurement": ["io_time"],
                "metrics_collection_interval": 60,
                "resources": ["*"]
            },
            "mem": {
                "measurement": ["mem_used_percent"],
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

# Create application logs directory
mkdir -p /opt/gambleglee/logs
chown ec2-user:ec2-user /opt/gambleglee/logs

# Set proper permissions
chown -R ec2-user:ec2-user /opt/gambleglee

# Create a simple health check script
cat > /opt/gambleglee/health_check.sh << 'EOF'
#!/bin/bash
# Health check script for the application

# Check if Docker is running
if ! systemctl is-active --quiet docker; then
    echo "Docker is not running"
    exit 1
fi

# Check if the application containers are running
if ! docker-compose ps | grep -q "Up"; then
    echo "Application containers are not running"
    exit 1
fi

# Check if the application is responding
if ! curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "Application is not responding"
    exit 1
fi

echo "Application is healthy"
exit 0
EOF

chmod +x /opt/gambleglee/health_check.sh

# Create a cron job for health checks
echo "*/5 * * * * /opt/gambleglee/health_check.sh >> /opt/gambleglee/logs/health_check.log 2>&1" | crontab -u ec2-user -

# Log the completion
echo "User data script completed at $(date)" >> /var/log/user-data.log
