# Database Migration System with H2O.ai GPTe Agents

A production-ready database migration application that uses H2O.ai GPTe agents to orchestrate PostgreSQL database migrations with a web-based GUI.

## Features

- **Four AI-Powered Agents**:
  - **Discovery Agent**: Analyzes source and destination databases, compares configurations, schemas, and tables
  - **Validation Agent**: Performs test migrations and validates data integrity with checksums
  - **Generation Agent**: Creates migration plans with risk assessment and APPROVE/DENY recommendations
  - **Execution Agent**: Executes full migrations with real-time progress tracking and validation

- **Web-Based GUI**: Modern, responsive interface for configuration and monitoring
- **RESTful API**: Flask-based backend with comprehensive endpoints
- **Real-Time Updates**: Live progress logs and agent status updates
- **Human-in-the-Loop**: Manual approval/denial workflow for migration execution
- **Comprehensive Validation**: Row counts, checksums, and sample data comparison
- **H2O.ai GPTe SDK Integration**: Uses official Python SDK for reliable AI agent orchestration

## Architecture

```
DBMigrate/
├── app.py                          # Flask API server
├── gpte_client.py                  # H2O.ai GPTe SDK wrapper
├── db_operations.py                # PostgreSQL operations
├── agents/
│   ├── __init__.py                 # Package initialization
│   ├── discovery_agent.py          # Database discovery
│   ├── validation_agent.py         # Migration validation
│   ├── generation_agent.py         # Plan generation
│   └── execution_agent.py          # Migration execution
├── static/
│   └── index.html                  # Web GUI
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variables template
├── Dockerfile                      # Docker configuration
├── docker-compose.yml              # Docker Compose setup
├── test_db_operations.py           # Database tests
├── test_h2ogpte_sdk.py            # GPTe SDK tests
├── test_full_integration.py        # Integration tests
└── README.md                       # This file
```

## Prerequisites

- Python 3.8 or higher
- PostgreSQL databases (source and destination)
- H2O.ai GPTe API access with valid API key
- Network connectivity to databases and H2O.ai GPTe instance

## Installation

### 1. Clone or Navigate to the Project

```bash
cd /Users/lmccoy/VIBE/DBMigrate
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- Flask 3.0.0 (web framework)
- Flask-CORS 4.0.0 (cross-origin requests)
- psycopg2-binary 2.9.9 (PostgreSQL adapter)
- requests 2.31.0 (HTTP library)
- python-dotenv 1.0.0 (environment variables)
- gunicorn 21.2.0 (production server)
- pytest 7.4.3 (testing framework)
- **h2ogpte 1.6.47** (H2O.ai GPTe SDK)

### 4. Configure Environment Variables (Optional)

```bash
cp .env.example .env
# Edit .env with your default settings
```

## Configuration

### Database Credentials

You'll need connection details for both source and destination PostgreSQL databases:

- **Host**: Database server hostname or IP address
- **Port**: PostgreSQL port (default: 5432)
- **Database**: Database name
- **Username**: Database user with appropriate permissions
- **Password**: Database password
- **SSL Mode**: `require`, `prefer`, or `disable`

### H2O.ai GPTe Configuration

Required credentials for H2O.ai GPTe:

- **API URL**: `https://h2ogpte.internal.dedicated.h2o.ai` (base URL without /api suffix)
- **API Key**: Your H2O.ai GPTe API key (format: `sk-...`)
- **Model ID**: Model to use (e.g., `gpt-4.1-mini`, `gpt-4-turbo-2024-04-09`)

**Important Notes**:
- This application uses the **official H2O.ai GPTe Python SDK**
- The SDK handles Okta authentication automatically
- SSL certificate verification is disabled for internal instances
- Do NOT include `/api` at the end of the API URL

## Usage

### Starting the Application

1. **Start the Flask server**:

```bash
python app.py
```

The server will start on `http://localhost:8000`

2. **Open the web interface**:

Open your browser and navigate to `http://localhost:8000`

### Migration Workflow

#### Step 1: Configure Databases

1. Enter source database credentials:
   - Host, port, database name
   - Username and password
   - SSL mode

2. Enter destination database credentials:
   - Host, port, database name
   - Username and password
   - SSL mode

3. Enter H2O.ai GPTe API credentials:
   - API URL: `https://h2ogpte.internal.dedicated.h2o.ai`
   - API Key: Your API key (starts with `sk-`)
   - Model ID: `gpt-4.1-mini` (or another available model)

4. Click "Save Configuration"

The system will validate all connections before proceeding.

#### Step 2: Start Workflow

Click "Start Migration Workflow" to begin. The system will execute:

1. **Discovery Phase** (Agent 1):
   - Connects to both databases
   - Analyzes database versions and configurations
   - Discovers schemas and tables
   - Calculates database sizes
   - Generates compatibility analysis using AI
   - **Output**: Detailed comparison report

