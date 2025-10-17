#!/bin/bash

# Verification Script for Multi-Cloud Distributed System

SKIP_GCP_TESTS=false
SKIP_AWS_TESTS=false

for arg in "$@"; do
    if [ "$arg" == "--aws-only" ]; then
        SKIP_GCP_TESTS=true
    elif [ "$arg" == "--gcp-only" ]; then
        SKIP_AWS_TESTS=true
    fi
done

# --- AWS Instance Details ---
aws_instance_ids=()
aws_public_ips=()
aws_instances_details=""

if [ "$SKIP_AWS_TESTS" = false ]; then
    echo "--- Verifying AWS Instances ---"
    echo "Searching for running or pending instances with tag 'Project=MultiCloudDistSys' in us-east-1..."

    aws_instances_details=$(aws ec2 describe-instances \
        --region us-east-1 \
        --filters "Name=tag:Project,Values=MultiCloudDistSys" "Name=instance-state-name,Values=running,pending" \
        --query "Reservations[*].Instances[*].{ID:InstanceId,State:State.Name,PublicIP:PublicIpAddress,PrivateIP:PrivateIpAddress,Type:InstanceType,Placement:Placement}" \
        --output json)

    echo "$aws_instances_details" | jq -r '.[] | .[] | [.ID, .State, .PublicIP, .PrivateIP, .Type, .Placement.AvailabilityZone] | @tsv' | column -t

    aws_instance_ids=$(echo "$aws_instances_details" | jq -r '.[][].ID')
    aws_public_ips=$(echo "$aws_instances_details" | jq -r '.[][].PublicIP')
else
    echo "--- Skipping AWS Instance Verification (GCP-only mode) ---"
fi

# --- GCP Instance Details ---
gcp_instance_names=()
gcp_public_ips=()
gcp_instances_details=""

if [ "$SKIP_GCP_TESTS" = false ]; then
    echo ""
    echo "--- Verifying GCP Instances ---"
    echo "Searching for running instances with prefix 'multi-cloud-node-gcp-' in us-central1-a..."

    gcp_instances_details=$(gcloud compute instances list --filter="name~'multi-cloud-node-gcp-' AND status:RUNNING" --format="json")

    echo "$gcp_instances_details" | jq -r '.[] | [.name, .zone, .status, .networkInterfaces[0].accessConfigs[0].natIP] | @tsv' | column -t

    gcp_instance_names=$(echo "$gcp_instances_details" | jq -r '.[].name')
    gcp_public_ips=$(echo "$gcp_instances_details" | jq -r '.[].networkInterfaces[0].accessConfigs[0].natIP')
else
    echo ""
    echo "--- Skipping GCP Instance Verification (AWS-only mode) ---"
fi

# --- Combine all public IPs ---
all_public_ips=()
if [ "$SKIP_AWS_TESTS" = false ]; then
    all_public_ips+=(${aws_public_ips})
fi
if [ "$SKIP_GCP_TESTS" = false ]; then
    all_public_ips+=(${gcp_public_ips})
fi


echo ""
echo "--- Starting Network Connectivity Test ---"
echo "This will attempt to SSH into each instance to run ping commands."
echo "Please ensure you have the necessary permissions and configurations."

