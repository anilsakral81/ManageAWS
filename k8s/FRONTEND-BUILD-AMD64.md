# Frontend Build Guide for AMD64 Architecture

The frontend needs to be built for AMD64 (x86_64) architecture to run on your EKS cluster nodes. Since you're on an ARM64 Mac, cross-compilation can be challenging. Here are your options:

## Option 1: Build on EC2 (Recommended) ✅

This method launches a temporary EC2 instance, builds the image natively on AMD64, pushes to ECR, and terminates the instance.

**Advantages:**
- Native AMD64 build (fast and reliable)
- Automatic cleanup
- No local resource usage

**Run:**
```bash
cd /Users/comviva/Documents/Code/ManageAWS/k8s
./build-on-ec2.sh
```

**What it does:**
1. Creates necessary AWS resources (key pair, security group, IAM role)
2. Launches a t3.medium EC2 instance
3. Copies frontend code to the instance
4. Builds Docker image natively
5. Pushes to ECR
6. Terminates the instance
7. Total time: ~5-7 minutes

**Cost:** ~$0.02 USD (t3.medium for ~5 minutes)

## Option 2: Build Locally with Buildx ⚙️

Uses Docker Buildx with QEMU emulation and optimized settings.

**Advantages:**
- No AWS resources needed
- All done locally

**Disadvantages:**
- Slower (10-15 minutes due to emulation)
- May still encounter memory issues
- Higher CPU/RAM usage on your Mac

**Run:**
```bash
cd /Users/comviva/Documents/Code/ManageAWS/k8s
./build-frontend-local.sh
```

## Option 3: Manual Build on EC2

If you prefer manual control:

### 1. Launch EC2 Instance
```bash
aws ec2 run-instances \
  --image-id ami-0c2af51e265bd5e0e \
  --instance-type t3.medium \
  --key-name YOUR_KEY_NAME \
  --region ap-south-1 \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=frontend-builder}]'
```

### 2. SSH into Instance
```bash
ssh -i ~/.ssh/YOUR_KEY.pem ec2-user@<INSTANCE_IP>
```

### 3. Install Docker & AWS CLI
```bash
sudo yum update -y
sudo yum install -y docker git
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -a -G docker ec2-user

# Logout and login again, then:
aws configure  # Enter your credentials
```

### 4. Copy Frontend Code
On your Mac:
```bash
cd /Users/comviva/Documents/Code/ManageAWS
tar czf frontend.tar.gz frontend/
scp -i ~/.ssh/YOUR_KEY.pem frontend.tar.gz ec2-user@<INSTANCE_IP>:/home/ec2-user/
```

### 5. Build and Push
On EC2:
```bash
tar xzf frontend.tar.gz
cd frontend

# Login to ECR
aws ecr get-login-password --region ap-south-1 | \
  docker login --username AWS --password-stdin \
  122610483530.dkr.ecr.ap-south-1.amazonaws.com

# Build
docker build -t 122610483530.dkr.ecr.ap-south-1.amazonaws.com/tenant-management-frontend:latest .

# Push
docker push 122610483530.dkr.ecr.ap-south-1.amazonaws.com/tenant-management-frontend:latest
```

### 6. Terminate Instance
```bash
aws ec2 terminate-instances --instance-ids <INSTANCE_ID> --region ap-south-1
```

## Optimizations Applied

I've already optimized your frontend for AMD64 builds:

### 1. Updated `vite.config.ts`:
- Reduced memory usage with chunking
- Optimized esbuild settings
- Better terser minification

### 2. Updated `Dockerfile`:
- Added `NODE_OPTIONS="--max-old-space-size=2048"`
- Optimized npm install with `--prefer-offline --no-audit`

### 3. Created Build Scripts:
- `build-on-ec2.sh` - Automated EC2 build
- `build-frontend-local.sh` - Local buildx with optimizations

## Deploy After Building

Once the image is built and pushed to ECR:

```bash
# Restart frontend deployment to pull new image
kubectl rollout restart deployment/frontend -n tenant-management

# Wait for rollout to complete
kubectl rollout status deployment/frontend -n tenant-management

# Check pods
kubectl get pods -n tenant-management

# View logs
kubectl logs -n tenant-management -l app=frontend
```

## Verify Frontend is Running

```bash
# Port forward to access locally
kubectl port-forward -n tenant-management svc/frontend-service 8080:80

# Then visit: http://localhost:8080
```

## Recommended Approach

**For production/regular builds:**
- Use Option 1 (EC2) for reliability and speed

**For quick tests:**
- Try Option 2 (local buildx) if you don't mind waiting

**My recommendation:** Run the EC2 script - it's automated, reliable, and cost-effective!

```bash
cd /Users/comviva/Documents/Code/ManageAWS/k8s
./build-on-ec2.sh
```
