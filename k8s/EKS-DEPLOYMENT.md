# EKS Deployment Guide

This guide explains how to deploy the Tenant Management Application to AWS EKS from VS Code.

## Prerequisites

Before deploying to EKS, ensure you have:

### 1. Install Required Tools

```bash
# Install AWS CLI
brew install awscli

# Install eksctl (optional, for cluster creation)
brew install eksctl

# Install Helm (optional, for AWS Load Balancer Controller)
brew install helm

# Verify installations
kubectl version --client
aws --version
docker --version
```

### 2. Configure AWS Credentials

```bash
# Configure AWS CLI with your credentials
aws configure

# You'll need:
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region (e.g., us-east-1)
# - Output format (json)

# Verify configuration
aws sts get-caller-identity
```

### 3. EKS Cluster

You need an existing EKS cluster, or the script can create one for you.

## Quick Deployment

### Option 1: Automated Full Deployment (Recommended)

From VS Code terminal:

```bash
cd /Users/comviva/Documents/Code/ManageAWS/k8s
./deploy-eks.sh deploy
```

This will:
1. ✅ Check all prerequisites
2. ✅ Configure AWS credentials (if needed)
3. ✅ Connect to your EKS cluster (or create one)
4. ✅ Create ECR repositories
5. ✅ Build Docker images
6. ✅ Push images to Amazon ECR
7. ✅ Update Kubernetes manifests
8. ✅ Deploy all services to EKS
9. ✅ Set up AWS Load Balancer (optional)
10. ✅ Display access information

### Option 2: Step-by-Step Deployment

#### Step 1: Build and Push Images Only
```bash
./deploy-eks.sh build
```

#### Step 2: Deploy to EKS
```bash
./deploy-eks.sh apply
```

## Script Commands

```bash
# Full deployment (build + deploy)
./deploy-eks.sh deploy

# Build and push images to ECR only
./deploy-eks.sh build

# Deploy/update Kubernetes manifests only
./deploy-eks.sh apply

# Cleanup and delete all resources
./deploy-eks.sh cleanup
```

## What the Script Does

### 1. Prerequisites Check
- Verifies `kubectl`, `docker`, and `aws` CLI are installed
- Checks AWS credentials are configured
- Validates cluster connectivity

### 2. ECR Setup
- Creates Amazon ECR repositories for backend and frontend
- Authenticates Docker with ECR
- Tags images with ECR repository URLs

### 3. Image Build & Push
```bash
# Backend image
docker build -t <account-id>.dkr.ecr.<region>.amazonaws.com/tenant-management-backend:latest ./backend
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/tenant-management-backend:latest

# Frontend image  
docker build -t <account-id>.dkr.ecr.<region>.amazonaws.com/tenant-management-frontend:latest ./frontend
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/tenant-management-frontend:latest
```

### 4. Manifest Updates
Creates EKS-specific manifests in `k8s/eks-manifests/` with:
- ECR image paths
- `imagePullPolicy: Always`
- AWS-specific configurations

### 5. Kubernetes Deployment
Deploys in order:
1. Namespace
2. Secrets & ConfigMaps
3. PostgreSQL database
4. RBAC permissions
5. Backend API
6. Frontend application
7. Ingress (with optional ALB)

### 6. AWS Load Balancer Controller (Optional)
- Sets up IAM OIDC provider
- Creates IAM policy and service account
- Installs AWS Load Balancer Controller via Helm
- Configures Application Load Balancer for ingress

## Accessing Your Application

### Option 1: Via Load Balancer (if ALB is configured)

After deployment, get the load balancer URL:

```bash
kubectl get ingress -n tenant-management

# Output will show:
# NAME                          CLASS    HOSTS   ADDRESS                               PORTS   AGE
# tenant-management-ingress    <none>   *       k8s-tenantma-xxxxxx.us-east-1.elb.amazonaws.com   80      5m
```

Access at: `http://<load-balancer-address>`

⚠️ **Note**: DNS propagation may take 2-5 minutes.

### Option 2: Via Port Forwarding (immediate access)

```bash
# Frontend (in one terminal)
kubectl port-forward -n tenant-management svc/frontend-service 8080:80

# Backend API (in another terminal)
kubectl port-forward -n tenant-management svc/backend-service 8000:8000
```

Then access:
- Frontend: http://localhost:8080
- Backend API: http://localhost:8000/docs

