#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== HTTPS Setup for Tenant Management System ===${NC}\n"

# Configuration
REGION="ap-south-1"
NAMESPACE="tenant-management"
DOMAIN="governance.mrtmcloud.com"

# Function to print colored messages
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if kubectl is configured
if ! kubectl cluster-info &> /dev/null; then
    print_error "kubectl is not configured or cluster is not accessible"
    exit 1
fi

print_info "Cluster is accessible"

# List available ACM certificates
print_info "Listing available ACM certificates..."
echo ""
aws acm list-certificates --region $REGION --output table

echo ""
echo -e "${YELLOW}Please choose an option:${NC}"
echo "1. Use existing ACM certificate (enter ARN)"
echo "2. Request new certificate for $DOMAIN"
echo "3. Exit"
read -p "Enter choice (1-3): " choice

CERT_ARN=""

case $choice in
    1)
        read -p "Enter the ACM Certificate ARN: " CERT_ARN
        
        # Validate certificate exists
        print_info "Validating certificate..."
        if aws acm describe-certificate --certificate-arn "$CERT_ARN" --region $REGION &> /dev/null; then
            print_info "Certificate validated successfully"
            
            # Show certificate details
            aws acm describe-certificate --certificate-arn "$CERT_ARN" --region $REGION \
                --query 'Certificate.{Domain:DomainName,Status:Status,Expiry:NotAfter}' --output table
        else
            print_error "Invalid certificate ARN or certificate not found"
            exit 1
        fi
        ;;
    2)
        print_warning "You need ACM permissions to request certificates"
        read -p "Domain name for certificate (e.g., *.mrtmcloud.com): " CERT_DOMAIN
        
        print_info "Requesting certificate for $CERT_DOMAIN..."
        
        CERT_ARN=$(aws acm request-certificate \
            --domain-name "$CERT_DOMAIN" \
            --subject-alternative-names "$DOMAIN" \
            --validation-method DNS \
            --region $REGION \
            --output text --query 'CertificateArn')
        
        if [ $? -eq 0 ]; then
            print_info "Certificate requested successfully"
            print_info "ARN: $CERT_ARN"
            print_warning "You need to validate the certificate by adding DNS records"
            print_warning "Run: aws acm describe-certificate --certificate-arn $CERT_ARN --region $REGION"
            echo ""
            read -p "Press Enter after you've validated the certificate..."
        else
            print_error "Failed to request certificate"
            exit 1
        fi
        ;;
    3)
        print_info "Exiting..."
        exit 0
        ;;
    *)
        print_error "Invalid choice"
        exit 1
        ;;
esac

# Get current load balancer DNS
print_info "Getting current load balancer information..."
LB_DNS=$(kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
print_info "Current Load Balancer DNS: $LB_DNS"

# Update Istio Ingress Gateway Service with SSL certificate
print_info "Updating Istio Ingress Gateway service with SSL certificate..."

kubectl patch svc istio-ingressgateway -n istio-system -p '{
  "metadata": {
    "annotations": {
      "service.beta.kubernetes.io/aws-load-balancer-ssl-cert": "'$CERT_ARN'",
      "service.beta.kubernetes.io/aws-load-balancer-ssl-ports": "443",
      "service.beta.kubernetes.io/aws-load-balancer-backend-protocol": "tcp"
    }
  }
}'

if [ $? -eq 0 ]; then
    print_info "Service updated successfully"
else
    print_error "Failed to update service"
    exit 1
fi

# Apply updated Istio Gateway
print_info "Applying updated Istio Gateway configuration..."
kubectl apply -f k8s/eks-manifests/07-istio-gateway.yaml

# Wait for load balancer to update
print_info "Waiting for load balancer to update (this may take 2-5 minutes)..."
sleep 10

for i in {1..30}; do
    echo -n "."
    sleep 10
done
echo ""

# Get updated load balancer DNS
NEW_LB_DNS=$(kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
print_info "Load Balancer DNS: $NEW_LB_DNS"

# Check if DNS update is needed
print_info "Checking DNS configuration..."
CURRENT_DNS=$(dig +short $DOMAIN | head -n 1)

if [ "$CURRENT_DNS" != "$NEW_LB_DNS" ]; then
    print_warning "DNS is not pointing to the load balancer"
    print_warning "Current DNS: $CURRENT_DNS"
    print_warning "Expected DNS: $NEW_LB_DNS"
    echo ""
    echo "Please update your DNS records:"
    echo "  Type: CNAME"
    echo "  Name: governance"
    echo "  Value: $NEW_LB_DNS"
    echo ""
else
    print_info "DNS is correctly configured"
fi

# Test HTTP endpoint
print_info "Testing HTTP endpoint..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://$DOMAIN/tm/health || echo "000")
if [ "$HTTP_STATUS" = "200" ]; then
    print_info "HTTP endpoint is working (Status: $HTTP_STATUS)"
else
    print_warning "HTTP endpoint returned status: $HTTP_STATUS"
fi

# Test HTTPS endpoint
print_info "Testing HTTPS endpoint..."
sleep 5
HTTPS_STATUS=$(curl -k -s -o /dev/null -w "%{http_code}" https://$DOMAIN/tm/health || echo "000")
if [ "$HTTPS_STATUS" = "200" ]; then
    print_info "HTTPS endpoint is working (Status: $HTTPS_STATUS)"
else
    print_warning "HTTPS endpoint returned status: $HTTPS_STATUS"
    print_warning "This is expected if DNS is not updated yet or certificate is still validating"
fi

# Display summary
echo ""
echo -e "${GREEN}=== Setup Summary ===${NC}"
echo "Certificate ARN: $CERT_ARN"
echo "Load Balancer: $NEW_LB_DNS"
echo "Domain: $DOMAIN"
echo "HTTP Status: $HTTP_STATUS"
echo "HTTPS Status: $HTTPS_STATUS"
echo ""

# Optional: Enable HTTPS redirect
echo ""
read -p "Do you want to force HTTPS redirect (redirect all HTTP to HTTPS)? (y/n): " enable_redirect

if [ "$enable_redirect" = "y" ] || [ "$enable_redirect" = "Y" ]; then
    print_info "Enabling HTTPS redirect..."
    
    # Update Gateway with HTTPS redirect
    kubectl patch gateway tenant-management-gateway -n $NAMESPACE --type='json' -p='[
      {
        "op": "add",
        "path": "/spec/servers/0/tls",
        "value": {"httpsRedirect": true}
      }
    ]'
    
    print_info "HTTPS redirect enabled"
fi

echo ""
print_info "HTTPS setup completed!"
print_info "Access your application at: https://$DOMAIN/tm/"
echo ""
print_warning "If HTTPS is not working yet:"
echo "  1. Wait for DNS propagation (5-10 minutes)"
echo "  2. Verify certificate is validated in ACM console"
echo "  3. Check load balancer listeners are configured correctly"
echo ""
print_info "For troubleshooting, see: k8s/HTTPS_SETUP.md"
