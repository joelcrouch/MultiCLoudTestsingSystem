#!/bin/bash

# Azure Teardown Script for Multi-Cloud Distributed System

# --- Configuration ---
RESOURCE_GROUP_NAME="MultiCloudRG"

echo "Starting Azure teardown process..."

# 1. Check if the Resource Group exists
echo "Checking for Resource Group: $RESOURCE_GROUP_NAME"
if az group show --name "$RESOURCE_GROUP_NAME" --output none 2>/dev/null; then
    
    # 2. Delete the entire Resource Group
    echo "Resource Group found. Deleting $RESOURCE_GROUP_NAME and ALL contained resources..."
    echo "This operation is irreversible."
    
    # The --yes flag bypasses the confirmation prompt
    # The --no-wait flag allows the script to finish immediately while Azure deletes resources in the background
    az group delete --name "$RESOURCE_GROUP_NAME" --yes --no-wait
    
    echo "Deletion command issued. Resources will be removed in the background."
    echo "You can check the status in the Azure Portal or by running: az group show --name $RESOURCE_GROUP_NAME"
else
    echo "Resource Group $RESOURCE_GROUP_NAME not found. Nothing to delete."
fi

echo "Azure teardown process finished."