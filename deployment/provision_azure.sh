#!/bin/bash

# Azure Provisioning Script for Multi-Cloud Distributed System

# --- Configuration ---
RESOURCE_GROUP_NAME="MultiCloudRG"
LOCATION="centralus"                      # Azure Region (e.g., eastus, westus3)
VM_SIZE="Standard_B2s"                 # Azure VM Size (low-cost burstable size)
VM_COUNT=2
USERNAME="azureuser"                   # VM login username
SSH_KEY_PATH="~/.ssh/id_rsa.pub"       # Path to your existing SSH public key
PROJECT_REPO="https://github.com/joelcrouch/MultiCLoudTestsingSystem"
APP_PORT=8080                          # Port for inter-node communication
NSG_NAME="multi-cloud-nsg"             # Network Security Group Name
VNET_NAME="multi-cloud-vnet"
SUBNET_NAME="multi-cloud-subnet"
IMAGE_NAME="Ubuntu2204"                # Azure URN alias for a current Ubuntu image

# --- Startup Script (Custom Data) ---
# This script runs when the instance first boots
read -r -d '' CUSTOM_DATA <<EOF
#!/bin/bash
echo "Starting custom data script..."
apt-get update -y
apt-get install -y git python3-pip

# Allow ICMP (ping) traffic through the OS firewall
iptables -A INPUT -p icmp -j ACCEPT

# Clone the repository
echo "Cloning repository: $PROJECT_REPO"
git clone $PROJECT_REPO /home/$USERNAME/multiCloudDistSys

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install -r /home/$USERNAME/multiCloudDistSys/multiCloudDistSys/requirements.txt # Adjust path as necessary

# Start the application (placeholder for now)
echo "Starting the application (placeholder)..."
echo "Application setup complete on instance."
EOF

# --- Provisioning Steps ---

# 1. Create Resource Group (if it doesn't exist)
echo "Ensuring resource group $RESOURCE_GROUP_NAME exists in $LOCATION..."
az group create --name "$RESOURCE_GROUP_NAME" --location "$LOCATION" --output none

# 2. Create Network Security Group (NSG) and Rules
echo "Creating Network Security Group: $NSG_NAME"
az network nsg create --resource-group "$RESOURCE_GROUP_NAME" --name "$NSG_NAME" --location "$LOCATION"

echo "Waiting 10 seconds for NSG to propagate..."
sleep 10

echo "Authorizing ingress for SSH (port 22) and App (port $APP_PORT)."
echo "WARNING: Opening to * is insecure for production. Will be refined later."

# Rule 1: Allow SSH (Port 22) from Any
az network nsg rule create \
    --resource-group "$RESOURCE_GROUP_NAME" \
    --nsg-name "$NSG_NAME" \
    --name "Allow-SSH" \
    --priority 100 \
    --direction Inbound \
    --protocol Tcp \
    --destination-port-ranges 22 \
    --access Allow \
    --output none

# Rule 2: Allow Application Port (App Port) from Any
az network nsg rule create \
    --resource-group "$RESOURCE_GROUP_NAME" \
    --nsg-name "$NSG_NAME" \
    --name "Allow-AppPort" \
    --priority 110 \
    --direction Inbound \
    --protocol Tcp \
    --destination-port-ranges "$APP_PORT" \
    --access Allow \
    --output none

# Rule 3: Allow ICMP (Ping) - Azure uses an 'Any' protocol rule for ICMP
# (Note: Azure often uses the name 'Allow-ICMP' or protocol 'Icmp' for ping, 
# but a general 'Custom' rule with the right protocol number is also common. 
# We'll stick to a common practice of allowing Any for simplicity in test environments.)
az network nsg rule create \
    --resource-group "$RESOURCE_GROUP_NAME" \
    --nsg-name "$NSG_NAME" \
    --name "Allow-Ping-Any" \
    --priority 120 \
    --direction Inbound \
    --protocol Icmp \
    --destination-port-ranges '*' \
    --access Allow \
    --output none


# 3. Create Virtual Network (VNet) and Subnet
echo "Creating Virtual Network and Subnet..."
az network vnet create \
    --resource-group "$RESOURCE_GROUP_NAME" \
    --name "$VNET_NAME" \
    --location "$LOCATION" \
    --subnet-name "$SUBNET_NAME" \
    --output none

# 4. Create Public IP addresses explicitly
echo "Creating Public IP addresses..."
for i in $(seq 1 $VM_COUNT); do
    PUBLIC_IP_NAME="MultiCloudNode-Azure-${i}PublicIP"
    echo "Creating Public IP: $PUBLIC_IP_NAME"
    az network public-ip create \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --name "$PUBLIC_IP_NAME" \
        --sku Standard \
        --location "$LOCATION" \
        --output none
done

# 5. Launch Instances (Loop for multiple VMs)
echo "Launching $VM_COUNT instances of size $VM_SIZE..."
for i in $(seq 1 $VM_COUNT); do
    VM_NAME="MultiCloudNode-Azure-$i"
    PUBLIC_IP_NAME="${VM_NAME}PublicIP"
    
    echo "Creating VM: $VM_NAME"
    az vm create \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --name "$VM_NAME" \
        --location "$LOCATION" \
        --image "$IMAGE_NAME" \
        --size "$VM_SIZE" \
        --vnet-name "$VNET_NAME" \
        --subnet "$SUBNET_NAME" \
        --nsg "$NSG_NAME" \
        --public-ip-address "$PUBLIC_IP_NAME" \
        --admin-username "$USERNAME" \
        --ssh-key-values "$SSH_KEY_PATH" \
        --custom-data "$CUSTOM_DATA" \
        --tags Project="MultiCloudDistSys" Name="$VM_NAME" \
        --output none

    # Get the Public IP for monitoring
    PUBLIC_IP=$(az vm show --resource-group "$RESOURCE_GROUP_NAME" --name "$VM_NAME" --query "publicIps" --output tsv)
    echo "VM $VM_NAME created with Public IP: $PUBLIC_IP"
done

echo "Azure provisioning script finished. Virtual Machines are launching and applying custom data."
echo "You can monitor the status in the Azure Portal or by running: az vm list -g $RESOURCE_GROUP_NAME --query '[].{Name:name, PublicIP:publicIps, State:powerState}' -o table"