# Test from GCP instances
if [ "$SKIP_GCP_TESTS" = false ]; then
    if [ ${#gcp_instance_names[@]} -ne 0 ]; then
        for instance_name in ${gcp_instance_names}; do
            echo ""
            echo "--- Testing from GCP instance: $instance_name ---"
            my_ip=$(echo "$gcp_instances_details" | jq -r --arg name "$instance_name" '.[] | select(.name==$name) | .networkInterfaces[0].accessConfigs[0].natIP')
            for ip_to_ping in "${all_public_ips[@]}"; do
                if [ "$my_ip" == "$ip_to_ping" ]; then
                    echo "Skipping pinging self: $ip_to_ping"
                    continue
                fi
                echo "Pinging $ip_to_ping from $instance_name..."
                gcloud compute ssh "$instance_name" --zone "us-central1-a" --command "ping -c 3 $ip_to_ping"
            done
        done
    else
        echo "No running GCP instances found to test from."
    fi
else
    echo ""
    echo "--- Skipping GCP Connectivity Test (AWS-only mode) ---"
fi


# Test from AWS instances
PEM_FILE="/home/dell-linux-dev3/Downloads/multi-cloud-key-3.pem"
PUB_KEY_FILE="/tmp/multi-cloud-key-3.pub"

if [ "$SKIP_AWS_TESTS" = false ]; then
    if [ ! -f "$PEM_FILE" ]; then
        echo "Error: Private key file not found at $PEM_FILE"
    else
        ssh-keygen -y -f "$PEM_FILE" > "$PUB_KEY_FILE"
        if [ ${#aws_instance_ids[@]} -ne 0 ]; then
            for instance_id in ${aws_instance_ids}; do
                echo ""
                echo "--- Testing from AWS instance: $instance_id ---"
                instance_ip=$(echo "$aws_instances_details" | jq -r --arg id "$instance_id" '.[] | .[] | select(.ID==$id) | .PublicIP')
                availability_zone=$(echo "$aws_instances_details" | jq -r --arg id "$instance_id" '.[] | .[] | select(.ID==$id) | .Placement.AvailabilityZone')

                echo "Pushing temporary SSH key to $instance_id..."
                aws ec2-instance-connect send-ssh-public-key \
                    --instance-id "$instance_id" \
                    --region "us-east-1" \
                    --availability-zone "$availability_zone" \
                    --instance-os-user ec2-user \
                    --ssh-public-key "file://$PUB_KEY_FILE"

                if [ $? -ne 0 ]; then
                    echo "Error: Failed to push SSH key to $instance_id. Skipping tests from this instance."
                    continue
                fi

                for ip_to_ping in "${all_public_ips[@]}"; do
                    if [ "$instance_ip" == "$ip_to_ping" ]; then
                        echo "Skipping pinging self: $ip_to_ping"
                        continue
                    fi
                    echo "Pinging $ip_to_ping from $instance_id..."
                    ssh -i "$PEM_FILE" -o "StrictHostKeyChecking=no" -o "UserKnownHostsFile=/dev/null" \
                        ec2-user@"$instance_ip" "ping -c 3 $ip_to_ping"
                done
            done
        else
            echo "No running AWS instances found to test from."
        fi
        rm -f "$PUB_KEY_FILE"
    fi
else
    echo ""
    echo "--- Skipping AWS Connectivity Test (GCP-only mode) ---"
fi


# echo ""
# echo "--- Verification Complete ---"


# #!/bin/bash

# # Verification Script for Multi-Cloud Distributed System

# # --- Configuration ---
# AZURE_RESOURCE_GROUP="MultiCloudRG" # Must match the provisioning script's RG name
# AZURE_USERNAME="azureuser"          # Must match the provisioning script's username
# AZURE_PEM_FILE="/home/dell-linux-dev3/Downloads/multi-cloud-key-3.pem" # Use the same key file as AWS
# AWS_REGION="us-east-1"
# GCP_ZONE="us-central1-a"

# SKIP_GCP_TESTS=false
# SKIP_AWS_TESTS=false
# SKIP_AZURE_TESTS=false # New skip flag

# for arg in "$@"; do
#     if [ "$arg" == "--aws-only" ]; then
#         SKIP_GCP_TESTS=true
#         SKIP_AZURE_TESTS=true
#     elif [ "$arg" == "--gcp-only" ]; then
#         SKIP_AWS_TESTS=true
#         SKIP_AZURE_TESTS=true
#     elif [ "$arg" == "--azure-only" ]; then
#         SKIP_AWS_TESTS=true
#         SKIP_GCP_TESTS=true
#     fi
# done

# # --- AWS Instance Details ---
# aws_instance_ids=()
# aws_public_ips=()
# aws_instances_details=""

# if [ "$SKIP_AWS_TESTS" = false ]; then
#     echo "--- Verifying AWS Instances ---"
#     echo "Searching for running or pending instances with tag 'Project=MultiCloudDistSys' in $AWS_REGION..."

#     aws_instances_details=$(aws ec2 describe-instances \
#         --region "$AWS_REGION" \
#         --filters "Name=tag:Project,Values=MultiCloudDistSys" "Name=instance-state-name,Values=running,pending" \
#         --query "Reservations[*].Instances[*].{ID:InstanceId,State:State.Name,PublicIP:PublicIpAddress,PrivateIP:PrivateIpAddress,Type:InstanceType,Placement:Placement}" \
#         --output json)

#     echo "$aws_instances_details" | jq -r '.[] | .[] | [.ID, .State, .PublicIP, .PrivateIP, .Type, .Placement.AvailabilityZone] | @tsv' | column -t

#     # Use 'map' to flatten the list of IDs and IPs
#     aws_instance_ids=($(echo "$aws_instances_details" | jq -r '.[][].ID'))
#     aws_public_ips=($(echo "$aws_instances_details" | jq -r '.[][].PublicIP'))
# else
#     echo "--- Skipping AWS Instance Verification ---"
# fi

# # ----------------------------------------------------------------------
# # --- NEW: AZURE VM Details ---
# # ----------------------------------------------------------------------
# azure_vm_names=()
# azure_public_ips=()
# azure_vms_details=""

# if [ "$SKIP_AZURE_TESTS" = false ]; then
#     echo ""
#     echo "--- Verifying Azure VMs ---"
#     echo "Searching for running VMs in resource group '$AZURE_RESOURCE_GROUP'..."

#     # Query running VMs and select Name and Public IP
#     azure_vms_details=$(az vm list \
#         --resource-group "$AZURE_RESOURCE_GROUP" \
#         --show-details \
#         --query "[?powerState=='VM running'].{Name:name, PublicIP:publicIps, State:powerState, Size:hardwareProfile.vmSize}" \
#         --output json)

#     # Format the output table
#     echo "$azure_vms_details" | jq -r '.[] | [.Name, .State, .PublicIP, .Size] | @tsv' | column -t

#     azure_vm_names=($(echo "$azure_vms_details" | jq -r '.[].Name'))
#     azure_public_ips=($(echo "$azure_vms_details" | jq -r '.[].PublicIP'))
# else
#     echo ""
#     echo "--- Skipping AZURE VM Verification ---"
# fi
# # ----------------------------------------------------------------------

# # --- GCP Instance Details ---
# gcp_instance_names=()
# gcp_public_ips=()
# gcp_instances_details=""

# if [ "$SKIP_GCP_TESTS" = false ]; then
#     echo ""
#     echo "--- Verifying GCP Instances ---"
#     echo "Searching for running instances with prefix 'multi-cloud-node-gcp-' in $GCP_ZONE..."

#     gcp_instances_details=$(gcloud compute instances list --filter="name~'multi-cloud-node-gcp-' AND status:RUNNING" --format="json")

#     echo "$gcp_instances_details" | jq -r '.[] | [.name, .zone, .status, .networkInterfaces[0].accessConfigs[0].natIP] | @tsv' | column -t

#     gcp_instance_names=($(echo "$gcp_instances_details" | jq -r '.[].name'))
#     gcp_public_ips=($(echo "$gcp_instances_details" | jq -r '.[].networkInterfaces[0].accessConfigs[0].natIP'))
# else
#     echo ""
#     echo "--- Skipping GCP Instance Verification ---"
# fi

# # ----------------------------------------------------------------------
# # --- Combine all public IPs ---
# # ----------------------------------------------------------------------
# all_public_ips=()
# if [ "$SKIP_AWS_TESTS" = false ]; then
#     all_public_ips+=(${aws_public_ips[@]})
# fi
# if [ "$SKIP_GCP_TESTS" = false ]; then
#     all_public_ips+=(${gcp_public_ips[@]})
# fi
# if [ "$SKIP_AZURE_TESTS" = false ]; then
#     all_public_ips+=(${azure_public_ips[@]})
# fi


# echo ""
# echo "--- Starting Network Connectivity Test ---"
# echo "This will attempt to SSH into each instance to run ping commands."

# # ----------------------------------------------------------------------
# # --- Test from AZURE instances ---
# # ----------------------------------------------------------------------
# if [ "$SKIP_AZURE_TESTS" = false ]; then
#     if [ ! -f "$AZURE_PEM_FILE" ]; then
#         echo "Error: Private key file not found at $AZURE_PEM_FILE. Cannot test from Azure instances."
#     elif [ ${#azure_vm_names[@]} -ne 0 ]; then
#         for vm_name in "${azure_vm_names[@]}"; do
#             echo ""
#             echo "--- Testing from Azure VM: $vm_name ---"
            
#             # Get the Public IP of the source Azure VM
#             source_ip=$(echo "$azure_vms_details" | jq -r --arg name "$vm_name" '.[] | select(.Name==$name) | .PublicIP')
            
#             for ip_to_ping in "${all_public_ips[@]}"; do
#                 if [ "$source_ip" == "$ip_to_ping" ]; then
#                     echo "Skipping pinging self: $ip_to_ping"
#                     continue
#                 fi
#                 echo "Pinging $ip_to_ping from $vm_name ($source_ip)..."
                
#                 # SSH into the Azure VM to run the ping command
#                 ssh -i "$AZURE_PEM_FILE" -o "StrictHostKeyChecking=no" -o "UserKnownHostsFile=/dev/null" \
#                     "$AZURE_USERNAME"@"$source_ip" "ping -c 3 $ip_to_ping"
#             done
#         done
#     else
#         echo "No running Azure instances found to test from."
#     fi
# else
#     echo ""
#     echo "--- Skipping Azure Connectivity Test ---"
# fi
# # ----------------------------------------------------------------------

# # Test from GCP instances (No change, but now pings Azure)
# if [ "$SKIP_GCP_TESTS" = false ]; then
#     if [ ${#gcp_instance_names[@]} -ne 0 ]; then
#         for instance_name in "${gcp_instance_names[@]}"; do
#             echo ""
#             echo "--- Testing from GCP instance: $instance_name ---"
#             my_ip=$(echo "$gcp_instances_details" | jq -r --arg name "$instance_name" '.[] | select(.name==$name) | .networkInterfaces[0].accessConfigs[0].natIP')
#             for ip_to_ping in "${all_public_ips[@]}"; do
#                 if [ "$my_ip" == "$ip_to_ping" ]; then
#                     echo "Skipping pinging self: $ip_to_ping"
#                     continue
#                 fi
#                 echo "Pinging $ip_to_ping from $instance_name..."
#                 gcloud compute ssh "$instance_name" --zone "$GCP_ZONE" --command "ping -c 3 $ip_to_ping"
#             done
#         done
#     else
#         echo "No running GCP instances found to test from."
#     fi
# else
#     echo ""
#     echo "--- Skipping GCP Connectivity Test ---"
# fi


# # Test from AWS instances (Original, now pings Azure)
# PEM_FILE="/home/dell-linux-dev3/Downloads/multi-cloud-key-3.pem"
# PUB_KEY_FILE="/tmp/multi-cloud-key-3.pub"

# if [ "$SKIP_AWS_TESTS" = false ]; then
#     if [ ! -f "$PEM_FILE" ]; then
#         echo "Error: Private key file not found at $PEM_FILE"
#     else
#         ssh-keygen -y -f "$PEM_FILE" > "$PUB_KEY_FILE"
#         if [ ${#aws_instance_ids[@]} -ne 0 ]; then
#             for instance_id in "${aws_instance_ids[@]}"; do
#                 echo ""
#                 echo "--- Testing from AWS instance: $instance_id ---"
#                 instance_ip=$(echo "$aws_instances_details" | jq -r --arg id "$instance_id" '.[] | .[] | select(.ID==$id) | .PublicIP')
#                 availability_zone=$(echo "$aws_instances_details" | jq -r --arg id "$instance_id" '.[] | .[] | select(.ID==$id) | .Placement.AvailabilityZone')

#                 echo "Pushing temporary SSH key to $instance_id..."
#                 aws ec2-instance-connect send-ssh-public-key \
#                     --instance-id "$instance_id" \
#                     --region "$AWS_REGION" \
#                     --availability-zone "$availability_zone" \
#                     --instance-os-user ec2-user \
#                     --ssh-public-key "file://$PUB_KEY_FILE"

#                 if [ $? -ne 0 ]; then
#                     echo "Error: Failed to push SSH key to $instance_id. Skipping tests from this instance."
#                     continue
#                 fi

#                 for ip_to_ping in "${all_public_ips[@]}"; do
#                     if [ "$instance_ip" == "$ip_to_ping" ]; then
#                         echo "Skipping pinging self: $ip_to_ping"
#                         continue
#                     fi
#                     echo "Pinging $ip_to_ping from $instance_id..."
#                     ssh -i "$PEM_FILE" -o "StrictHostKeyChecking=no" -o "UserKnownHostsFile=/dev/null" \
#                         ec2-user@"$instance_ip" "ping -c 3 $ip_to_ping"
#                 done
#             done
#         else
#             echo "No running AWS instances found to test from."
#         fi
#         rm -f "$PUB_KEY_FILE"
#     fi
# else
#     echo ""
#     echo "--- Skipping AWS Connectivity Test ---"
# fi


# echo ""
# echo "--- Verification Complete ---"