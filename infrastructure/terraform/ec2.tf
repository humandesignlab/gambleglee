# EC2 Instance for application hosting
# Using Free Tier eligible instance

# Key Pair for SSH access
resource "aws_key_pair" "main" {
  key_name   = "${local.name_prefix}-key"
  public_key = file("~/.ssh/id_rsa.pub") # Assumes you have SSH key

  tags = local.common_tags
}

# IAM Role for EC2 instance
resource "aws_iam_role" "ec2" {
  name = "${local.name_prefix}-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

# IAM Policy for EC2 instance
resource "aws_iam_policy" "ec2" {
  name = "${local.name_prefix}-ec2-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.main.arn,
          "${aws_s3_bucket.main.arn}/*",
          aws_s3_bucket.static.arn,
          "${aws_s3_bucket.static.arn}/*",
          aws_s3_bucket.uploads.arn,
          "${aws_s3_bucket.uploads.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.db_password.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })

  tags = local.common_tags
}

# Attach policy to role
resource "aws_iam_role_policy_attachment" "ec2" {
  role       = aws_iam_role.ec2.name
  policy_arn = aws_iam_policy.ec2.arn
}

# Attach AWS managed policies
resource "aws_iam_role_policy_attachment" "ec2_ssm" {
  role       = aws_iam_role.ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Instance Profile
resource "aws_iam_instance_profile" "ec2" {
  name = "${local.name_prefix}-ec2-profile"
  role = aws_iam_role.ec2.name

  tags = local.common_tags
}

# User data script for EC2 initialization
locals {
  user_data = base64encode(templatefile("${path.module}/user_data.sh", {
    db_endpoint = aws_db_instance.main.endpoint
    db_name     = aws_db_instance.main.db_name
    redis_endpoint = aws_elasticache_replication_group.main.primary_endpoint_address
    s3_bucket   = aws_s3_bucket.main.bucket
    s3_static_bucket = aws_s3_bucket.static.bucket
    s3_uploads_bucket = aws_s3_bucket.uploads.bucket
    region      = var.aws_region
  }))
}

# EC2 Instance
resource "aws_instance" "main" {
  ami           = "ami-0c02fb55956c7d316" # Amazon Linux 2 AMI (Free Tier eligible)
  instance_type = "t3.micro" # Free Tier eligible
  key_name      = aws_key_pair.main.key_name

  # Network
  subnet_id                   = aws_subnet.public[0].id
  vpc_security_group_ids      = [aws_security_group.ec2.id]
  associate_public_ip_address = true

  # Storage
  root_block_device {
    volume_type = "gp2"
    volume_size = 8 # Free Tier eligible
    encrypted   = true
  }

  # IAM
  iam_instance_profile = aws_iam_instance_profile.ec2.name

  # User data
  user_data = local.user_data

  # Monitoring
  monitoring = true

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-app-server"
  })
}

# Elastic IP for EC2 instance
resource "aws_eip" "ec2" {
  instance = aws_instance.main.id
  domain   = "vpc"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-ec2-eip"
  })
}

# CloudWatch Log Group for application logs
resource "aws_cloudwatch_log_group" "app" {
  name              = "/aws/ec2/${local.name_prefix}"
  retention_in_days = 7

  tags = local.common_tags
}

# Outputs
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
