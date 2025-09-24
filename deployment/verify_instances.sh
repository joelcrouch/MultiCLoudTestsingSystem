#!/bin/bash

# Verification Script for Multi-Cloud Distributed System

echo "--- Verifying AWS Instances ---"
echo "Searching for running or pending instances with tag 'Project=MultiCloudDistSys' in us-east-1..."

aws ec2 describe-instances \
    --region us-east-1 \
    --filters "Name=tag:Project,Values=MultiCloudDistSys" "Name=instance-state-name,Values=running,pending" \
    --query "Reservations[*].Instances[*].{ID:InstanceId,State:State.Name,PublicIP:PublicIpAddress,PrivateIP:PrivateIpAddress,Type:InstanceType}" \
    --output table

echo ""
echo "--- Verifying GCP Instances ---"
echo "Searching for running instances with prefix 'multi-cloud-node-gcp-' in us-central1-a..."

gcloud compute instances list --filter="name~'multi-cloud-node-gcp-' AND status:RUNNING"

echo ""
echo "--- Verification Complete ---"
