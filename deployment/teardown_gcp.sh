#!/bin/bash

# GCP Teardown Script for Multi-Cloud Distributed System

# --- Configuration ---
PROJECT_ID=$(gcloud config get-value project)
ZONE=$(gcloud config get-value compute/zone)
FIREWALL_RULE_NAME="multi-cloud-firewall"

echo "Starting GCP teardown process..."

# 1. Find and delete instances tagged with multi-cloud-node
echo "Finding instances to delete..."
INSTANCE_NAMES=$(gcloud compute instances list \
    --project="$PROJECT_ID" \
    --filter="tags:multi-cloud-node" \
    --format="value(name)")

if [ -z "$INSTANCE_NAMES" ]; then
    echo "No instances found with tag multi-cloud-node in project $PROJECT_ID."
else
    echo "Deleting instances: $INSTANCE_NAMES"
    # Delete instances in the specified zone
    gcloud compute instances delete $INSTANCE_NAMES --zone="$ZONE" --project="$PROJECT_ID" --quiet
    echo "Instances deleted."
fi

# 2. Delete the firewall rule
echo "Finding firewall rule $FIREWALL_RULE_NAME..."
if gcloud compute firewall-rules describe "$FIREWALL_RULE_NAME" --project="$PROJECT_ID" --quiet &>/dev/null; then
    echo "Deleting firewall rule $FIREWALL_RULE_NAME..."
    gcloud compute firewall-rules delete "$FIREWALL_RULE_NAME" --project="$PROJECT_ID" --quiet
    echo "Firewall rule deleted."
else
    echo "Firewall rule $FIREWALL_RULE_NAME not found in project $PROJECT_ID. Skipping deletion."
fi

echo "GCP teardown process finished."

