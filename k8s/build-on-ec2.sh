#!/bin/bash

# Build Frontend on AWS EC2 AMD64 Instance
# This script launches an EC2 instance, builds the frontend image, pushes to ECR, and terminates the instance

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_header() {
    echo ""
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}  Build Frontend on EC2 AMD64${NC}"
    echo -e "${BLUE}============================================${NC}"
    echo ""
}

# Configuration
AWS_REGION="ap-south-1"
AWS_ACCOUNT_ID="122610483530"
INSTANCE_TYPE="t3.medium"
AMI_ID="ami-0c2af51e265bd5e0e"  # Amazon Linux 2023 AMD64 in ap-south-1
KEY_NAME="frontend-builder-key"
SECURITY_GROUP_NAME="frontend-builder-sg"
ECR_BACKEND_REPO="tenant-management-backend"
ECR_FRONTEND_REPO="tenant-management-frontend"

print_header

# Get the project directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log_step "Checking AWS configuration..."
if ! aws sts get-caller-identity &> /dev/null; then
    log_error "AWS credentials not configured"
    exit 1
fi
log_info "AWS credentials verified ✓"

# Create key pair if it doesn't exist
log_step "Setting up SSH key pair..."
if ! aws ec2 describe-key-pairs --key-names $KEY_NAME --region $AWS_REGION &> /dev/null; then
    log_info "Creating new key pair..."
    aws ec2 create-key-pair --key-name $KEY_NAME --region $AWS_REGION --query 'KeyMaterial' --output text > ~/.ssh/${KEY_NAME}.pem
    chmod 400 ~/.ssh/${KEY_NAME}.pem
    log_info "Key pair created: ~/.ssh/${KEY_NAME}.pem"
else
    log_info "Key pair already exists"
fi

# Get VPC and Subnet
log_step "Getting VPC and Subnet..."
VPC_ID=$(aws ec2 describe-vpcs --region $AWS_REGION --query 'Vpcs[0].VpcId' --output text)
SUBNET_ID=$(aws ec2 describe-subnets --region $AWS_REGION --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[0].SubnetId' --output text)
log_info "Using VPC: $VPC_ID, Subnet: $SUBNET_ID"

# Create security group if it doesn't exist
log_step "Setting up security group..."
SG_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=$SECURITY_GROUP_NAME" --region $AWS_REGION --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || echo "None")

if [ "$SG_ID" == "None" ]; then
    log_info "Creating security group..."
    SG_ID=$(aws ec2 create-security-group \
        --group-name $SECURITY_GROUP_NAME \
        --description "Security group for frontend builder EC2 instance" \
        --vpc-id $VPC_ID \
        --region $AWS_REGION \
        --query 'GroupId' --output text)
    
    # Add SSH rule
    aws ec2 authorize-security-group-ingress \
        --group-id $SG_ID \
        --protocol tcp \
        --port 22 \
        --cidr 0.0.0.0/0 \
        --region $AWS_REGION
    
    log_info "Security group created: $SG_ID"
else
    log_info "Security group already exists: $SG_ID"
fi

# Create IAM role for ECR access if it doesn't exist
log_step "Preparing instance configuration..."
log_info "Will use AWS credentials for ECR access"

# Get AWS credentials to pass to instance
AWS_ACCESS_KEY=$(aws configure get aws_access_key_id)
AWS_SECRET_KEY=$(aws configure get aws_secret_access_key)

# Launch EC2 instance
log_step "Launching EC2 instance..."

USER_DATA=$(cat <<'EOF'
#!/bin/bash
yum update -y
yum install -y docker git

# Start Docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install
rm -rf awscliv2.zip aws

# Signal completion
touch /tmp/init-complete
EOF
)subnet-id $SUBNET_ID \
    --associate-public-ip-address \
    --

INSTANCE_ID=$(aws ec2 run-instances \
    --image-id $AMI_ID \
    --instance-type $INSTANCE_TYPE \
    --key-name $KEY_NAME \
    --security-group-ids $SG_ID \
    --subnet-id $SUBNET_ID \
    --associate-public-ip-address \
    --user-data "$USER_DATA" \
    --region $AWS_REGION \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=frontend-builder}]" \
    --query 'Instances[0].InstanceId' \
    --output text)

log_info "Instance launched: $INSTANCE_ID"
log_info "Waiting for instance to be running..."

aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $AWS_REGION

# Get public IP
INSTANCE_IP=$(aws ec2 describe-instances \
    --instance-ids $INSTANCE_ID \
    --region $AWS_REGION \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text)

log_info "Instance is running at: $INSTANCE_IP"
log_info "Waiting for initialization to complete (this may take 2-3 minutes)..."
EOF
#!/bin/bash
yum update -y
yum install -y docker git

# Start Docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install
rm -rf awscliv2.zip aws

# Configure AWS credentials
mkdir -p /home/ec2-user/.aws
cat > /home/ec2-user/.aws/credentials <<AWSCREDS
[default]
aws_access_key_id = ${AWS_ACCESS_KEY}
aws_secret_access_key = ${AWS_SECRET_KEY}
AWSCREDS

cat > /home/ec2-user/.aws/config <<AWSCONFIG
[default]
region = ${AWS_REGION}
output = json
AWSCONFIG

chown -R ec2-user:ec2-user /home/ec2-user/.aws
chmod 600 /home/ec2-user/.aws/credential
# Copy project files
log_step "Copying project files to EC2..."
cd "$PROJECT_ROOT"
tar czf /tmp/frontend.tar.gz frontend/
scp -i ~/.ssh/${KEY_NAME}.pem -o StrictHostKeyChecking=no /tmp/frontend.tar.gz ec2-user@$INSTANCE_IP:/tmp/
rm /tmp/frontend.tar.gz

# Build on EC2
log_step "Building Docker image on EC2..."

ssh -i ~/.ssh/${KEY_NAME}.pem -o StrictHostKeyChecking=no ec2-user@$INSTANCE_IP << 'ENDSSH'
set -e

echo "Extracting frontend files..."
cd /tmp
tar xzf frontend.tar.gz
cd frontend

echo "Logging into ECR..."
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin 122610483530.dkr.ecr.ap-south-1.amazonaws.com

echo "Building Docker image..."
docker build -t 122610483530.dkr.ecr.ap-south-1.amazonaws.com/tenant-management-frontend:latest .

echo "Pushing image to ECR..."
docker push 122610483530.dkr.ecr.ap-south-1.amazonaws.com/tenant-management-frontend:latest

echo "Build and push completed successfully!"
ENDSSH

if [ $? -eq 0 ]; then
    log_info "Frontend image built and pushed successfully! ✓"
else
    log_error "Build failed"
    log_warn "Instance $INSTANCE_ID left running for debugging"
    log_info "SSH into instance: ssh -i ~/.ssh/${KEY_NAME}.pem ec2-user@$INSTANCE_IP"
    exit 1
fi

# Cleanup
log_step "Cleaning up..."
log_info "Terminating EC2 instance..."
aws ec2 terminate-instances --instance-ids $INSTANCE_ID --region $AWS_REGION > /dev/null
log_info "Instance $INSTANCE_ID terminating"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Build Complete! 🎉${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
log_info "Frontend image available at:"
echo "  122610483530.dkr.ecr.ap-south-1.amazonaws.com/tenant-management-frontend:latest"
echo ""
log_info "Now deploy the frontend:"
echo "  cd $PROJECT_ROOT/k8s"
echo "  kubectl rollout restart deployment/frontend -n tenant-management"
echo ""
