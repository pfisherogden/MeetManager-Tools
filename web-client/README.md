# MeetManager Web Client

A generic Next.js application for visualizing Swim Meet data.

## Features
- **Modern UI**: Built with Next.js 14, Tailwind CSS, and Shadcn/UI.
- **Data Browsing**: Interactive tables for Meets, Teams, Athletes, and Results.
- **Admin Console**: Interface for uploading and managing datasets.
- **gRPC Integration**: Communicates with the Backend via `grpc-js`.

## Development

### Prerequisites
- Node.js 18+ (Node 20 recommended)

### Installation
```bash
cd web-client
npm install
```

### Running Locally
```bash
npm run dev
```

### Docker
The application is containerized to handle proto generation and build steps automatically.
```bash
docker-compose up frontend
```
