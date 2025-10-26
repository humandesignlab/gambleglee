# AWS IVS (Interactive Video Service) for live streaming
# Note: IVS is not part of Free Tier, but we'll set it up for future use

# IVS Channel for live streaming
resource "aws_ivs_channel" "main" {
  name        = "${local.name_prefix}-streaming"
  authorized  = false
  latency_mode = "LOW"
  type        = "STANDARD"

  tags = local.common_tags
}

# IVS Stream Key
resource "aws_ivs_stream_key" "main" {
  channel_arn = aws_ivs_channel.main.arn

  tags = local.common_tags
}

# CloudFront Distribution for IVS
resource "aws_cloudfront_distribution" "ivs" {
  origin {
    domain_name = aws_ivs_channel.main.ingest_endpoint
    origin_id   = "IVS-${aws_ivs_channel.main.id}"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  enabled = true

  default_cache_behavior {
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "IVS-${aws_ivs_channel.main.id}"
    compress               = true
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 3600
    max_ttl     = 86400
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = local.common_tags
}

# Outputs
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

output "cloudfront_ivs_domain" {
  description = "CloudFront distribution domain for IVS"
  value       = aws_cloudfront_distribution.ivs.domain_name
}