2. **Validation Phase** (Agent 2):
   - Creates sample backups from both databases
   - Selects a suitable test table (small, representative)
   - Performs test migration on the selected table
   - Validates data integrity (row counts, checksums, sample data)
   - Generates validation report with AI recommendations
   - **Output**: Test migration results and feasibility assessment

3. **Generation Phase** (Agent 3):
   - Reviews discovery and validation results using AI
   - Analyzes compatibility and migration risks
   - Generates detailed migration plan with:
     - Recommended approach (table-by-table, schema-based, etc.)
     - Estimated migration time
     - Identified potential issues
     - Risk assessment (HIGH/MEDIUM/LOW)
   - Provides final recommendation: **APPROVE** or **DENY**
   - **Output**: Migration plan and AI recommendation

#### Step 3: Approve or Deny

After the Generation Agent completes:

- Review the AI-generated recommendation
- Review the detailed risk assessment
- Review the proposed migration plan
- **Approve**: Click "Approve Migration" to proceed to execution
- **Deny**: Click "Deny Migration" to stop the workflow

**Note**: This is a critical decision point. The application requires explicit human approval before executing the full migration.

#### Step 4: Execution (if approved)

The Execution Agent will:

- Migrate all tables from source to destination
- Process tables in order (considering dependencies)
- Migrate data in batches (default: 1000 rows per batch)
- Provide real-time progress updates in the GUI
- Validate each migrated table:
  - Compare row counts
  - Calculate and compare checksums
  - Verify sample data
- Retry failed tables (up to 2 retries)
- Generate comprehensive final migration report with AI analysis
- **Output**: Complete migration results with statistics

### Monitoring

- **Agent Status Cards**: Real-time visual status of each agent (pending, running, completed, failed)
- **Workflow Logs**: Detailed logs of all operations with timestamps
- **Agent Reports**: Comprehensive JSON reports from each agent phase
- **Progress Tracking**: Live updates during table migrations

## API Endpoints

### Configuration

```bash
POST /api/configure
```

Configure database connections and GPTe API.

**Request Body**:
```json
{
  "source": {
    "host": "source-host",
    "port": 5432,
    "database": "source_db",
    "user": "postgres",
    "password": "password",
    "sslmode": "prefer"
  },
  "destination": {
    "host": "dest-host",
    "port": 5432,
    "database": "dest_db",
    "user": "postgres",
    "password": "password",
    "sslmode": "prefer"
  },
  "gpte": {
    "api_url": "https://h2ogpte.internal.dedicated.h2o.ai",
    "api_key": "sk-your-api-key",
    "model_id": "gpt-4.1-mini"
  }
}
```

**Response**:
```json
{
  "success": true,
  "message": "Configuration saved and validated successfully"
}
```

### Workflow Management

```bash
# Start workflow
POST /api/workflow/start

# Get workflow status
GET /api/workflow/status

# Approve migration (after Generation Agent)
POST /api/workflow/approve

# Deny migration
POST /api/workflow/deny
Body: { "reason": "Optional reason for denial" }

# Reset workflow
POST /api/reset
```

### Reports and Logs

```bash
# Get all logs
GET /api/logs

# Get specific agent report
GET /api/reports/{agent}
# where {agent} is: discovery, validation, generation, or execution

# Get all agent reports
GET /api/reports
```

### Health Check

```bash
GET /api/health
```

## Security Considerations

- **Passwords**: Never logged or exposed in API responses
- **SSL/TLS**: Support for SSL mode in database connections
- **API Keys**: Stored securely, not exposed in logs
- **Network**: Ensure proper firewall rules for database access
- **Validation**: All user inputs are validated and sanitized
- **SQL Injection**: Uses parameterized queries exclusively
- **Authentication**: H2O.ai GPTe SDK handles Okta authentication

## Error Handling

The application includes comprehensive error handling:

- **Database Connection Failures**: Clear error messages with troubleshooting hints
- **GPTe API Timeouts**: Automatic retry with exponential backoff (up to 3 attempts)
- **Transaction Rollbacks**: Automatic rollback on migration failures
- **Retry Logic**: Transient failures are retried automatically
- **Detailed Logging**: All errors logged with full context
- **User Feedback**: User-friendly error messages in GUI

## Troubleshooting

### Connection Issues

**Problem**: "Connection failed" error for databases

**Solutions**:
- Verify database credentials are correct
- Check network connectivity to database host
- Verify firewall rules allow connections on the database port
- Test connection manually: `psql -h host -U user -d database`
- Ensure the database user has appropriate permissions

### GPTe API Issues

**Problem**: "GPTe initialization failed" error

**Solutions**:
- Verify API URL is correct (no `/api` suffix)
- Check that API key is valid and starts with `sk-`
- Verify network access to H2O.ai GPTe instance
- Check that the model ID is available
- Review H2O.ai GPTe SDK logs for details

**Problem**: SSL certificate errors

**Solution**: The application is configured to disable SSL verification for internal instances. This is handled automatically by the SDK.

