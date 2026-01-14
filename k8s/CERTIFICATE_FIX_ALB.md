# Certificate Fix: Switch to ALB for ACM Integration

## Problem
- NLB in TCP mode cannot terminate TLS with ACM certificates
- Istio Gateway expects Kubernetes TLS secret, but ACM certs cannot be exported
- Current setup shows self-signed certificate instead of ACM cert

## Solution: Switch to Application Load Balancer (ALB)

### Certificate Details
- **ARN**: `arn:aws:acm:ap-south-1:122610483530:certificate/bcbac6f5-c195-4e31-926e-0e50c7faa7dc`
- **Domain**: mrtmcloud.com
- **SANs**: 
  - mrtmcloud.com
  - *.mrtmcloud.com (covers governance.mrtmcloud.com ✅)
  - *.demo.pm.mrtmcloud.com
  - *.release.comviva.mrtmcloud.com
  - *.comviva.demo.mrtmcloud.com
  - *.pm.demo.mrtmcloud.com
  - *.ext.pm.mrtmcloud.com

### Steps to Fix

#### 1. Install AWS Load Balancer Controller
```bash
# Add helm repo
helm repo add eks https://aws.github.io/eks-charts
helm repo update

# Create IAM policy for ALB controller
curl -o iam_policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.7.1/docs/install/iam_policy.json

aws iam create-policy \
    --policy-name AWSLoadBalancerControllerIAMPolicy \
    --policy-document file://iam_policy.json

# Create IAM service account
eksctl create iamserviceaccount \
  --cluster=your-cluster-name \
  --namespace=kube-system \
  --name=aws-load-balancer-controller \
  --attach-policy-arn=arn:aws:iam::122610483530:policy/AWSLoadBalancerControllerIAMPolicy \
  --override-existing-serviceaccounts \
  --approve

# Install controller
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=your-cluster-name \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller
```

#### 2. Create ALB Ingress with ACM Certificate
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tenant-management-ingress
  namespace: istio-system
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:ap-south-1:122610483530:certificate/bcbac6f5-c195-4e31-926e-0e50c7faa7dc
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS":443}]'
    alb.ingress.kubernetes.io/ssl-redirect: '443'
spec:
  rules:
  - host: governance.mrtmcloud.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: istio-ingressgateway
            port:
              number: 80
```

#### 3. Update DNS
After ALB is created, update Route53:
```bash
# Get ALB DNS name
kubectl get ingress -n istio-system tenant-management-ingress

# Update Route53 A record for governance.mrtmcloud.com
# Point to the ALB DNS name
```

### Alternative: Keep NLB + Upload Certificate to Istio

If you want to keep NLB, you need to:
1. Get certificate and private key from your CA
2. Create Kubernetes TLS secret manually

This is NOT recommended if certificate is from ACM (cannot export).

### Benefits of ALB
- ✅ Native ACM certificate integration
- ✅ HTTPS termination at load balancer
- ✅ No certificate management in Kubernetes
- ✅ Multiple certificates with SNI support
- ✅ Web Application Firewall (WAF) integration
- ✅ Path-based routing capabilities

### Why Current Setup Fails
1. NLB runs TCP mode (no TLS termination)
2. Istio Gateway expects `tenant-management-tls` secret
3. Secret doesn't exist → Istio generates self-signed cert
4. Browser sees self-signed cert → "Not Secure" warning

## Quick Decision

**Do you want to**:
- **Option A**: Switch to ALB (recommended, uses ACM natively)
- **Option B**: Manually upload certificate to Istio (requires exportable cert, NOT possible with ACM)
