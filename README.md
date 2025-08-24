# Digital Freight Platform

A comprehensive microservices-based platform for managing sea and air freight operations with dynamic pricing, real-time tracking, and document management.

## 🚀 Features

### Core Capabilities
- **Dynamic Pricing Engine** - Real-time quote calculation with configurable rules
- **Quote Management** - PDF generation, acceptance workflow, validity tracking
- **Shipment Tracking** - Real-time milestone updates and status management
- **Document Management** - Secure upload, storage, and retrieval with checksums
- **Multi-Channel Notifications** - Email, SMS, and push notifications
- **Customer Relationship Management** - Customer profiles and interaction history
- **Vendor Management** - Carrier registry with performance KPIs
- **Analytics & Reporting** - Business intelligence and operational metrics

### Technical Features
- **Microservices Architecture** - 6 independent, scalable services
- **Event-Driven Integration** - Kafka-based messaging for loose coupling
- **High Availability** - Multi-replica deployments with automatic failover
- **Security** - OIDC authentication, RBAC authorization, audit trails
- **Performance** - Redis caching, optimized database queries, async processing
- **Observability** - Comprehensive monitoring, logging, and tracing

## 🏗️ Architecture

### Service Overview

```mermaid
graph TB
    subgraph "Frontend Layer"
        WEB[Web Application]
        API[API Gateway]
    end
    
    subgraph "Service Layer"
        QS[Quotation Service]
        BS[Booking Service]
        CS[CRM Service]
        VS[Vendor Service]
        NS[Notification Service]
        AS[Analytics Service]
    end
    
    subgraph "Data Layer"
        PG[(PostgreSQL)]
        RD[(Redis)]
        MO[(MinIO)]
        KF[(Kafka)]
    end
    
    WEB --> API
    API --> QS
    API --> BS
    API --> CS
    API --> VS
    
    QS --> PG
    QS --> RD
    QS --> MO
    QS --> KF
    
    BS --> PG
    BS --> KF
    
    NS --> KF
    AS --> KF
    AS --> MO
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Backend Framework** | Flask 3.1+ | REST API development |
| **Database** | PostgreSQL 16 | Primary data storage |
| **Cache** | Redis 7 | Performance optimization |
| **Message Broker** | Redpanda | Event streaming |
| **Object Storage** | MinIO | Document storage |
| **Container Runtime** | Docker | Application packaging |
| **Orchestration** | Kubernetes | Container management |
| **Monitoring** | Prometheus + Grafana | Observability |

## 🚦 Quick Start

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- Python 3.11+ (for development)
- kubectl (for Kubernetes deployment)
- Helm 3.0+ (for production deployment)

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/freight-platform.git
   cd freight-platform
   ```

2. **Start infrastructure services**
   ```bash
   cd deployment/docker
   docker-compose up -d postgres redis minio redpanda
   ```

3. **Wait for services to be ready**
   ```bash
   # Check service health
   docker-compose ps
   
   # Wait for all services to show "healthy"
   ```

4. **Set up the quotation service**
   ```bash
   cd services/quotation/quotation-service
   
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Initialize database
   python src/init_db.py
   
   # Start the service
   python src/main.py
   ```

5. **Verify the setup**
   ```bash
   # Check service health
   curl http://localhost:8101/health
   
   # Create a test quote
   curl -X POST http://localhost:8101/api/v1/quotes \
     -H "Content-Type: application/json" \
     -d '{
       "mode": "SEA",
       "service": "FCL",
       "origin": "SGSIN",
       "destination": "EGALY",
       "containers": [{"type": "40HC", "count": 1}],
       "cargo": {"weightKg": 8200, "volumeM3": 58},
       "accessorials": ["FUEL", "PORT_FEES"]
     }'
   ```

### Using Docker Compose (Recommended for Development)

1. **Start all services**
   ```bash
   cd deployment/docker
   docker-compose up -d
   ```

2. **View logs**
   ```bash
   # All services
   docker-compose logs -f
   
   # Specific service
   docker-compose logs -f quotation-service
   ```

3. **Access services**
   - Quotation API: http://localhost:8101
   - MinIO Console: http://localhost:9001 (admin/admin)
   - Redpanda Console: http://localhost:8080

## 📚 API Documentation

### Quotation Service API

The quotation service provides dynamic pricing and quote management capabilities.

#### Create Quote
```bash
POST /api/v1/quotes
Content-Type: application/json

{
  "mode": "SEA",
  "service": "FCL",
  "origin": "SGSIN",
  "destination": "EGALY",
  "containers": [{"type": "40HC", "count": 1}],
  "cargo": {"weightKg": 8200, "volumeM3": 58},
  "accessorials": ["FUEL", "PORT_FEES"],
  "customer_id": "CUST123"
}
```

