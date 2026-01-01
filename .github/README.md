# GitHub Actions Setup for EKS Deployment

This project uses GitHub Actions to automatically build and deploy the frontend to AWS EKS.

## Setup Instructions

### 1. Add AWS Credentials to GitHub Secrets

Go to your GitHub repository: **Settings → Secrets and variables → Actions**

Add these secrets:
- `AWS_ACCESS_KEY_ID`: Your AWS access key (AKIARZDBHQFFJM6QLOT5)
- `AWS_SECRET_ACCESS_KEY`: Your AWS secret key

### 2. Workflow Trigger Options

The workflow runs automatically when:
- Code is pushed to `main` branch
- Files in `frontend/` directory change

**Manual Trigger:**
1. Go to **Actions** tab in GitHub
2. Select "Build and Push Frontend to ECR"
3. Click "Run workflow"
4. Select branch and click "Run workflow"

### 3. First Time Setup

If this is your first workflow run, you need to push the code to GitHub:

```bash
cd /Users/comviva/Documents/Code/ManageAWS

# Initialize git if not already done
git init
git add .
git commit -m "Add GitHub Actions workflow for frontend deployment"

# Add your GitHub repository as remote
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git

# Push to GitHub
git push -u origin main
```

### 4. Monitor Workflow Execution

1. Go to **Actions** tab in your GitHub repository
2. Click on the running workflow
3. View real-time logs
4. Verify build and deployment success

### 5. Verify Deployment

After successful workflow execution:

```bash
# Check frontend pods
kubectl get pods -n tenant-management

# Check deployment status
kubectl get deployment frontend-deployment -n tenant-management

# View frontend logs
kubectl logs -f deployment/frontend-deployment -n tenant-management
```

## Workflow Details

- **Runs on**: Ubuntu AMD64 (no cross-platform emulation issues!)
- **Build time**: ~3-5 minutes
- **Auto-deploys**: Yes, to EKS cluster wonderful-blues-rainbow
- **Image location**: ECR tenant-management-frontend repository

## Troubleshooting

**If workflow fails:**
1. Check AWS credentials are correct in GitHub Secrets
2. Ensure eksadmin user has ECR push permissions
3. Verify EKS cluster access (update-kubeconfig permissions)
4. Review workflow logs in Actions tab

**To manually trigger a build right now:**
1. Commit and push this workflow file
2. Go to GitHub Actions tab
3. Click "Run workflow" button