## Useful Commands

### View Resources
```bash
# All resources in namespace
kubectl get all -n tenant-management

# Pods status
kubectl get pods -n tenant-management

# Services
kubectl get svc -n tenant-management

# Ingress
kubectl get ingress -n tenant-management
```

### View Logs
```bash
# Backend logs
kubectl logs -f -n tenant-management -l app=backend

# Frontend logs
kubectl logs -f -n tenant-management -l app=frontend

# Postgres logs
kubectl logs -f -n tenant-management -l app=postgres

# Specific pod
kubectl logs -f -n tenant-management <pod-name>
```

### Debugging
```bash
# Describe pod
kubectl describe pod -n tenant-management <pod-name>

# Execute commands in pod
kubectl exec -it -n tenant-management <pod-name> -- /bin/bash

# View events
kubectl get events -n tenant-management --sort-by='.lastTimestamp'
```

### Updates
```bash
# Update backend after code changes
cd /Users/comviva/Documents/Code/ManageAWS/k8s
./deploy-eks.sh build  # Rebuild and push images

# Restart deployment to pull new images
kubectl rollout restart deployment/backend -n tenant-management
kubectl rollout restart deployment/frontend -n tenant-management

# Check rollout status
kubectl rollout status deployment/backend -n tenant-management
```

## Cost Management

### View Current Resources
```bash
# Node information
kubectl get nodes

# Resource usage
kubectl top nodes
kubectl top pods -n tenant-management
```

### Scale Down to Save Costs
```bash
# Scale down deployments
kubectl scale deployment/backend --replicas=0 -n tenant-management
kubectl scale deployment/frontend --replicas=0 -n tenant-management

# Scale back up
kubectl scale deployment/backend --replicas=2 -n tenant-management
kubectl scale deployment/frontend --replicas=2 -n tenant-management
```

### Delete Everything
```bash
# Using the script
./deploy-eks.sh cleanup

# Manual deletion
kubectl delete namespace tenant-management

# Delete ECR repositories
aws ecr delete-repository --repository-name tenant-management-backend --force
aws ecr delete-repository --repository-name tenant-management-frontend --force
```

## Troubleshooting

### Images Not Pulling
```bash
# Check if images exist in ECR
aws ecr describe-images --repository-name tenant-management-backend
aws ecr describe-images --repository-name tenant-management-frontend

# Verify IAM permissions for EKS nodes
aws iam get-role --role-name <node-role-name>
```

### Pods Not Starting
```bash
# Check pod events
kubectl describe pod -n tenant-management <pod-name>

# Check logs
kubectl logs -n tenant-management <pod-name>

# Check previous logs if pod restarted
kubectl logs -n tenant-management <pod-name> --previous
```

### Database Connection Issues
```bash
# Test database connectivity
kubectl exec -it -n tenant-management <backend-pod> -- env | grep DATABASE

# Check PostgreSQL is running
kubectl get pods -n tenant-management -l app=postgres

# Test connection from backend pod
kubectl exec -it -n tenant-management <backend-pod> -- \
  python -c "from app.database import engine; print(engine.connect())"
```

### Load Balancer Not Created
```bash
# Check ALB controller logs
kubectl logs -n kube-system -l app.kubernetes.io/name=aws-load-balancer-controller

# Verify IAM permissions
eksctl get iamserviceaccount --cluster <cluster-name>

# Check ingress annotations
kubectl describe ingress -n tenant-management
```

## CI/CD Integration

### GitHub Actions Example

Create `.github/workflows/deploy-eks.yml`:

```yaml
name: Deploy to EKS

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v1
      
      - name: Deploy to EKS
        run: |
          chmod +x ./k8s/deploy-eks.sh
          ./k8s/deploy-eks.sh deploy
```

## Security Best Practices

1. **Use Secrets Manager** for sensitive data
2. **Enable Pod Security Standards**
3. **Use Network Policies** to restrict traffic
4. **Enable audit logging**
5. **Regularly update images** for security patches
6. **Use IAM roles** instead of static credentials
7. **Enable encryption** at rest and in transit

## Additional Resources

- [EKS Best Practices Guide](https://aws.github.io/aws-eks-best-practices/)
- [AWS Load Balancer Controller Docs](https://kubernetes-sigs.github.io/aws-load-balancer-controller/)
- [kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)
- [EKS Workshop](https://www.eksworkshop.com/)
