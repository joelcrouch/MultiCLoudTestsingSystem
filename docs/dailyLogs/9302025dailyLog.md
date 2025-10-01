# Daily Log: 09/30/2025 - Infrastructure Re-Setup

## 🎯 **Objective**
After a full OS reinstallation, the goal was to bring the multi-cloud infrastructure back online, verify its connectivity, and prepare for Sprint 2 development.

---

## ❗ **Errors Encountered & Solutions**

This log details the series of configuration and infrastructure issues encountered and the steps taken to resolve them.

### 1. **Conda Environment Lost**
-   **Problem**: The project's `conda` environment was lost due to the OS crash.
-   **Solution**: Recreated the environment from scratch. The user was guided to run `conda create`, `conda activate`, and then `pip install -r requirements.txt` to restore the necessary Python dependencies.

### 2. **AWS & GCP CLIs Not Found**
-   **Problem**: Running the provisioning scripts failed because the `aws` and `gcloud` command-line tools were not installed on the new OS.
-   **Solution**:
    -   **AWS CLI**: Guided the user to download the official installer, unzip it, and run `sudo ./aws/install`.
    -   **GCP CLI**: Guided the user to run `sudo snap install google-cloud-cli --classic`.

### 3. **AWS Credentials Not Configured**
-   **Problem**: The AWS CLI was installed but not configured, leading to an `Unable to locate credentials` error.
-   **Solution**: Instructed the user to run `aws configure` and provide their credentials. This led to the discovery that the credentials themselves were lost.

### 4. **Lost AWS Access Keys**
-   **Problem**: The user had lost the Secret Access Key associated with their IAM user.
-   **Solution**: Walked the user through the process of creating a new, least-privilege IAM setup:
    1.  Created a new IAM Policy with the required EC2 permissions (from project logs).
    2.  Created a new IAM Group and attached the policy.
    3.  Created a new IAM User, added it to the group, and generated a new Access Key ID and Secret Access Key.

### 5. **EC2 Key Pair Not Found**
-   **Problem**: The `provision_aws.sh` script failed with an `InvalidKeyPair.NotFound` error.
-   **Solution**: Debugged the issue by having the user run `aws ec2 describe-key-pairs`, which showed no keys in the target region (`us-east-1`). We discovered the user had accidentally created the key pair in the wrong region (`us-east-2`, Ohio). The user then created a new key pair in the correct `us-east-1` region, and the script was updated with the new key name.

### 6. **AWS Account Pending Verification**
-   **Problem**: After fixing the key pair, the script failed with a `PendingVerification` error, indicating an account-level hold by AWS.
-   **Solution**: Explained that this is a temporary AWS hold that requires waiting. We decided to provision the GCP instances in the meantime to continue making progress.

### 7. **Cross-Cloud Connectivity Failure (Firewall)**
-   **Problem**: The verification script showed that GCP instances could not `ping` AWS instances.
-   **Solution**: Identified that the AWS Security Group was blocking incoming ICMP traffic. The `provision_aws.sh` script was modified to add a new ingress rule allowing all ICMP traffic, resolving the one-way connectivity issue.

### 8. **Remote Command Execution Failure on AWS**
-   **Problem**: The verification script was unable to run `ping` commands *from* the AWS instances due to an incorrect command syntax for the `aws ec2-instance-connect ssh` tool.
-   **Solution**: Researched the correct method for non-interactive command execution. The `verify_instances.sh` script was rewritten to use a more robust two-step process: `aws ec2-instance-connect send-ssh-public-key` followed by a standard `ssh` command using the user's `.pem` file.

### 9. **Private Key File Permissions**
-   **Problem**: The private key file (`.pem`) had permissions that were too open (`0664`), causing SSH to reject it with a "bad permissions" error.
-   **Solution**: Guided the user to change the file permissions to `0400` using `chmod 400 '/path/to/key.pem'`.

### 10. **Bash Syntax Error with Parentheses in Filename**
-   **Problem**: The `.pem` file name contained parentheses (`multi-cloud-key-3(1).pem`), which caused a `bash: syntax error near unexpected token '('` when referenced in the script.
-   **Solution**: Guided the user to rename the file to remove the parentheses (`multi-cloud-key-3.pem`), and then updated the `verify_instances.sh` script with the new filename.

### 11. **IAM Policy Missing `ec2-instance-connect:SendSSHPublicKey` Permission**
-   **Problem**: The `multicloud-cli-user` lacked permission to perform the `ec2-instance-connect:SendSSHPublicKey` action, leading to an `AccessDeniedException`.
-   **Solution**: Guided the user to update the `MultiCloudExperimentPolicy` in the AWS IAM console to include `"ec2-instance-connect:SendSSHPublicKey"` in the `Action` list.

### 12. **`jq` Error in AWS Instance Details Display**
-   **Problem**: The `jq` query for displaying AWS instance details in `verify_instances.sh` was trying to output the entire `Placement` object into a TSV row, which is not supported by `@tsv`.
-   **Solution**: Modified `verify_instances.sh` to extract only `Placement.AvailabilityZone` for display in the TSV output.

### 13. **`jq` Error in AWS Availability Zone Extraction (Over-correction)**
-   **Problem**: An attempt to fix a previous `jq` error led to an over-correction, causing `jq` to fail with `Cannot index array with string "Reservations"` because the input was already an array, not an object with a `Reservations` key.
-   **Solution**: Reverted the `jq` queries for `instance_ip` and `availability_zone` in `verify_instances.sh` back to their original, correct form (`.[] | .[] | select(.ID==$id) | .PublicIP` and `.[] | .[] | select(.ID==$id) | .Placement.AvailabilityZone`).

---

## ✅ **Final Verification Status**

-   All local dependencies (CLIs, conda environment) have been restored.
-   All infrastructure configuration issues have been resolved.
-   The provisioning and verification scripts have been debugged and updated.
-   **Full bi-directional connectivity between all AWS and GCP instances has been successfully verified.**