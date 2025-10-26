# Outputs for the infrastructure
# All important connection details and endpoints

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "vpc_cidr_block" {
  description = "VPC CIDR block"
  value       = aws_vpc.main.cidr_block
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = aws_subnet.private[*].id
}

# Database outputs
output "database_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.main.endpoint
}

output "database_port" {
  description = "RDS instance port"
  value       = aws_db_instance.main.port
}

output "database_name" {
  description = "RDS database name"
  value       = aws_db_instance.main.db_name
}

output "database_username" {
  description = "RDS master username"
  value       = aws_db_instance.main.username
  sensitive   = true
}

output "database_password_secret_arn" {
  description = "ARN of the secret containing the RDS password"
  value       = aws_secretsmanager_secret.db_password.arn
}

# Redis outputs
output "redis_endpoint" {
  description = "Redis primary endpoint"
  value       = aws_elasticache_replication_group.main.primary_endpoint_address
}

output "redis_port" {
  description = "Redis port"
  value       = aws_elasticache_replication_group.main.port
}

# S3 outputs
output "s3_main_bucket" {
  description = "Main S3 bucket name"
  value       = aws_s3_bucket.main.bucket
}

output "s3_static_bucket" {
  description = "Static assets S3 bucket name"
  value       = aws_s3_bucket.static.bucket
}

output "s3_uploads_bucket" {
  description = "User uploads S3 bucket name"
  value       = aws_s3_bucket.uploads.bucket
}

# EC2 outputs
output "ec2_public_ip" {
  description = "EC2 instance public IP"
  value       = aws_eip.ec2.public_ip
}

output "ec2_public_dns" {
  description = "EC2 instance public DNS"
  value       = aws_instance.main.public_dns
}

output "ec2_instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.main.id
}

# IVS outputs
output "ivs_channel_arn" {
  description = "IVS Channel ARN"
  value       = aws_ivs_channel.main.arn
}

output "ivs_channel_playback_url" {
  description = "IVS Channel playback URL"
  value       = aws_ivs_channel.main.playback_url
}

output "ivs_channel_ingest_endpoint" {
  description = "IVS Channel ingest endpoint"
  value       = aws_ivs_channel.main.ingest_endpoint
}

output "ivs_stream_key_arn" {
  description = "IVS Stream Key ARN"
  value       = aws_ivs_stream_key.main.arn
}

output "ivs_stream_key_value" {
  description = "IVS Stream Key value"
  value       = aws_ivs_stream_key.main.value
  sensitive   = true
}

# CloudWatch outputs
output "cloudwatch_dashboard_url" {
  description = "CloudWatch Dashboard URL"
  value       = "https://${var.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.main.dashboard_name}"
}

# Connection strings for application configuration
output "database_url" {
  description = "Database connection URL"
  value       = "postgresql://${aws_db_instance.main.username}:${random_password.db_password.result}@${aws_db_instance.main.endpoint}:${aws_db_instance.main.port}/${aws_db_instance.main.db_name}"
  sensitive   = true
}

output "redis_url" {
  description = "Redis connection URL"
  value       = "redis://${aws_elasticache_replication_group.main.primary_endpoint_address}:${aws_elasticache_replication_group.main.port}"
}

# Environment variables for application
output "environment_variables" {
  description = "Environment variables for the application"
  value = {
    DATABASE_URL = "postgresql://${aws_db_instance.main.username}:${random_password.db_password.result}@${aws_db_instance.main.endpoint}:${aws_db_instance.main.port}/${aws_db_instance.main.db_name}"
    REDIS_URL    = "redis://${aws_elasticache_replication_group.main.primary_endpoint_address}:${aws_elasticache_replication_group.main.port}"
    S3_BUCKET    = aws_s3_bucket.main.bucket
    S3_STATIC_BUCKET = aws_s3_bucket.static.bucket
    S3_UPLOADS_BUCKET = aws_s3_bucket.uploads.bucket
    AWS_REGION   = var.aws_region
    IVS_CHANNEL_ARN = aws_ivs_channel.main.arn
    IVS_PLAYBACK_URL = aws_ivs_channel.main.playback_url
    IVS_INGEST_ENDPOINT = aws_ivs_channel.main.ingest_endpoint
  }
  sensitive = true
}
