#!/bin/bash
# Quick script to build and deploy backend with permission fixes

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Building and deploying backend with permission fixes...${NC}"

# Configuration
AWS_REGION="ap-south-1"
AWS_ACCOUNT_ID="122610483530"
ECR_REPO="tenant-management-backend"
IMAGE_TAG="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}:latest"

# Navigate to backend directory
cd backend

echo -e "${YELLOW}Step 1: Building Docker image...${NC}"
docker build -t $IMAGE_TAG .

echo -e "${YELLOW}Step 2: Logging into ECR...${NC}"
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

echo -e "${YELLOW}Step 3: Pushing image to ECR...${NC}"
docker push $IMAGE_TAG

echo -e "${YELLOW}Step 4: Restarting backend deployment...${NC}"
kubectl rollout restart deployment/backend -n tenant-management

echo -e "${YELLOW}Step 5: Waiting for rollout to complete...${NC}"
kubectl rollout status deployment/backend -n tenant-management --timeout=5m

echo -e "${GREEN}✓ Backend deployed with permission fixes!${NC}"
echo ""
echo "Next steps:"
echo "1. Login as operator.user and verify you see NO tenants"
echo "2. Login as admin.user"
echo "3. Go to User Management and grant namespace access to operators"
echo "4. Verify operators can only see their assigned tenants"
