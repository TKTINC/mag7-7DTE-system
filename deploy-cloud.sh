#!/bin/bash

# Mag7-7DTE-System One-Click Cloud Deployment Script
# This script automates AWS infrastructure provisioning and deployment

set -e  # Exit on any error

echo "☁️  Starting Mag7-7DTE-System Cloud Deployment..."
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
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

print_mag7() {
    echo -e "${PURPLE}[MAG7]${NC} $1"
}

# Check prerequisites
print_status "Checking prerequisites..."

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI is not installed. Please install AWS CLI first."
    echo "Installation guide: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
    exit 1
fi

# Check if Terraform is installed
if ! command -v terraform &> /dev/null; then
    print_error "Terraform is not installed. Please install Terraform first."
    echo "Installation guide: https://learn.hashicorp.com/tutorials/terraform/install-cli"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS credentials not configured. Please run 'aws configure' first."
    exit 1
fi

print_success "Prerequisites check passed!"

# Get AWS account info
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region || echo "us-east-1")

print_status "AWS Account ID: $AWS_ACCOUNT_ID"
print_status "AWS Region: $AWS_REGION"
print_mag7 "Deploying for Magnificent 7 stocks: AAPL, MSFT, GOOGL, AMZN, NVDA, TSLA, META"

# Navigate to terraform directory
cd terraform

# Check if terraform.tfvars exists
if [ ! -f terraform.tfvars ]; then
    print_warning "terraform.tfvars not found. Creating from example..."
    cp terraform.tfvars.example terraform.tfvars
    
    echo ""
    print_warning "Please edit terraform.tfvars with your configuration:"
    echo "  1. Set your AWS key pair name"
    echo "  2. Set secure passwords for database and InfluxDB"
    echo "  3. Add your API keys (Polygon, Alpha Vantage, OpenAI)"
    echo "  4. Adjust instance types for production workload"
    echo "  5. Configure Magnificent 7 symbols and DTE target"
    echo ""
    read -p "Press Enter after editing terraform.tfvars to continue..."
fi

# Validate Terraform configuration
print_status "Validating Terraform configuration..."
terraform fmt
terraform validate

if [ $? -ne 0 ]; then
    print_error "Terraform configuration validation failed!"
    exit 1
fi

print_success "Terraform configuration is valid!"

# Initialize Terraform
print_status "Initializing Terraform..."
terraform init

# Plan deployment
print_status "Creating deployment plan..."
terraform plan -out=tfplan

echo ""
print_warning "Review the deployment plan above."
print_mag7 "This will deploy infrastructure for 7-day options trading on Magnificent 7 stocks."
read -p "Do you want to proceed with the deployment? (y/N): " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_status "Deployment cancelled."
    exit 0
fi

# Apply deployment
print_status "Deploying Mag7-7DTE infrastructure to AWS..."
print_status "This may take 15-20 minutes due to enhanced infrastructure..."

terraform apply tfplan

if [ $? -ne 0 ]; then
    print_error "Terraform deployment failed!"
    exit 1
fi

# Get outputs
print_status "Retrieving deployment information..."
LOAD_BALANCER_DNS=$(terraform output -raw load_balancer_dns)
APPLICATION_URL=$(terraform output -raw load_balancer_url)
MAG7_SYMBOLS=$(terraform output -raw mag7_symbols)
DTE_TARGET=$(terraform output -raw dte_target)

# Wait for application to be ready
print_status "Waiting for Mag7-7DTE application to be ready..."
print_status "This may take 10-15 minutes for initial deployment and data initialization..."

for i in {1..90}; do
    if curl -f "$APPLICATION_URL/health" &>/dev/null; then
        print_success "Mag7-7DTE application is ready!"
        break
    fi
    if [ $i -eq 90 ]; then
        print_warning "Application health check timeout. It may still be starting up."
        break
    fi
    sleep 20
done

# Display deployment summary
echo ""
echo "🎉 Mag7-7DTE-System Cloud Deployment Complete!"
echo "=============================================="
echo ""
print_mag7 "Magnificent 7 Trading System Deployed Successfully!"
echo ""
echo "📊 Application URLs:"
echo "   Frontend:     $APPLICATION_URL"
echo "   Backend API:  $APPLICATION_URL/api"
echo "   API Docs:     $APPLICATION_URL/docs"
echo "   Health Check: $APPLICATION_URL/health"
echo ""
echo "🔧 Infrastructure Details:"
echo "   Load Balancer: $LOAD_BALANCER_DNS"
echo "   AWS Region:    $AWS_REGION"
echo "   Account ID:    $AWS_ACCOUNT_ID"
echo ""
echo "📈 Trading Configuration:"
echo "   Target Stocks: $MAG7_SYMBOLS"
echo "   DTE Target:    $DTE_TARGET days"
echo "   Strategy:      7-day options on individual stocks"
echo ""
echo "🏗️  Enhanced Infrastructure:"
echo "   • Larger EC2 instances (t3.xlarge) for processing"
echo "   • Enhanced RDS (db.t3.small) for fundamental data"
echo "   • Dedicated InfluxDB instance for time-series data"
echo "   • Enhanced Redis cluster for caching"
echo "   • Auto-scaling group (1-5 instances)"
echo ""
echo "📝 Next Steps:"
echo "   1. Access the application at: $APPLICATION_URL"
echo "   2. Configure IBKR connection for individual stock options"
echo "   3. Verify fundamental data feeds (Alpha Vantage)"
echo "   4. Monitor enhanced logging in AWS CloudWatch"
echo "   5. Set up SSL certificate for production use"
echo ""
echo "🛠️  Management Commands:"
echo "   • View infrastructure: terraform show"
echo "   • Update deployment:   terraform plan && terraform apply"
echo "   • Scale instances:     Update desired_instances in terraform.tfvars"
echo "   • Destroy resources:   terraform destroy"
echo ""
echo "📋 Enhanced Monitoring:"
echo "   • CloudWatch Logs: /aws/ec2/mag7-7dte-system"
echo "   • InfluxDB Logs:   /aws/ec2/mag7-7dte-influxdb"
echo "   • Auto Scaling:    mag7-7dte-asg"
echo "   • Load Balancer:   mag7-7dte-alb"
echo "   • Custom Metrics:  Mag7-7DTE-System namespace"
echo ""
print_success "Mag7-7DTE cloud deployment completed successfully!"

# Save deployment info
cat > ../deployment-info.txt << EOF
Mag7-7DTE-System Cloud Deployment Information
=============================================

Deployment Date: $(date)
AWS Account ID: $AWS_ACCOUNT_ID
AWS Region: $AWS_REGION

Application URLs:
- Frontend: $APPLICATION_URL
- Backend API: $APPLICATION_URL/api
- API Documentation: $APPLICATION_URL/docs
- Health Check: $APPLICATION_URL/health

Trading Configuration:
- Target Stocks: $MAG7_SYMBOLS
- DTE Target: $DTE_TARGET days
- Strategy: 7-day options on Magnificent 7 stocks

Infrastructure:
- Load Balancer DNS: $LOAD_BALANCER_DNS
- Auto Scaling Group: mag7-7dte-asg
- Database: RDS PostgreSQL (enhanced)
- Cache: ElastiCache Redis (enhanced)
- Time-Series DB: Dedicated InfluxDB instance

Management:
- Terraform state: terraform/terraform.tfstate
- AWS Console: https://console.aws.amazon.com/
- CloudWatch Logs: /aws/ec2/mag7-7dte-system
- InfluxDB Logs: /aws/ec2/mag7-7dte-influxdb
EOF

print_status "Deployment information saved to deployment-info.txt"

