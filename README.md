# Marketing Intake Multi-Agent System

A sophisticated marketing intake system powered by multiple AI agents, Google Cloud Platform integration, and advanced workflow orchestration.

## 🚀 Features

- **Multi-Agent Architecture**: Web Crawler, Social Media, NLP, Map, Review, and Document agents
- **Google Cloud Integration**: VertexAI, Firestore, BigQuery, Cloud Run, and more
- **Intelligent Orchestration**: Smart agent selection and parallel execution
- **Real-time Processing**: Background workflow execution with status tracking
- **External Integrations**: Telegram, Discord, Reddit, and web scraping
- **Production Ready**: Docker containerization and CI/CD pipelines

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI       │    │   Google Cloud  │    │   AI Agents     │
│   Application   │◄──►│   Platform      │◄──►│   (6 Types)     │
│                 │    │                 │    │                 │
│ - Health Check  │    │ - VertexAI      │    │ - Web Crawler   │
│ - Intake API    │    │ - Firestore     │    │ - Social Media  │
│ - Status Track  │    │ - Cloud Run     │    │ - NLP Agent     │
│ - Background    │    │ - BigQuery      │    │ - Map Agent     │
│   Processing    │    │ - Secret Mgr    │    │ - Review Agent  │
└─────────────────┘    └─────────────────┘    │ - Doc Agent     │
                                             └─────────────────┘
```

## 📋 Prerequisites

### 1. Google Cloud Setup

1. **Create a Google Cloud Project**
   ```bash
   gcloud projects create your-project-id
   gcloud config set project your-project-id
   ```

2. **Enable Required APIs**
   ```bash
   gcloud services enable vertexai.googleapis.com
   gcloud services enable workflows.googleapis.com
   gcloud services enable cloudfunctions.googleapis.com
   gcloud services enable firestore.googleapis.com
   gcloud services enable bigquery.googleapis.com
   gcloud services enable customsearch.googleapis.com
   gcloud services enable maps-backend.googleapis.com
   gcloud services enable places-backend.googleapis.com
   gcloud services enable drive.googleapis.com
   gcloud services enable docs.googleapis.com
   gcloud services enable gmail.googleapis.com
   gcloud services enable calendar-json.googleapis.com
   ```

3. **Create Service Account**
   ```bash
   gcloud iam service-accounts create marketing-intake-api \
       --display-name="Marketing Intake API Service Account"

   gcloud projects add-iam-policy-binding your-project-id \
       --member="serviceAccount:marketing-intake-api@your-project-id.iam.gserviceaccount.com" \
       --role="roles/owner"
   ```

4. **Download Service Account Key**
   ```bash
   gcloud iam service-accounts keys create key.json \
       --iam-account=marketing-intake-api@your-project-id.iam.gserviceaccount.com
   ```

### 2. External Service Accounts

#### Telegram Bot
1. Message @BotFather on Telegram
2. Create new bot with `/newbot`
3. Copy the bot token

#### Discord Webhook
1. Go to Server Settings → Integrations → Webhooks
2. Create new webhook
3. Copy webhook URL

#### Google Custom Search API
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Enable Custom Search API
3. Create API key and Custom Search Engine

#### Reddit API (Optional)
1. Go to [Reddit Apps](https://www.reddit.com/prefs/apps)
2. Create app and copy client ID/secret

## 🔧 Installation & Setup

### 1. Clone and Setup

```bash
git clone <repository-url>
cd marketing-intake-system
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Copy `.env` and update values:
```bash
cp .env .env.local
# Edit .env.local with your actual values
```

Required environment variables:
```bash
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/key.json
OPENAI_API_KEY=your-openai-key
GOOGLE_CUSTOM_SEARCH_API_KEY=your-search-key
GOOGLE_CUSTOM_SEARCH_ENGINE_ID=your-engine-id
TELEGRAM_BOT_TOKEN=your-bot-token
DISCORD_WEBHOOK_URL=your-webhook-url
```

### 4. Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GOOGLE_APPLICATION_CREDENTIALS="path/to/key.json"
export GOOGLE_CLOUD_PROJECT="your-project-id"

# Run the application
python main.py
```

The API will be available at `http://localhost:8080`

## 🚀 Deployment

### Option 1: Google Cloud Run (Recommended)

```bash
# Build and deploy
gcloud builds submit --config deployment/cloudbuild.yaml .

# Or manually:
gcloud run deploy marketing-intake-api \
    --source . \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated
```

### Option 2: Google App Engine

```bash
# Deploy to App Engine
gcloud app deploy deployment/app.yaml
```

### Option 3: Local Docker

```bash
# Build image
docker build -f deployment/Dockerfile -t marketing-intake-api .

# Run container
docker run -p 8080:8080 \
    -e GOOGLE_CLOUD_PROJECT=your-project-id \
    -e GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json \
    marketing-intake-api
```

## 📖 API Usage

### Health Check
```bash
curl http://localhost:8080/health
```

