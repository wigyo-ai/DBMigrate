# Database Migration System with H2O.ai GPTe Agents

A production-ready database migration application that uses H2O.ai GPTe agents to orchestrate PostgreSQL database migrations with a web-based GUI.

## Features

- **Four AI-Powered Agents**:
  - **Discovery Agent**: Analyzes source and destination databases, compares configurations
  - **Validation Agent**: Performs test migrations and validates data integrity
  - **Generation Agent**: Creates migration plans with risk assessment and recommendations
  - **Execution Agent**: Executes full migrations with real-time progress tracking

- **Web-Based GUI**: Modern, responsive interface for configuration and monitoring
- **RESTful API**: Flask-based backend with comprehensive endpoints
- **Real-Time Updates**: Live progress logs and agent status updates
- **Human-in-the-Loop**: Manual approval/denial workflow for migration execution
- **Comprehensive Validation**: Row counts, checksums, and sample data comparison

## Architecture

```
DBMigrate/
├── app.py                          # Flask API server
├── gpte_client.py                  # H2O.ai GPTe API wrapper
├── db_operations.py                # PostgreSQL operations
├── agents/
│   ├── discovery_agent.py          # Database discovery
│   ├── validation_agent.py         # Migration validation
│   ├── generation_agent.py         # Plan generation
│   └── execution_agent.py          # Migration execution
├── static/
│   └── index.html                  # Web GUI
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variables template
└── README.md                       # This file
```

## Prerequisites

- Python 3.8 or higher
- PostgreSQL databases (source and destination)
- H2O.ai GPTe API access
- Network connectivity to databases and H2O.ai GPTe API

## Installation

### 1. Clone or Download the Repository

```bash
cd /path/to/DBMigrate
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

### 4. Configure Environment Variables (Optional)

Create a `.env` file for default configurations:

```bash
cp .env.example .env
# Edit .env with your default settings
```

## Configuration

### Database Credentials

You'll need connection details for both source and destination PostgreSQL databases:

- **Host**: Database server hostname or IP
- **Port**: PostgreSQL port (default: 5432)
- **Database**: Database name
- **Username**: Database user
- **Password**: Database password
- **SSL Mode**: `require`, `prefer`, or `disable`

### H2O.ai GPTe Configuration

Required credentials for H2O.ai GPTe:

- **API URL**: `https://h2ogpte.internal.dedicated.h2o.ai/api` (or your instance URL)
- **API Key**: Your H2O.ai GPTe API key
- **Model ID**: Model to use (default: `gpt-4-turbo-2024-04-09`)

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

1. Enter source database credentials
2. Enter destination database credentials
3. Enter H2O.ai GPTe API credentials
4. Click "Save Configuration"

The system will validate all connections before proceeding.

#### Step 2: Start Workflow

Click "Start Migration Workflow" to begin. The system will execute:

1. **Discovery Phase**: Analyzes both databases
   - Database versions and configurations
   - Schemas and tables
   - Size estimates
   - Compatibility analysis

2. **Validation Phase**: Tests migration feasibility
   - Creates sample backups
   - Performs test migration on a sample table
   - Validates data integrity

3. **Generation Phase**: Creates migration plan
   - Analyzes discovery and validation results
   - Assesses risks (HIGH/MEDIUM/LOW)
   - Generates detailed migration plan
   - Provides APPROVE or DENY recommendation

#### Step 3: Approve or Deny

After the Generation Agent completes:

- Review the AI recommendation
- Review the risk assessment
- Review the migration plan
- **Approve**: Proceeds to execution
- **Deny**: Stops the workflow

#### Step 4: Execution (if approved)

The Execution Agent will:

- Migrate all tables from source to destination
- Provide real-time progress updates
- Validate each migrated table
- Generate a final migration report

### Monitoring

- **Agent Status Cards**: Real-time status of each agent
- **Workflow Logs**: Detailed logs of all operations
- **Agent Reports**: Comprehensive reports from each agent

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
    "api_url": "https://h2ogpte.internal.dedicated.h2o.ai/api",
    "api_key": "your-api-key",
    "model_id": "gpt-4-turbo-2024-04-09"
  }
}
```

### Workflow Management

```bash
# Start workflow
POST /api/workflow/start

# Get workflow status
GET /api/workflow/status

# Approve migration
POST /api/workflow/approve

# Deny migration
POST /api/workflow/deny
Body: { "reason": "Optional reason" }

# Reset workflow
POST /api/reset
```

### Reports and Logs

```bash
# Get logs
GET /api/logs

# Get specific agent report
GET /api/reports/{agent}
# agent: discovery, validation, generation, or execution

# Get all reports
GET /api/reports
```

### Health Check

```bash
GET /api/health
```

## Security Considerations

- **Passwords**: Never log or expose passwords in responses
- **SSL/TLS**: Use SSL mode for database connections in production
- **API Keys**: Store H2O.ai GPTe API keys securely
- **Network**: Ensure proper firewall rules for database access
- **Validation**: All inputs are validated and sanitized
- **SQL Injection**: Uses parameterized queries exclusively

## Error Handling

The application includes comprehensive error handling:

- Database connection failures
- GPTe API timeouts and errors
- Transaction rollbacks on migration failures
- Retry logic for transient failures
- Detailed error logging

## Troubleshooting

### Connection Issues

**Problem**: "Connection failed" error

**Solutions**:
- Verify database credentials
- Check network connectivity
- Verify firewall rules
- Test database connectivity: `psql -h host -U user -d database`

### GPTe API Issues

**Problem**: "GPTe initialization failed"

**Solutions**:
- Verify API URL and key
- Check network access to H2O.ai GPTe
- Verify API key permissions
- Check API rate limits

### Migration Failures

**Problem**: Tables fail to migrate

**Solutions**:
- Check database logs for errors
- Verify sufficient storage on destination
- Check for schema incompatibilities
- Review detailed error messages in logs

## Development

### Running in Development Mode

```bash
export DEBUG=true
python app.py
```

### Running Tests

(Tests would go here - consider adding pytest tests)

```bash
pytest tests/
```

### Code Structure

- `app.py`: Main Flask application with API endpoints
- `gpte_client.py`: H2O.ai GPTe API wrapper with retry logic
- `db_operations.py`: PostgreSQL database operations
- `agents/`: Individual agent implementations
- `static/`: Frontend HTML/CSS/JavaScript

## Production Deployment

### Using Gunicorn

```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

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
ExecStart=/path/to/DBMigrate/venv/bin/gunicorn -w 4 -b 0.0.0.0:8000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable dbmigrate
sudo systemctl start dbmigrate
```

## Docker Deployment

See `Dockerfile` and `docker-compose.yml` for containerized deployment.

```bash
docker-compose up -d
```

## Limitations

- Currently supports PostgreSQL databases only
- Requires network connectivity during migration
- Large databases may require significant time
- Does not handle custom database extensions automatically

## Future Enhancements

- Support for MySQL, MariaDB, and other databases
- Incremental/differential migrations
- Scheduled migrations
- Email notifications
- Advanced schema transformation
- Multi-database parallel migrations

## License

[Specify your license here]

## Support

For issues, questions, or contributions:
- Create an issue in the repository
- Contact the development team

## Credits

Built with:
- Flask (Web framework)
- H2O.ai GPTe (AI agent orchestration)
- PostgreSQL (Database)
- psycopg2 (PostgreSQL adapter)

---

**Version**: 1.0.0
**Last Updated**: 2025-12-09
