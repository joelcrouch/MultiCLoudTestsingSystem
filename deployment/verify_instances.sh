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


echo ""
echo "--- Verification Complete ---"