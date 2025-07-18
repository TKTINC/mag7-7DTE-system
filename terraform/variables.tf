# Mag7-7DTE-System Terraform Variables

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (development, staging, production)"
  type        = string
  default     = "development"
  
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be development, staging, or production."
  }
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "mag7-7dte"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.1.0.0/16"  # Different from Smart-0DTE to avoid conflicts
}

variable "admin_cidr" {
  description = "CIDR block for admin access"
  type        = string
  default     = "0.0.0.0/0"
}

# EC2 Configuration
variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.xlarge"  # Larger for Mag7 processing requirements
}

variable "key_pair_name" {
  description = "AWS Key Pair name for EC2 access"
  type        = string
  default     = ""
}

variable "min_instances" {
  description = "Minimum number of instances in ASG"
  type        = number
  default     = 1
}

variable "max_instances" {
  description = "Maximum number of instances in ASG"
  type        = number
  default     = 5  # Higher for Mag7 scaling
}

variable "desired_instances" {
  description = "Desired number of instances in ASG"
  type        = number
  default     = 2
}

# Database Configuration
variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.small"  # Larger for fundamental data
}

variable "db_username" {
  description = "Database username"
  type        = string
  default     = "postgres"
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

# Redis Configuration
variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t3.small"  # Larger for Mag7 caching
}

# InfluxDB Configuration
variable "influxdb_instance_type" {
  description = "InfluxDB EC2 instance type"
  type        = string
  default     = "t3.medium"
}

variable "influxdb_admin_password" {
  description = "InfluxDB admin password"
  type        = string
  sensitive   = true
  default     = "admin123"
}

# API Keys
variable "polygon_api_key" {
  description = "Polygon.io API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "alpha_vantage_api_key" {
  description = "Alpha Vantage API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "openai_api_key" {
  description = "OpenAI API key"
  type        = string
  sensitive   = true
  default     = ""
}

# IBKR Configuration
variable "ibkr_host" {
  description = "IBKR TWS/Gateway host"
  type        = string
  default     = "127.0.0.1"
}

variable "ibkr_port" {
  description = "IBKR TWS/Gateway port"
  type        = number
  default     = 7497
}

variable "ibkr_client_id" {
  description = "IBKR client ID"
  type        = number
  default     = 2
}

# Mag7 Specific Configuration
variable "mag7_symbols" {
  description = "Magnificent 7 stock symbols"
  type        = string
  default     = "AAPL,MSFT,GOOGL,AMZN,NVDA,TSLA,META"
}

variable "dte_target" {
  description = "Days to expiration target"
  type        = number
  default     = 7
}

