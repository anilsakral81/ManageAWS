# Kubernetes Tenant Management Portal

A web-based GUI application for managing AWS EKS-based SaaS tenants across multiple Kubernetes namespaces.

## Features

- 🚀 **Start/Stop Tenants**: Scale deployments between 0 and 1 replicas
- ⏰ **Scheduled Operations**: Configure periodic tenant shutdowns and startups
- 🔐 **Keycloak Authentication**: Secure OIDC-based user authentication
- 👥 **Role-Based Access**: Fine-grained permissions for tenant management
- 📊 **Audit Logging**: Complete history of all tenant operations
- 🎯 **Namespace Isolation**: Secure multi-tenant architecture

## Technology Stack

### Backend
- **FastAPI**: High-performance Python web framework
- **SQLAlchemy**: ORM for database operations
- **PostgreSQL**: Persistent data storage
- **Kubernetes Python Client**: K8s API interaction
- **APScheduler**: Task scheduling engine
- **python-keycloak**: Keycloak integration

### Frontend
- **React 18**: UI library
- **TypeScript**: Type-safe JavaScript
- **Vite**: Fast build tool
- **Material-UI (MUI)**: UI component library
- **React Query**: Server state management
- **Keycloak JS**: Frontend authentication

### Infrastructure
- **Docker**: Containerization
- **Kubernetes**: Orchestration platform
- **Helm**: Package manager for K8s
- **AWS EKS**: Managed Kubernetes service

## Project Structure

```
ManageAWS/
├── backend/              # FastAPI backend application
│   ├── app/
│   │   ├── api/         # API routes
│   │   ├── models/      # Database models
│   │   ├── schemas/     # Pydantic schemas
│   │   ├── services/    # Business logic
│   │   └── auth/        # Authentication logic
│   ├── tests/           # Backend tests
│   └── requirements.txt
│
├── frontend/            # React frontend application
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── pages/       # Page components
│   │   ├── services/    # API services
│   │   └── contexts/    # React contexts
│   └── package.json
│
├── k8s/                 # Kubernetes manifests
│   ├── namespace.yaml
│   ├── serviceaccount.yaml
│   └── rbac.yaml
│
└── helm-chart/          # Helm deployment chart
    ├── Chart.yaml
    ├── values.yaml
    └── templates/
```

## Prerequisites

- Docker and Docker Compose
- kubectl configured for your EKS cluster
- Helm 3.x
- Node.js 18+ (for frontend development)
- Python 3.11+ (for backend development)
- Access to Keycloak instance

## Quick Start (Local Development)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ManageAWS
   ```

2. **Configure environment variables**
   ```bash
   cp backend/.env.example backend/.env
   # Edit backend/.env with your configuration
   ```

3. **Start services with Docker Compose**
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## Deployment to Kubernetes

1. **Create namespace**
   ```bash
   kubectl apply -f k8s/namespace.yaml
   ```

2. **Configure RBAC**
   ```bash
   kubectl apply -f k8s/serviceaccount.yaml
   kubectl apply -f k8s/rbac.yaml
   ```

3. **Deploy using Helm**
   ```bash
   helm install tenant-portal ./helm-chart \
     --namespace management-portal \
     --set keycloak.url=https://your-keycloak.example.com \
     --set keycloak.realm=saas-management \
     --set keycloak.clientId=tenant-management-portal
   ```

## Configuration

### Keycloak Setup

1. Create a new realm: `saas-management`
2. Create a client: `tenant-management-portal`
3. Define roles:
   - `tenant-admin`: Full tenant management
   - `tenant-operator`: Start/stop operations
   - `tenant-viewer`: Read-only access
4. Assign roles to users

### Environment Variables

See `backend/.env.example` for all configuration options.

## Security Considerations

- ServiceAccount with minimal RBAC permissions
- IRSA (IAM Roles for Service Accounts) for AWS integration
- JWT token validation for all API requests
- Network policies for namespace isolation
- Audit logging for compliance

## Development

### Backend Development
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend Development
```bash
cd frontend
npm install
npm run dev
```

### Running Tests
```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## License

MIT

## Support

For issues and questions, please open a GitHub issue.
