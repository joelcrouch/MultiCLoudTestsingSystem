#!/bin/bash

# GCP Provisioning Script for Multi-Cloud Distributed System

# --- Configuration ---
PROJECT_ID=$(gcloud config get-value project)
REGION=$(gcloud config get-value compute/region)
ZONE=$(gcloud config get-value compute/zone)
INSTANCE_TYPE="e2-micro" # Cheapest general-purpose instance
INSTANCE_COUNT=3
FIREWALL_RULE_NAME="multi-cloud-firewall"
PROJECT_REPO="https://github.com/joelcrouch/MultiCLoudTestsingSystem" # From user input
APP_PORT=8080 # Port for inter-node communication

# --- Startup Script (User Data) ---
# This script runs when the instance first boots
read -r -d '' STARTUP_SCRIPT <<EOF
#!/bin/bash
echo "Starting GCP user data script..."
apt-get update -y
apt-get install -y git python3 python3-pip

# Clone the repository
echo "Cloning repository: $PROJECT_REPO"
git clone $PROJECT_REPO /home/multiCloudDistSys

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install -r /home/multiCloudDistSys/requirements.txt

# Start the application (placeholder for now)
echo "Starting the application (placeholder)..."
# Example: python3 /home/multiCloudDistSys/src/main.py &
# For now, we'll just ensure the setup is complete.
echo "Application setup complete on instance."
EOF

# --- Provisioning Steps ---

# 1. Create Firewall Rule (if it doesn't exist)
echo "Checking for firewall rule: $FIREWALL_RULE_NAME"
if ! gcloud compute firewall-rules describe "$FIREWALL_RULE_NAME" --project="$PROJECT_ID" --quiet &>/dev/null; then
    echo "Creating firewall rule: $FIREWALL_RULE_NAME"
    echo "WARNING: Opening port $APP_PORT to 0.0.0.0/0 is insecure for production. Will be refined later."
    gcloud compute firewall-rules create "$FIREWALL_RULE_NAME" \
        --project="$PROJECT_ID" \
        --allow=tcp:22,tcp:"$APP_PORT" \
        --source-ranges=0.0.0.0/0 \
        --description="Allow SSH and app traffic for multi-cloud experiment" \
        --target-tags="multi-cloud-node"
else
    echo "Firewall rule $FIREWALL_RULE_NAME already exists. Skipping creation."
fi

# 2. Launch Instances
echo "Launching $INSTANCE_COUNT instances of type $INSTANCE_TYPE in $ZONE..."
for i in $(seq 1 $INSTANCE_COUNT); do
    INSTANCE_NAME="multi-cloud-node-gcp-$i"
    gcloud compute instances create "$INSTANCE_NAME" \
        --project="$PROJECT_ID" \
        --zone="$ZONE" \
        --machine-type="$INSTANCE_TYPE" \
        --image-family="debian-11" \
        --image-project="debian-cloud" \
        --metadata-from-file=startup-script=<(echo "$STARTUP_SCRIPT") \
        --tags="multi-cloud-node" \
        --labels="project=multi-cloud-distsys" \
        --preemptible # Use preemptible VMs for cost savings
done

echo "GCP provisioning script finished. Instances are launching."
echo "You can monitor their status by running: gcloud compute instances list --project $PROJECT_ID --filter='tags:multi-cloud-node'"
