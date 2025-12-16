# Architecture Diagram Requirements - AutoPredict Platform

## Form Answers for Architecture Generation

### Question 1: Level of Detail
**Answer: "A balance between overview and some key subcomponents"**

**Rationale**: 
- Show service names clearly
- Include key subcomponents for critical services (Orchestration with Master/Worker agents, ML with RF+LSTM, UEBA with Isolation Forest)
- Keep infrastructure components at high-level (databases, message queues)

### Question 2: Communication Patterns
**Selected Options:**
- ✅ **Asynchronous messaging via Kafka** (Critical - telemetry streaming)
- ✅ **WebSocket real-time communication** (Dashboard live updates)
- ✅ **Synchronous REST API calls** (Primary API communication)
- ✅ **Batch data transfers** (Model training, historical analytics)

**Additional Details:**
- REST API: FastAPI endpoints for all service interactions
- Kafka: Real-time telemetry ingestion from IoT devices
- WebSocket: Live dashboard updates for risk scores and alerts
- Batch: Scheduled model retraining, historical data processing

### Question 3: User Roles/Personas
**Answer:**
```
Primary Users:
1. Fleet Managers - Monitor vehicle health, schedule maintenance via dashboard
2. Technicians - Receive maintenance assignments, update work status
3. Manufacturing Quality Engineers - Review defect patterns, CAPA recommendations
4. System Administrators - Monitor system health, configure agents
5. Data Scientists - Review ML model performance, retrain models

User Journey Highlights:
- Fleet Manager: Dashboard → Risk Alerts → Schedule Maintenance → Track Status
- Technician: Mobile App → Receive Assignment → Complete Work → Update System
- Quality Engineer: Manufacturing Dashboard → Defect Heatmaps → CAPA Actions → Track Improvements
```

### Question 4: Deployment Environment Details
**Answer: "Yes, include deployment environment details"**

**Details to Include:**
- **Cloud Provider**: Microsoft Azure (primary)
- **Container Orchestration**: Kubernetes (for production scaling)
- **Container Runtime**: Docker containers for all services
- **CI/CD**: GitHub Actions → Build → Test → Deploy to Azure AKS
- **Regions**: Multi-region deployment (Primary: East US, Secondary: West Europe)
- **Load Balancing**: Azure Application Gateway
- **Auto-scaling**: Kubernetes HPA based on CPU/memory metrics
- **Service Mesh**: Istio (for service-to-service communication, security)

### Question 5: Performance, Scalability, Security Considerations
**Answer:**
```
PERFORMANCE:
- Real-time inference: <100ms latency for ML predictions
- Telemetry processing: 10,000+ events/second via Kafka
- Dashboard updates: <500ms via WebSocket
- Batch processing: Parallel model training on GPU clusters

SCALABILITY:
- Horizontal scaling: All services stateless, scale independently
- Database sharding: TimescaleDB partitioned by vehicle fleet
- Caching layer: Redis for frequently accessed data (risk scores, agent decisions)
- CDN: Azure CDN for static frontend assets

SECURITY (Visual Emphasis):
- UEBA Guard: Red-highlighted security layer blocking risky actions
- API Gateway: Authentication/Authorization (OAuth2, JWT tokens)
- Network isolation: VPC with private subnets for databases
- Encryption: TLS 1.3 for all communications, at-rest encryption for databases
- Audit trail: All agent decisions logged to Elasticsearch (immutable logs)
- Shadow Safety Twin: Parallel decision validation (highlight as security feature)
```

---

## Enhanced Architecture Prompt with All Requirements

Based on the form answers, here's the complete prompt:

---

**Create a production-grade system architecture diagram for an "Agentic AI-Driven Predictive Maintenance & Quality Intelligence Platform" that fits perfectly in a 16:9 slide (1920x1080px).**

### DETAIL LEVEL: Balance (Overview + Key Subcomponents)

**Show at high-level:**
- Infrastructure components (databases, message queues)
- External services
- Network components

**Show with subcomponents:**
- **Orchestration Service**: Master Agent, Worker Agents (6 types), Shadow Safety Twin
- **ML Inference**: RF Model, LSTM Model, Fusion Layer
- **UEBA Engine**: Isolation Forest, Intent Graph, Guard Layer
- **Voice AI**: STT (Whisper), TTS (Azure), Sentiment Analysis

### COMMUNICATION PATTERNS (Show with different arrow styles):

1. **Synchronous REST API** (Solid blue arrows)
   - Client → API Gateway → Services
   - Service-to-service API calls

2. **Asynchronous Kafka** (Dashed green arrows)
   - IoT → Kafka → TimescaleDB
   - Event streaming between services

3. **WebSocket** (Wavy orange arrows)
   - WebSocket Server → Dashboard (real-time updates)

4. **Batch Processing** (Dotted gray arrows)
   - Scheduled jobs → Data Warehouse
   - Model training pipelines

### USER ROLES (Annotate in Client Layer):

- **Fleet Manager** (Web Dashboard)
- **Technician** (Mobile App)
- **Quality Engineer** (Manufacturing Dashboard)
- **System Admin** (Admin Panel)
- **Data Scientist** (ML Ops Dashboard)

