#!/bin/bash

# Quick EC2 Frontend Builder
# Simplified version that uses existing resources

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

# Configuration
AWS_REGION="ap-south-1"
AWS_ACCOUNT_ID="122610483530"
INSTANCE_TYPE="t3.medium"
AMI_ID="ami-0c2af51e265bd5e0e"
KEY_NAME="frontend-builder-key"
SG_ID="sg-0a449491eeeb09c7a"
VPC_ID="vpc-06ea3d9f076478f19"
SUBNET_ID="subnet-09dd63bc7bae7eaa8"

echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  Quick EC2 Frontend Builder${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Get AWS credentials
AWS_ACCESS_KEY=$(aws configure get aws_access_key_id)
AWS_SECRET_KEY=$(aws configure get aws_secret_access_key)

# Create user data
USER_DATA=$(cat <<EOF
#!/bin/bash
yum update -y
yum install -y docker git

systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install
rm -rf awscliv2.zip aws

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
chmod 600 /home/ec2-user/.aws/credentials

touch /tmp/init-complete
EOF
)

log_step "Launching EC2 instance..."

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

INSTANCE_IP=$(aws ec2 describe-instances \
    --instance-ids $INSTANCE_ID \
    --region $AWS_REGION \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text)

log_info "Instance running at: $INSTANCE_IP"
log_info "Waiting for initialization (90 seconds)..."
sleep 90

log_info "Testing SSH connection..."
for i in {1..10}; do
    if ssh -i ~/.ssh/${KEY_NAME}.pem -o StrictHostKeyChecking=no -o ConnectTimeout=10 ec2-user@$INSTANCE_IP "echo 'SSH OK'" &> /dev/null; then
        log_info "SSH connected ✓"
        break
    fi
    log_warn "Attempt $i: Waiting for SSH..."
    sleep 10
done

log_step "Copying frontend code..."
cd "$PROJECT_ROOT"
tar czf /tmp/frontend.tar.gz frontend/
scp -i ~/.ssh/${KEY_NAME}.pem -o StrictHostKeyChecking=no /tmp/frontend.tar.gz ec2-user@$INSTANCE_IP:/tmp/
rm /tmp/frontend.tar.gz

log_step "Building on EC2..."

ssh -i ~/.ssh/${KEY_NAME}.pem -o StrictHostKeyChecking=no ec2-user@$INSTANCE_IP << 'ENDSSH'
set -e
cd /tmp
tar xzf frontend.tar.gz
cd frontend

echo "Logging into ECR..."
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin 122610483530.dkr.ecr.ap-south-1.amazonaws.com

echo "Building image..."
docker build -t 122610483530.dkr.ecr.ap-south-1.amazonaws.com/tenant-management-frontend:latest .

echo "Pushing to ECR..."
docker push 122610483530.dkr.ecr.ap-south-1.amazonaws.com/tenant-management-frontend:latest

echo "Done!"
ENDSSH

if [ $? -eq 0 ]; then
    log_info "Build successful! ✓"
else
    log_error "Build failed"
    log_warn "Instance $INSTANCE_ID left running for debugging"
    log_info "SSH: ssh -i ~/.ssh/${KEY_NAME}.pem ec2-user@$INSTANCE_IP"
    exit 1
fi

log_step "Terminating instance..."
aws ec2 terminate-instances --instance-ids $INSTANCE_ID --region $AWS_REGION > /dev/null

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Success! 🎉${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
log_info "Frontend image: 122610483530.dkr.ecr.ap-south-1.amazonaws.com/tenant-management-frontend:latest"
echo ""
log_info "Deploy now:"
echo "  kubectl rollout restart deployment/frontend -n tenant-management"
echo ""