#### Get Quote
```bash
GET /api/v1/quotes/{quote_id}
```

#### Accept Quote
```bash
PUT /api/v1/quotes/{quote_id}/accept
```

#### Get Quote PDF
```bash
GET /api/v1/quotes/{quote_id}/pdf
```

### Complete API Documentation

- **OpenAPI Specification**: [docs/api/quotation.yaml](docs/api/quotation.yaml)
- **AsyncAPI Specification**: [docs/asyncapi/events.yaml](docs/asyncapi/events.yaml)
- **Interactive Documentation**: Available at `/docs` endpoint when services are running

## 🔧 Configuration

### Environment Variables

#### Database Configuration
```bash
DATABASE_URL=postgresql://freight:freight@localhost:5432/freight_db
```

#### Redis Configuration
```bash
REDIS_URL=redis://localhost:6379/0
```

#### MinIO Configuration
```bash
OBJECT_STORE_ENDPOINT=localhost:9000
OBJECT_STORE_ACCESS_KEY=minioadmin
OBJECT_STORE_SECRET_KEY=minioadmin
OBJECT_STORE_SECURE=false
OBJECT_STORE_BUCKET=freight-docs
```

#### Kafka Configuration
```bash
KAFKA_BROKERS=localhost:9092
```

#### Service Configuration
```bash
SERVICE_NAME=quotation-service
SERVICE_VERSION=1.0.0
FLASK_ENV=development
LOG_LEVEL=INFO
AUTH_ENABLED=false
```

### Configuration Files

- **Docker Compose**: [deployment/docker/docker-compose.yml](deployment/docker/docker-compose.yml)
- **Kubernetes Manifests**: [deployment/k8s/manifests/](deployment/k8s/manifests/)
- **Helm Values**: [deployment/k8s/helmfile/values/](deployment/k8s/helmfile/values/)

## 🚀 Production Deployment

### Kubernetes Deployment

1. **Create namespace**
   ```bash
   kubectl apply -f deployment/k8s/manifests/namespace.yaml
   ```

2. **Deploy infrastructure using Helmfile**
   ```bash
   cd deployment/k8s/helmfile
   helmfile sync
   ```

3. **Deploy application services**
   ```bash
   kubectl apply -f ../manifests/config-secrets.yaml
   kubectl apply -f ../manifests/quotation-service.yaml
   kubectl apply -f ../manifests/ingress.yaml
   ```

4. **Verify deployment**
   ```bash
   kubectl get pods -n freight-platform
   kubectl get services -n freight-platform
   kubectl get ingress -n freight-platform
   ```

### High Availability Setup

The platform supports high availability deployment with:

- **Database**: PostgreSQL with streaming replication (3 replicas)
- **Cache**: Redis Sentinel for automatic failover (3 nodes)
- **Message Broker**: Redpanda cluster with replication (3+ nodes)
- **Object Storage**: MinIO distributed mode (4+ nodes)
- **Application Services**: Multiple replicas with load balancing

## 📊 Monitoring & Observability

### Health Checks

All services provide health and readiness endpoints:

- **Health**: `/health` - Basic service health
- **Readiness**: `/ready` - Service readiness including dependencies
- **Metrics**: `/metrics` - Prometheus metrics

### Monitoring Stack

1. **Start monitoring services**
   ```bash
   docker-compose --profile monitoring up -d
   ```

2. **Access monitoring dashboards**
   - Prometheus: http://localhost:9090
   - Grafana: http://localhost:3000 (admin/admin)

### Key Metrics

- **Request Rate**: Requests per second by service and endpoint
- **Response Time**: p50, p95, p99 latencies
- **Error Rate**: 4xx and 5xx error percentages
- **Database Performance**: Query time, connection pool usage
- **Cache Hit Rate**: Redis cache effectiveness
- **Message Queue**: Kafka lag, throughput, partition distribution

## 🧪 Testing

### Unit Tests

```bash
cd services/quotation/quotation-service
source venv/bin/activate
python -m pytest tests/unit/
```

### Integration Tests

```bash
# Start test environment
docker-compose -f docker-compose.test.yml up -d

# Run integration tests
python -m pytest tests/integration/

# Cleanup
docker-compose -f docker-compose.test.yml down
```

### Load Testing

```bash
# Install k6
# See: https://k6.io/docs/getting-started/installation/

# Run load tests
k6 run tests/load/quotation_load_test.js
```

### Test Coverage

```bash
python -m pytest --cov=src tests/
```

## 🔒 Security

### Authentication & Authorization

The platform uses OIDC (OpenID Connect) for authentication with role-based access control:

#### Roles
- **Admin**: Full system access
- **Operations**: Manage shipments and vendors
- **Sales**: Manage quotes and customers  
- **Customer**: View own data only

#### API Security
- JWT token authentication
- Rate limiting (100 req/min per IP)
- Input validation and sanitization
- CORS configuration
- Request/response logging

### Security Best Practices

1. **Never commit secrets** - Use environment variables
2. **Use HTTPS** - TLS encryption for all communications
3. **Regular updates** - Keep dependencies updated
4. **Audit logs** - Track all user actions
5. **Network security** - Use firewalls and network policies

## 📈 Performance

### SLA Targets

| Operation | Target | Measurement |
|-----------|--------|-------------|
| Quote Creation | p95 ≤ 2s (cached), ≤ 5s (cold) | Response time |
| Quote Retrieval | p95 ≤ 300ms | Response time |
| Booking Confirmation | ≤ 30s | End-to-end time |
| Milestone Updates | ≤ 60s | Event processing time |
| Notification Delivery | 99% ≤ 60s | Delivery time |
| System Availability | 99.9% | Uptime |

### Performance Optimization

1. **Database Optimization**
   - Proper indexing on frequently queried columns
   - Connection pooling with pgbouncer
   - Query optimization and EXPLAIN analysis

2. **Caching Strategy**
   - Redis for frequently accessed data
   - Application-level caching for pricing rules
   - CDN for static assets

3. **Async Processing**
   - Background jobs for PDF generation
   - Event-driven architecture for loose coupling
   - Message queuing for reliable processing

## 🛠️ Development

### Project Structure

```
freight-platform/
├── services/                 # Microservices
│   ├── quotation/           # Quotation service
│   ├── booking/             # Booking service (placeholder)
│   ├── crm/                 # CRM service (placeholder)
│   ├── vendor/              # Vendor service (placeholder)
│   ├── notify/              # Notification service (placeholder)
│   └── analytics/           # Analytics service (placeholder)
├── shared/                  # Shared libraries
│   ├── config.py           # Common Flask configuration
│   ├── database.py         # Database utilities
│   ├── cache.py            # Redis cache wrapper
│   ├── storage.py          # MinIO storage utilities
│   ├── events.py           # Kafka event handling
│   └── auth.py             # Authentication middleware
├── deployment/              # Deployment configurations
│   ├── docker/             # Docker Compose files
│   └── k8s/                # Kubernetes manifests
├── docs/                   # Documentation
│   ├── api/                # OpenAPI specifications
│   ├── asyncapi/           # AsyncAPI specifications
│   └── adr/                # Architecture Decision Records
└── scripts/                # Utility scripts
```

### Adding a New Service

1. **Create service directory**
   ```bash
   mkdir -p services/new-service
   cd services/new-service
   manus-create-flask-app new-service
   ```

2. **Update shared dependencies**
   ```bash
   # Add shared libraries to requirements.txt
   echo "../../../shared" >> requirements.txt
   ```

3. **Implement service logic**
   - Follow the quotation service pattern
   - Use shared libraries for common functionality
   - Implement health and metrics endpoints

4. **Add to Docker Compose**
   ```yaml
   new-service:
     build:
       context: ../../services/new-service
     environment:
       - DATABASE_URL=postgresql://freight:freight@postgres:5432/freight_db
     ports:
       - "8107:8107"
   ```

5. **Create Kubernetes manifests**
   - Follow the quotation service pattern
   - Add deployment, service, and HPA configurations

### Code Style

- **Python**: Follow PEP 8 with Black formatter
- **Documentation**: Comprehensive docstrings and type hints
- **Testing**: Minimum 80% code coverage
- **Logging**: Structured JSON logging with correlation IDs

### Git Workflow

1. **Feature branches**: `feature/description`
2. **Pull requests**: Required for all changes
3. **Code review**: At least one approval required
4. **CI/CD**: Automated testing and deployment

## 🤝 Contributing

### Getting Started

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

### Development Guidelines

- Follow the existing code style and patterns
- Write comprehensive tests
- Update documentation for new features
- Use meaningful commit messages
- Keep pull requests focused and small

### Reporting Issues

Please use GitHub Issues to report bugs or request features. Include:

- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Environment details
- Relevant logs or screenshots

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Documentation
- [API Documentation](docs/api/)
- [Architecture Decisions](docs/adr/)
- [Deployment Guide](docs/deployment.md)

### Community
- GitHub Issues: Bug reports and feature requests
- GitHub Discussions: Questions and community support
- Email: platform-support@freightplatform.com

### Commercial Support
For enterprise support, training, and consulting services, contact:
- Email: enterprise@freightplatform.com
- Website: https://freightplatform.com/support

---

**Built with ❤️ by the Freight Platform Team**

