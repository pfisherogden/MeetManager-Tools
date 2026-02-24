# MeetManager Web Client

A generic Next.js application for visualizing Swim Meet data.

## Features
- **Modern UI**: Built with Next.js 16, Tailwind CSS v4, and Shadcn/UI.
- **Tailwind CSS v4**: Uses the latest `@theme inline` syntax in `globals.css` for enhanced performance and seamless Shadcn integration.
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

## Troubleshooting

### Build Failures (Out of Memory)
If the build fails with an "OOM" (Out of Memory) error in Docker or local environments, set the Node heap size:
```bash
export NODE_OPTIONS="--max-old-space-size=4096"
```

### Tailwind v4 Issues
Ensure `globals.css` uses the `@theme inline` block to expose CSS variables to the compiler. Ad-hoc utility classes may fail if not defined in the theme.

### Docker
The application is containerized to handle proto generation and build steps automatically.
```bash
docker-compose up frontend
```
