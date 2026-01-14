#!/bin/bash
# Script to request ACM certificate for governance.mrtmcloud.com
# Run this with an AWS account that has ACM permissions

set -e

REGION="ap-south-1"
DOMAIN="governance.mrtmcloud.com"

echo "Requesting ACM certificate for $DOMAIN..."

CERT_ARN=$(aws acm request-certificate \
  --domain-name "$DOMAIN" \
  --subject-alternative-names "*.mrtmcloud.com" "mrtmcloud.com" \
  --validation-method DNS \
  --region $REGION \
  --output text --query 'CertificateArn')

echo "Certificate requested successfully!"
echo "Certificate ARN: $CERT_ARN"
echo ""
echo "Next steps:"
echo "1. Add the DNS validation records shown below to your DNS provider"
echo ""

# Get validation details
aws acm describe-certificate \
  --certificate-arn "$CERT_ARN" \
  --region $REGION \
  --query 'Certificate.DomainValidationOptions[*].[DomainName,ResourceRecord.Name,ResourceRecord.Type,ResourceRecord.Value]' \
  --output table

echo ""
echo "2. Wait for validation (usually 5-30 minutes)"
echo "3. Check status with:"
echo "   aws acm describe-certificate --certificate-arn $CERT_ARN --region $REGION --query 'Certificate.Status'"
echo ""
echo "4. Once status is 'ISSUED', update the load balancer:"
echo "   ./k8s/apply-certificate.sh $CERT_ARN"
echo ""
echo "Save this ARN for later: $CERT_ARN"
