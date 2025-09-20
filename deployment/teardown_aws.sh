#!/bin/bash

# AWS Teardown Script for Multi-Cloud Distributed System

# --- Configuration ---
REGION="us-east-1"
SECURITY_GROUP_NAME="multi-cloud-sg"

echo "Starting AWS teardown process..."

# 1. Find and terminate instances tagged with Project=MultiCloudDistSys
echo "Finding instances to terminate..."
INSTANCE_IDS=$(aws ec2 describe-instances \
    --region "$REGION" \
    --filters "Name=tag:Project,Values=MultiCloudDistSys" "Name=instance-state-name,Values=running,pending,stopping,stopped" \
    --query "Reservations[*].Instances[*].InstanceId" \
    --output text)

if [ -z "$INSTANCE_IDS" ]; then
    echo "No running/pending/stopping/stopped instances found with tag Project=MultiCloudDistSys in $REGION."
else
    echo "Terminating instances: $INSTANCE_IDS"
    aws ec2 terminate-instances --region "$REGION" --instance-ids $INSTANCE_IDS
    echo "Waiting for instances to terminate..."
    aws ec2 wait instance-terminated --region "$REGION" --instance-ids $INSTANCE_IDS
    echo "Instances terminated."
fi

# 2. Delete the security group
echo "Finding security group $SECURITY_GROUP_NAME..."
SG_ID=$(aws ec2 describe-security-groups --region "$REGION" --group-names "$SECURITY_GROUP_NAME" --query "SecurityGroups[0].GroupId" --output text 2>/dev/null)

if [ -z "$SG_ID" ]; then
    echo "Security group $SECURITY_GROUP_NAME not found in $REGION. Skipping deletion."
else
    echo "Deleting security group $SECURITY_GROUP_NAME (ID: $SG_ID)..."
    # Need to ensure no instances are using it, but wait above should handle that.
    aws ec2 delete-security-group --region "$REGION" --group-id "$SG_ID"
    echo "Security group deleted."
fi

echo "AWS teardown process finished."

