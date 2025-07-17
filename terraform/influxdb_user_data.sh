#!/bin/bash

# InfluxDB Setup Script for Mag7-7DTE-System
# This script sets up InfluxDB on a dedicated EC2 instance

set -e

# Update system
yum update -y

# Install Docker
amazon-linux-extras install docker -y
systemctl start docker
systemctl enable docker

# Create InfluxDB data directory
mkdir -p /opt/influxdb/data
mkdir -p /opt/influxdb/config

# Create InfluxDB configuration
cat > /opt/influxdb/config/influxdb.conf << EOF
[meta]
  dir = "/var/lib/influxdb/meta"

[data]
  dir = "/var/lib/influxdb/data"
  engine = "tsm1"
  wal-dir = "/var/lib/influxdb/wal"

[coordinator]

[retention]

[shard-precreation]

[monitor]

[http]
  enabled = true
  bind-address = ":8086"
  auth-enabled = false
  log-enabled = true
  write-tracing = false
  pprof-enabled = true
  debug-pprof-enabled = false
  https-enabled = false

[logging]
  format = "auto"
  level = "info"
  suppress-logo = false

[[graphite]]

[[collectd]]

[[opentsdb]]

[[udp]]

[continuous_queries]
  log-enabled = true
  enabled = true
EOF

# Run InfluxDB container
docker run -d \
  --name influxdb \
  --restart unless-stopped \
  -p 8086:8086 \
  -v /opt/influxdb/data:/var/lib/influxdb2 \
  -v /opt/influxdb/config:/etc/influxdb2 \
  -e DOCKER_INFLUXDB_INIT_MODE=setup \
  -e DOCKER_INFLUXDB_INIT_USERNAME=admin \
  -e DOCKER_INFLUXDB_INIT_PASSWORD=${influxdb_admin_password} \
  -e DOCKER_INFLUXDB_INIT_ORG=mag7-7dte \
  -e DOCKER_INFLUXDB_INIT_BUCKET=market_data \
  -e DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=mag7-7dte-token-123456789 \
  influxdb:2.7

# Wait for InfluxDB to start
sleep 30

# Create systemd service for InfluxDB
cat > /etc/systemd/system/influxdb.service << EOF
[Unit]
Description=InfluxDB for Mag7-7DTE-System
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/docker start influxdb
ExecStop=/usr/bin/docker stop influxdb
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

systemctl enable influxdb.service

# Install CloudWatch agent
yum install -y amazon-cloudwatch-agent

# Configure CloudWatch monitoring for InfluxDB
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << EOF
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/opt/influxdb/logs/*.log",
            "log_group_name": "/aws/ec2/mag7-7dte-influxdb",
            "log_stream_name": "{instance_id}/influxdb"
          }
        ]
      }
    }
  },
  "metrics": {
    "namespace": "Mag7-7DTE-InfluxDB",
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

# Create backup script
cat > /opt/influxdb/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/influxdb/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
docker exec influxdb influx backup "$BACKUP_DIR"
# Keep only last 7 days of backups
find /opt/influxdb/backups -type d -mtime +7 -exec rm -rf {} +
EOF

chmod +x /opt/influxdb/backup.sh

# Schedule daily backups
echo "0 2 * * * /opt/influxdb/backup.sh" | crontab -

# Create health check script
cat > /opt/influxdb/health-check.sh << 'EOF'
#!/bin/bash
curl -f http://localhost:8086/ping || exit 1
EOF

chmod +x /opt/influxdb/health-check.sh

# Add health check to cron
echo "*/5 * * * * /opt/influxdb/health-check.sh" | crontab -