### DEPLOYMENT ENVIRONMENT (Show as infrastructure layer):

**Top Section - Cloud Infrastructure:**
- **Azure Cloud** (container)
  - **Region 1: East US** (Primary)
    - Azure Kubernetes Service (AKS)
    - Application Gateway (Load Balancer)
  - **Region 2: West Europe** (Secondary/DR)
    - AKS (standby)

**Container Details:**
- Each service in its own container/pod
- Show Kubernetes deployment symbols
- Service mesh (Istio) overlay

**CI/CD Pipeline:**
- GitHub → GitHub Actions → Azure Container Registry → AKS
- Show as a small pipeline diagram on the side

### PERFORMANCE & SCALABILITY (Visual Annotations):

**Add callout boxes:**
- "Real-time: <100ms inference latency"
- "Scale: 10K+ events/sec via Kafka"
- "Auto-scaling: K8s HPA enabled"
- "Caching: Redis for hot data"

**Highlight with icons:**
- ⚡ Performance-critical paths
- 📈 Scalability components (Kafka, K8s)
- 🔄 Auto-scaling indicators

### SECURITY (Red/Purple Highlighting):

**Security Layers (Perimeter):**
1. **API Gateway** (Auth: OAuth2/JWT) - Purple border
2. **UEBA Guard** (Anomaly blocking) - Red highlight, prominent
3. **Network Security** (VPC, Firewall) - Dashed purple border
4. **Shadow Safety Twin** - Red callout: "Safety Validation"

**Security Annotations:**
- "TLS 1.3: All communications encrypted"
- "Audit: Immutable logs in Elasticsearch"
- "Guard: Blocks risky agent actions"

### LAYOUT STRUCTURE:

```
[CLOUD INFRASTRUCTURE - Top Banner]
Azure Cloud (East US + West Europe)
├── AKS Clusters
├── Application Gateway
└── CI/CD Pipeline

[CLIENT LAYER]
Fleet Manager | Technician | Quality Engineer | Admin | Data Scientist
    ↓
Web Dashboard | Mobile App | Manufacturing Dashboard | Admin Panel | ML Ops

[API GATEWAY LAYER]
API Gateway (OAuth2/JWT) → Load Balancer

[CORE SERVICES - Horizontal, with subcomponents]
[Orchestration] → [ML Inference] → [UEBA] → [Scheduler] → [Voice AI] → [Manufacturing]
  ├─Master        ├─RF Model      ├─Isolation   ├─OR-Tools   ├─Whisper    ├─KMeans
  ├─Workers       ├─LSTM          ├─Intent      └─Optimizer  ├─Azure TTS  ├─RCA
  └─Safety Twin   └─Fusion        └─Guard                    └─Sentiment  └─CAPA

[INFRASTRUCTURE LAYER]
Kafka (Streaming) | WebSocket Server | Redis Cache

[DATA LAYER]
TimescaleDB | PostgreSQL | Elasticsearch | Azure SQL | Vector DB

[EXTERNAL SERVICES]
Azure Cognitive | Azure Blob Storage | Monitoring (Prometheus/Grafana)
```

### COLOR SCHEME:
- **Blue**: Data/Storage
- **Green**: ML/AI Services
- **Orange**: APIs/Services
- **Purple**: Security Components
- **Red**: Critical Security (UEBA Guard, Safety Twin)
- **Gray**: Infrastructure
- **Yellow**: Performance/Scalability highlights

### ARROW STYLES:
- **Solid Blue**: REST API calls
- **Dashed Green**: Kafka async messaging
- **Wavy Orange**: WebSocket real-time
- **Dotted Gray**: Batch processing
- **Thick Red**: Security checks (Guard → Decision)

### ANNOTATIONS (Small callouts with icons):
- ⚡ "Real-time: <100ms"
- 📊 "Scale: 10K+ events/sec"
- 🔒 "TLS 1.3 encrypted"
- 🛡️ "UEBA Guard active"
- 🔄 "Auto-scaling enabled"
- ✅ "Shadow Twin validation"

### OUTPUT:
High-resolution PNG/SVG, 16:9 aspect ratio, professional styling, suitable for technical presentations to stakeholders, investors, or technical teams.

---

## Quick Reference for Form Filling

Copy these answers when filling out the architecture form:

**Q1**: A balance between overview and some key subcomponents

**Q2**: 
- ✅ Synchronous REST API calls
- ✅ Asynchronous messaging via Kafka
- ✅ WebSocket real-time communication
- ✅ Batch data transfers

**Q3**: 
Fleet Managers (dashboard monitoring), Technicians (mobile assignments), Quality Engineers (manufacturing analytics), System Admins (system configuration), Data Scientists (ML operations)

**Q4**: Yes, include deployment environment details (Azure, Kubernetes, multi-region, CI/CD)

**Q5**: 
Performance: <100ms inference, 10K+ events/sec. Scalability: Horizontal scaling, K8s auto-scaling, Redis caching. Security: UEBA Guard (highlighted), TLS encryption, OAuth2/JWT, Shadow Safety Twin validation, immutable audit logs.

