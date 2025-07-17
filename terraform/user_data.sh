#!/bin/bash

# Mag7-7DTE-System EC2 User Data Script
# This script sets up the application on EC2 instances

set -e

# Update system
yum update -y

# Install Docker
amazon-linux-extras install docker -y
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install Git
yum install -y git

# Install CloudWatch agent
yum install -y amazon-cloudwatch-agent

# Create application directory
mkdir -p /opt/mag7-7dte-system
cd /opt/mag7-7dte-system

# Clone repository (in production, you'd use a specific release)
git clone https://github.com/TKTINC/mag7-7DTE-system.git .

# Create environment file
cat > .env << EOF
# Database Configuration
DATABASE_URL=postgresql://postgres:${db_password}@${db_host}:5432/${db_name}
REDIS_URL=redis://${redis_host}:6379
INFLUXDB_URL=http://${influxdb_host}:8086
INFLUXDB_TOKEN=mag7-7dte-token-123456789
INFLUXDB_ORG=mag7-7dte
INFLUXDB_BUCKET=market_data

# API Keys
POLYGON_API_KEY=${polygon_api_key}
ALPHA_VANTAGE_API_KEY=${alpha_vantage_api_key}
OPENAI_API_KEY=${openai_api_key}

# IBKR Configuration
IBKR_HOST=${ibkr_host}
IBKR_PORT=${ibkr_port}
IBKR_CLIENT_ID=${ibkr_client_id}

# Application Configuration
ENVIRONMENT=production
LOG_LEVEL=INFO

# Magnificent 7 Configuration
MAG7_SYMBOLS=${mag7_symbols}
DTE_TARGET=${dte_target}
EOF

# Create production Docker Compose override
cat > docker-compose.prod.yml << EOF
version: '3.8'

services:
  backend:
    environment:
      - DATABASE_URL=postgresql://postgres:${db_password}@${db_host}:5432/${db_name}
      - REDIS_URL=redis://${redis_host}:6379
      - INFLUXDB_URL=http://${influxdb_host}:8086
    restart: always
    
  data-feed:
    environment:
      - DATABASE_URL=postgresql://postgres:${db_password}@${db_host}:5432/${db_name}
      - REDIS_URL=redis://${redis_host}:6379
      - INFLUXDB_URL=http://${influxdb_host}:8086
    restart: always
    
  signal-generator:
    environment:
      - DATABASE_URL=postgresql://postgres:${db_password}@${db_host}:5432/${db_name}
      - REDIS_URL=redis://${redis_host}:6379
      - INFLUXDB_URL=http://${influxdb_host}:8086
    restart: always
    
  frontend:
    restart: always

# Remove database services (using managed services)
  postgres:
    deploy:
      replicas: 0
      
  redis:
    deploy:
      replicas: 0
      
  influxdb:
    deploy:
      replicas: 0
EOF

# Build and start services
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# Create systemd service for auto-start
cat > /etc/systemd/system/mag7-7dte.service << EOF
[Unit]
Description=Mag7-7DTE-System
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/mag7-7dte-system
ExecStart=/usr/local/bin/docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.yml -f docker-compose.prod.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

systemctl enable mag7-7dte.service

# Configure CloudWatch logging
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << EOF
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/opt/mag7-7dte-system/logs/*.log",
            "log_group_name": "/aws/ec2/mag7-7dte-system",
            "log_stream_name": "{instance_id}/application"
          }
        ]
      }
    }
  },
  "metrics": {
    "namespace": "Mag7-7DTE-System",
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
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json -s

# Create health check script
cat > /opt/mag7-7dte-system/health-check.sh << 'EOF'
#!/bin/bash
curl -f http://localhost:8000/health || exit 1
curl -f http://localhost:3000 || exit 1
EOF

chmod +x /opt/mag7-7dte-system/health-check.sh

# Add health check to cron
echo "*/5 * * * * /opt/mag7-7dte-system/health-check.sh" | crontab -

# Create log rotation for application logs
cat > /etc/logrotate.d/mag7-7dte << EOF
/opt/mag7-7dte-system/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 root root
    postrotate
        docker-compose -f /opt/mag7-7dte-system/docker-compose.yml -f /opt/mag7-7dte-system/docker-compose.prod.yml restart backend data-feed signal-generator
    endscript
}
EOF

# Signal completion
/opt/aws/bin/cfn-signal -e $? --stack "$${AWS::StackName}" --resource AutoScalingGroup --region "$${AWS::Region}" || true

