# System Diagrams

This document contains the architecture and interaction diagrams for the MeetManager-Tools project, covering both local and cloud deployment scenarios.

## 1. System Architecture

The following diagram illustrates the components and data flow for both local (Docker-based) and cloud (GCP Cloud Run) environments.

```dot
digraph Architecture {
    rankdir=LR;
    node [shape=box, style=filled, fillcolor=lightblue];

    subgraph cluster_local {
        label = "Local Deployment";
        style=dashed;
        color=grey;
        
        Director [label="Meet Director
(Browser)"];
        JudgeLocal [label="Judge
(Mobile App)"];
        WebClientLocal [label="Next.js Web Client
(Docker:8080)"];
        BackendLocal [label="Python gRPC Backend
(Docker:8081)"];
        StorageLocal [label="Local Filesystem
(.mdb / .json)"];
        
        Director -> WebClientLocal;
        JudgeLocal -> BackendLocal [label="gRPC"];
        WebClientLocal -> BackendLocal [label="gRPC-Web"];
        BackendLocal -> StorageLocal [label="File I/O"];
    }

    subgraph cluster_cloud {
        label = "Cloud Deployment (GCP)";
        style=dashed;
        color=blue;
        
        UserCloud [label="Users
(Web/Mobile)"];
        LB [label="Cloud Run Load Balancer", fillcolor=orange];
        FrontendCloud [label="Frontend Service
(Cloud Run)"];
        BackendCloud [label="Backend Service
(Cloud Run)"];
        GCS [label="Google Cloud Storage
(Sandboxed Buckets)", fillcolor=lightgreen];
        FirebaseAuth [label="Firebase Auth", fillcolor=yellow];
        
        UserCloud -> LB;
        LB -> FrontendCloud;
        LB -> BackendCloud;
        FrontendCloud -> FirebaseAuth [label="Verify Session"];
        BackendCloud -> FirebaseAuth [label="Verify JWT"];
        FrontendCloud -> BackendCloud [label="gRPC-Web"];
        BackendCloud -> GCS [label="Blob API"];
    }
}
```

## 2. Core Interaction: DQ Entry (Sync)

This sequence diagram shows how a DQ entry is recorded in the mobile app and synchronized with the backend, including authentication and user-sandboxed storage.

```mermaid
sequenceDiagram
    participant Judge as Judge (Mobile App)
    participant Backend as Backend (Cloud Run / Local)
    participant Auth as Auth (Firebase / Mock)
    participant Storage as Storage (GCS / Local)

    Note over Judge: Offline Mode Supported
    Judge->>Judge: Record DQ (Lane 4, Code 1A)
    Judge->>Judge: Add to Offline Queue

    Note over Judge, Backend: Network Available
    Judge->>Auth: Get Identity Token
    Auth-->>Judge: JWT Token
    
    Judge->>Backend: SyncDQ(DQEntry, Token)
    
    rect rgb(240, 240, 240)
        Note right of Backend: gRPC Interceptor
        Backend->>Auth: Verify Token
        Auth-->>Backend: UserID (e.g., "org_123")
    end
    
    Backend->>Storage: Save DQ to Dataset (org_123/meet_x/dqs.json)
    Storage-->>Backend: Success
    
    Backend-->>Judge: SyncResponse (Success)
    Judge->>Judge: Clear Entry from Queue
```
