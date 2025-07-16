# Mag7-7DTE-System: Deployment Guide

This guide provides comprehensive instructions for deploying the Mag7-7DTE-System in various environments, from local development to production.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Local Development Deployment](#local-development-deployment)
3. [Docker Deployment](#docker-deployment)
4. [AWS Cloud Deployment](#aws-cloud-deployment)
5. [Monitoring and Maintenance](#monitoring-and-maintenance)
6. [Troubleshooting](#troubleshooting)

## System Requirements

### Hardware Requirements

- **Development**: 4+ CPU cores, 8GB+ RAM, 20GB+ storage
- **Production**: 8+ CPU cores, 16GB+ RAM, 100GB+ SSD storage
- **Database**: Separate instance recommended for production with 4+ CPU cores, 8GB+ RAM, 100GB+ SSD storage

### Software Requirements

- **Operating System**: Ubuntu 20.04 LTS or newer (recommended), or any Linux distribution
- **Docker**: Docker Engine 20.10+ and Docker Compose 2.0+
- **Database**: PostgreSQL 13+, Redis 6+, InfluxDB 2.0+
- **Python**: 3.9+ (for local development without Docker)
- **Node.js**: 16+ (for local development without Docker)

### Network Requirements

- **Ports**: 80/443 (HTTP/HTTPS), 5432 (PostgreSQL), 6379 (Redis), 8086 (InfluxDB)
- **Bandwidth**: 10+ Mbps for development, 100+ Mbps for production
- **Data Feed**: Reliable connection to Polygon.io and Alpha Vantage APIs

## Local Development Deployment

### 1. Clone the Repository

```bash
git clone https://github.com/TKTINC/mag7-7DTE-system.git
cd mag7-7DTE-system
```

### 2. Set Up Environment Variables

Create a `.env` file in the root directory:

```bash
# Database Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=mag7_7dte
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=your_secure_password

# InfluxDB Configuration
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_TOKEN=your_influxdb_token
INFLUXDB_ORG=mag7_7dte
INFLUXDB_BUCKET=market_data

# API Keys
POLYGON_API_KEY=your_polygon_api_key
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_api_key

# JWT Secret
JWT_SECRET=your_jwt_secret_key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Frontend Configuration
VITE_API_URL=http://localhost:8000
```

### 3. Start the Development Environment

Using Docker Compose:

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

This will start all services in development mode with hot reloading enabled.

### 4. Initialize the Database

```bash
docker-compose exec backend python -m app.scripts.init_db
```

### 5. Generate Sample Data (Optional)

```bash
docker-compose exec backend python -m app.scripts.generate_sample_data
```

### 6. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## Docker Deployment

### 1. Production Docker Compose Setup

For production deployment, use the production Docker Compose file:

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

The production configuration includes:
- Optimized build settings
- Nginx reverse proxy with SSL
- Health checks
- Automatic restarts
- Volume mounts for persistent data

### 2. SSL Configuration

For production deployment with SSL:

1. Create a `certs` directory in the project root:

```bash
mkdir -p certs
```

2. Add your SSL certificates:
   - `certs/fullchain.pem`: Your certificate chain
   - `certs/privkey.pem`: Your private key

3. Update the Nginx configuration in `nginx/nginx.conf` to use SSL.

### 3. Database Backup

Set up regular database backups:

```bash
# Add to crontab
0 0 * * * docker-compose exec -T postgres pg_dump -U postgres mag7_7dte > /path/to/backups/mag7_7dte_$(date +\%Y\%m\%d).sql
```

## AWS Cloud Deployment

### 1. Infrastructure Setup

#### Using AWS CLI

```bash
# Create VPC
aws ec2 create-vpc --cidr-block 10.0.0.0/16 --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=Mag7-7DTE-VPC}]'

# Create subnets
aws ec2 create-subnet --vpc-id vpc-id --cidr-block 10.0.1.0/24 --availability-zone us-east-1a --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=Mag7-7DTE-Public-1a}]'
aws ec2 create-subnet --vpc-id vpc-id --cidr-block 10.0.2.0/24 --availability-zone us-east-1b --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=Mag7-7DTE-Public-1b}]'

# Create security groups
aws ec2 create-security-group --group-name Mag7-7DTE-SG --description "Security group for Mag7-7DTE-System" --vpc-id vpc-id
```

#### Using AWS CloudFormation

A CloudFormation template is provided in `aws/cloudformation.yml` for automated infrastructure setup.

```bash
aws cloudformation create-stack --stack-name Mag7-7DTE-Stack --template-body file://aws/cloudformation.yml --parameters ParameterKey=KeyName,ParameterValue=your-key-pair
```

### 2. EC2 Instance Setup

1. Launch an EC2 instance with Ubuntu 20.04 LTS.
2. Install Docker and Docker Compose:

```bash
sudo apt update
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.5.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

3. Clone the repository and set up environment variables as described in the Local Development section.

### 3. Database Setup with RDS

1. Create a PostgreSQL RDS instance:

```bash
aws rds create-db-instance \
    --db-instance-identifier mag7-7dte-db \
    --db-instance-class db.t3.medium \
    --engine postgres \
    --master-username postgres \
    --master-user-password your_secure_password \
    --allocated-storage 100 \
    --vpc-security-group-ids sg-id \
    --db-subnet-group-name your-subnet-group
```

2. Update the `.env` file with the RDS endpoint.

### 4. ElastiCache for Redis

1. Create a Redis ElastiCache cluster:

```bash
aws elasticache create-cache-cluster \
    --cache-cluster-id mag7-7dte-redis \
    --engine redis \
    --cache-node-type cache.t3.medium \
    --num-cache-nodes 1 \
    --security-group-ids sg-id \
    --cache-subnet-group-name your-subnet-group
```

2. Update the `.env` file with the ElastiCache endpoint.

### 5. Load Balancer Setup

1. Create an Application Load Balancer:

```bash
aws elbv2 create-load-balancer \
    --name Mag7-7DTE-ALB \
    --subnets subnet-id-1 subnet-id-2 \
    --security-groups sg-id
```

2. Create target groups and listeners for HTTP/HTTPS.

### 6. Deployment with Docker

Follow the Docker Deployment instructions above, but update the environment variables to use the AWS resources.

## Monitoring and Maintenance

### 1. Logging

The system uses structured logging with JSON format. Logs are available in the following locations:

- **Docker**: `docker-compose logs -f [service_name]`
- **AWS CloudWatch**: If deployed on AWS, logs are sent to CloudWatch

### 2. Monitoring

#### Prometheus and Grafana

The system includes Prometheus for metrics collection and Grafana for visualization.

1. Access Grafana at http://your-domain:3000/grafana
2. Default credentials: admin/admin
3. Import the provided dashboards from `monitoring/grafana-dashboards/`

#### Health Checks

Health check endpoints are available at:

- `/api/v1/health` - Backend API health
- `/health` - Frontend health

### 3. Backup and Recovery

#### Database Backup

Automated backups are configured for:

- PostgreSQL: Daily full backups, WAL archiving for point-in-time recovery
- InfluxDB: Daily backups of time-series data

#### Backup Locations

- Local: `/var/backups/mag7-7dte/`
- AWS: S3 bucket `mag7-7dte-backups`

#### Recovery Procedure

1. Stop the services:

```bash
docker-compose down
```

2. Restore the database:

```bash
# PostgreSQL
cat backup.sql | docker-compose exec -T postgres psql -U postgres mag7_7dte

# InfluxDB
docker-compose exec influxdb influx restore -t your_influxdb_token /path/to/backup
```

3. Restart the services:

```bash
docker-compose up -d
```

## Troubleshooting

### Common Issues

#### Database Connection Errors

**Symptom**: Backend service fails to start with database connection errors.

**Solution**:
1. Check if the database container is running: `docker-compose ps`
2. Verify database credentials in `.env`
3. Check database logs: `docker-compose logs postgres`

#### Data Feed Issues

**Symptom**: No market data is being received.

**Solution**:
1. Verify API keys in `.env`
2. Check data feed service logs: `docker-compose logs data-feed`
3. Ensure the system clock is synchronized
4. Verify network connectivity to API providers

#### Frontend Connection Issues

**Symptom**: Frontend cannot connect to backend API.

**Solution**:
1. Check if the backend is running: `docker-compose ps`
2. Verify the `VITE_API_URL` in `.env`
3. Check for CORS issues in browser developer console
4. Ensure the Nginx configuration is correct

### Support Resources

- **GitHub Issues**: https://github.com/TKTINC/mag7-7DTE-system/issues
- **Documentation**: https://github.com/TKTINC/mag7-7DTE-system/docs
- **Contact**: support@example.com

