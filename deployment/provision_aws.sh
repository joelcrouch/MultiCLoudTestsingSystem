#!/bin/bash

# AWS Provisioning Script for Multi-Cloud Distributed System

# --- Configuration ---
REGION="us-east-1"
INSTANCE_TYPE="t4g.nano"
KEY_NAME="multicloudKey2_east_1"
INSTANCE_COUNT=3
SECURITY_GROUP_NAME="multi-cloud-sg"
PROJECT_REPO="https://github.com/joelcrouch/MultiCLoudTestsingSystem"
APP_PORT=8080 # Port for inter-node communication

# Find the latest Amazon Linux 2 ARM AMI in the specified region
echo "Fetching latest Amazon Linux 2 ARM AMI ID for region $REGION..."
AMI_ID=$(aws ec2 describe-images --region "$REGION" --owners amazon --filters "Name=name,Values=amzn2-ami-hvm-*-arm64-gp2" "Name=state,Values=available" --query "sort_by(Images, &CreationDate)[-1].ImageId" --output text)

if [ -z "$AMI_ID" ]; then
    echo "Error: Could not find a suitable AMI ID in $REGION. Exiting."
    exit 1
fi
echo "Using AMI ID: $AMI_ID"

# --- Startup Script (User Data) ---
# This script runs when the instance first boots
read -r -d '' USER_DATA <<EOF
#!/bin/bash
echo "Starting user data script..."
yum update -y
yum install -y git python3-pip

# Clone the repository
echo "Cloning repository: $PROJECT_REPO"
git clone $PROJECT_REPO /home/ec2-user/multiCloudDistSys

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install -r /home/ec2-user/multiCloudDistSys/requirements.txt

# Start the application (placeholder for now)
echo "Starting the application (placeholder)..."
# Example: python3 /home/ec2-user/multiCloudDistSys/src/main.py &
# For now, we'll just ensure the setup is complete.
echo "Application setup complete on instance."
EOF

# --- Provisioning Steps ---

# 1. Check if Security Group already exists
SG_ID=$(aws ec2 describe-security-groups --region "$REGION" --group-names "$SECURITY_GROUP_NAME" --query "SecurityGroups[0].GroupId" --output text 2>/dev/null)

if [ -z "$SG_ID" ]; then
    echo "Creating security group: $SECURITY_GROUP_NAME"
    SG_ID=$(aws ec2 create-security-group --group-name "$SECURITY_GROUP_NAME" --description "Security group for multi-cloud experiment" --region "$REGION" --query "GroupId" --output text)
    echo "Security Group ID: $SG_ID"

    # 2. Add Firewall Rules
    echo "Authorizing ingress for SSH (port 22) and App (port $APP_PORT) from anywhere (0.0.0.0/0)."
    echo "WARNING: 0.0.0.0/0 for app port is insecure for production. Will be refined later."
    aws ec2 authorize-security-group-ingress --group-id "$SG_ID" --protocol tcp --port 22 --cidr 0.0.0.0/0 --region "$REGION"
    aws ec2 authorize-security-group-ingress --group-id "$SG_ID" --protocol tcp --port "$APP_PORT" --cidr 0.0.0.0/0 --region "$REGION"
else
    echo "Security group $SECURITY_GROUP_NAME already exists with ID: $SG_ID. Skipping creation and ingress rules."
fi

# 3. Launch Instances
echo "Launching $INSTANCE_COUNT instances of type $INSTANCE_TYPE in $REGION..."
aws ec2 run-instances \
    --region "$REGION" \
    --image-id "$AMI_ID" \
    --instance-type "$INSTANCE_TYPE" \
    --key-name "$KEY_NAME" \
    --security-group-ids "$SG_ID" \
    --user-data "$USER_DATA" \
    --count "$INSTANCE_COUNT" \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Project,Value=MultiCloudDistSys}, {Key=Name,Value=MultiCloudNode-AWS}]' \
    --associate-public-ip-address

echo "AWS provisioning script finished. Instances are launching."
echo "You can monitor their status in the AWS EC2 console or by running: aws ec2 describe-instances --region $REGION --filters 'Name=tag:Project,Values=MultiCloudDistSys' --query 'Reservations[*].Instances[*].{InstanceId:InstanceId,State:State.Name,PublicIp:PublicIpAddress}' --output table