### Submit Intake Request
```bash
curl -X POST http://localhost:8080/intake \
  -H "Content-Type: application/json" \
  -d '{
    "intake": {
      "campaign_name": "Summer Sale 2024",
      "target_audience": "dentists in Chennai",
      "budget": "$5000",
      "goals": ["increase leads", "brand awareness"],
      "platforms": ["Facebook", "Instagram"],
      "website": "https://example-dental.com"
    },
    "user_id": "user123",
    "priority": "high"
  }'
```

### Check Workflow Status
```bash
curl http://localhost:8080/status/your-request-id
```

### List Available Agents
```bash
curl http://localhost:8080/agents
```

## 🤖 Agent System

### Available Agents

1. **Web Crawler Agent** - Scrapes websites and extracts structured data
2. **Social Media Agent** - Analyzes social media presence and engagement
3. **NLP Agent** - Processes natural language and extracts insights
4. **Map Agent** - Handles location-based data and mapping
5. **Review Agent** - Collects and analyzes reviews and ratings
6. **Document Agent** - Processes documents and generates content

### Agent Execution Flow

1. **Intake Reception** - Request received via API
2. **Agent Selection** - Orchestrator determines which agents to run
3. **Parallel Execution** - Independent agents run simultaneously
4. **Dependency Resolution** - Dependent agents wait for prerequisites
5. **Result Aggregation** - All outputs combined into final result
6. **Storage & Notification** - Results stored and notifications sent

## 🔄 Workflow Management

### Request Lifecycle

```
Submitted → Agent Selection → Parallel Execution → Results → Storage → Notification
    ↓           ↓                    ↓            ↓        ↓           ↓
  Pending  →  Running        →  Processing  →  Complete → Stored →  Sent
```

### Status Tracking

- **Pending**: Request submitted, awaiting processing
- **Running**: Agents are being selected and initialized
- **Processing**: Agents executing in background
- **Completed**: All agents finished successfully
- **Failed**: One or more agents encountered errors
- **Partial**: Some agents succeeded, others failed

## 🔒 Security & Best Practices

### Authentication
- Use service account with minimal required permissions
- Store API keys in Google Secret Manager
- Implement request validation and rate limiting

### Data Protection
- Encrypt sensitive data in transit and at rest
- Implement proper access controls
- Regular security audits and updates

### Monitoring
- Enable Cloud Logging and Monitoring
- Set up alerts for failures and performance issues
- Monitor resource usage and costs

## 🛠️ Development

### Adding New Agents

1. Create agent class inheriting from `BaseAgent`
2. Implement required methods (`get_dependencies`, `execute`)
3. Register with orchestrator in `main.py`
4. Add tests in `tests/` directory

### Configuration

All configuration is handled through environment variables and the `.env` file. Key settings:

- `MAX_PARALLEL_AGENTS`: Maximum agents to run simultaneously
- `AGENT_TIMEOUT`: Timeout for individual agent execution
- `DEBUG`: Enable debug logging
- `LOG_LEVEL`: Set logging level (INFO, DEBUG, ERROR)

### Testing

```bash
# Run all tests
python -m pytest tests/

# Run specific agent tests
python -m pytest tests/test_web_crawler.py

# Run with coverage
python -m pytest --cov=. tests/
```

## 📊 Monitoring & Logging

### Cloud Logging
```bash
# View logs
gcloud logging read "resource.type=cloud_run_revision" \
    --filter="resource.labels.service_name=marketing-intake-api"

# View specific request logs
gcloud logging read "jsonPayload.request_id=your-request-id"
```

### Cloud Monitoring
- Set up dashboards for key metrics
- Configure alerts for error rates and latency
- Monitor resource utilization

## 🚨 Troubleshooting

### Common Issues

**Import Errors**: Ensure all dependencies are installed
```bash
pip install -r requirements.txt
```

**Authentication Errors**: Check service account permissions
```bash
gcloud auth application-default login
```

**Memory Issues**: Increase Cloud Run memory allocation
```bash
gcloud run deploy marketing-intake-api --memory 4Gi
```

**Timeout Errors**: Increase agent timeout settings
```bash
# In .env file
AGENT_TIMEOUT=600
```

### Debug Mode

Enable debug logging for detailed troubleshooting:
```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
```

## 📈 Performance Optimization

### Scaling
- Use Cloud Run concurrency settings for high throughput
- Implement caching for frequently accessed data
- Optimize agent execution with parallel processing

### Cost Optimization
- Use preemptible instances where possible
- Set appropriate memory and CPU allocations
- Implement request batching for bulk operations

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Check the troubleshooting section above
- Review Cloud Run and App Engine logs
- Monitor application health via `/health` endpoint
- Check agent status via `/agents` endpoint

---

**Quick Start Commands:**
```bash
# 1. Setup Google Cloud Project
gcloud config set project your-project-id

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env .env.local
# Edit .env.local with your credentials

# 4. Run locally
python main.py

# 5. Test the API
curl -X POST http://localhost:8080/intake \
  -H "Content-Type: application/json" \
  -d '{"intake":{"campaign_name":"Test Campaign"}}'
```

The system is now ready for both development and production use! 🚀