**Problem**: Version mismatch warning

**Solution**: Install the matching SDK version:
```bash
pip install h2ogpte==1.6.47
```

### Migration Failures

**Problem**: Tables fail to migrate

**Solutions**:
- Check database logs for detailed error messages
- Verify sufficient storage space on destination database
- Check for schema incompatibilities (data types, constraints)
- Review table-specific error messages in the logs
- Ensure destination database is not in read-only mode

**Problem**: Validation failures after migration

**Solutions**:
- Check for data type conversion issues
- Verify both databases have same time zone settings
- Review checksums for specific mismatches
- Examine sample data differences in validation report

## Testing

### Test Database Connections

```bash
python test_db_operations.py -v
```

### Test H2O.ai GPTe SDK

```bash
python test_h2ogpte_sdk.py
```

### Test Full Integration

```bash
python test_full_integration.py
```

### Run All Tests

```bash
pytest -v
```

## Development

### Running in Development Mode

```bash
export DEBUG=true
export PORT=8000
python app.py
```

### Code Structure

- **`app.py`**: Main Flask application with API endpoints and workflow orchestration
- **`gpte_client.py`**: H2O.ai GPTe SDK wrapper with retry logic and error handling
- **`db_operations.py`**: PostgreSQL database operations (connect, query, migrate, validate)
- **`agents/`**: Individual agent implementations (discovery, validation, generation, execution)
- **`static/`**: Frontend HTML/CSS/JavaScript for web interface

### Adding New Agents

To add a new agent:

1. Create new file in `agents/` directory (e.g., `agents/my_agent.py`)
2. Implement agent class with `run()` method
3. Use `GPTeClient.send_agent_prompt()` for AI interactions
4. Update `app.py` workflow to include new agent
5. Update frontend to display new agent status

## Production Deployment

### Using Gunicorn

```bash
gunicorn -w 4 -b 0.0.0.0:8000 --timeout 120 app:app
```

Parameters:
- `-w 4`: 4 worker processes
- `-b 0.0.0.0:8000`: Bind to all interfaces on port 8000
- `--timeout 120`: 2-minute timeout for long-running requests
- `app:app`: Application module and instance

### Environment Variables

```bash
export PORT=8000
export DEBUG=false
export LOG_LEVEL=INFO
```

### Systemd Service (Linux)

Create `/etc/systemd/system/dbmigrate.service`:

```ini
[Unit]
Description=Database Migration Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/DBMigrate
Environment="PATH=/path/to/DBMigrate/venv/bin"
ExecStart=/path/to/DBMigrate/venv/bin/gunicorn -w 4 -b 0.0.0.0:8000 --timeout 120 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable dbmigrate
sudo systemctl start dbmigrate
sudo systemctl status dbmigrate
```

### Docker Deployment

Build and run with Docker Compose:

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f dbmigrate

# Stop
docker-compose down
```

Access at `http://localhost:8000`

### Nginx Reverse Proxy (Optional)

```nginx
server {
    listen 80;
    server_name dbmigrate.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }
}
```

## Limitations

- Currently supports **PostgreSQL databases only**
- Requires continuous network connectivity during migration
- Large databases (>100GB) may require significant time
- Does not handle custom PostgreSQL extensions automatically
- Requires H2O.ai GPTe access with valid API key

## Future Enhancements

- Support for MySQL, MariaDB, and other databases
- Incremental/differential migrations
- Scheduled migrations with cron-like scheduling
- Email/Slack notifications for workflow events
- Advanced schema transformation capabilities
- Multi-database parallel migrations
- Migration rollback functionality
- Cloud storage integration for backups

## Technologies Used

- **Backend**: Python 3.8+, Flask 3.0.0
- **Database**: PostgreSQL, psycopg2-binary 2.9.9
- **AI Orchestration**: H2O.ai GPTe SDK 1.6.47
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Deployment**: Gunicorn, Docker, Docker Compose
- **Testing**: pytest 7.4.3

## License

[Specify your license here]

## Support

For issues, questions, or contributions:
- Review the documentation in this README
- Check the QUICKSTART.md for quick start guide
- Review SDK_MIGRATION_NOTES.md for SDK-specific information
- Run diagnostic scripts (test_h2ogpte_sdk.py, test_full_integration.py)
- Check application logs for detailed error information

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

## Credits

Built with:
- **Flask** - Web framework
- **H2O.ai GPTe** - AI agent orchestration and decision support
- **PostgreSQL** - Database platform
- **psycopg2** - PostgreSQL adapter for Python

## Version History

### Version 1.0.0 (December 9, 2025)
- Initial release
- Four AI-powered agents for complete migration workflow
- Web-based GUI with real-time updates
- H2O.ai GPTe SDK integration
- Comprehensive validation and error handling
- Docker support
- Production-ready deployment options

---

**Version**: 1.0.0
**Last Updated**: December 9, 2025
**Status**: Production Ready ✅
