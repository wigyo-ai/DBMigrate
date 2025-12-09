# Quick Start Guide

Get up and running with the Database Migration System in 5 minutes.

## Prerequisites

- Python 3.8+
- PostgreSQL databases (source and destination)
- H2O.ai GPTe API access

## Installation

```bash
# 1. Navigate to the project directory
cd /Users/lmccoy/VIBE/DBMigrate

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

## Quick Start

### Option 1: Web Interface (Recommended)

```bash
# Start the server
python app.py
```

Then open your browser to `http://localhost:8000` and follow these steps:

1. **Configure Databases**
   - Enter source database credentials
   - Enter destination database credentials
   - Enter H2O.ai GPTe API credentials
   - Click "Save Configuration"

2. **Start Migration**
   - Click "Start Migration Workflow"
   - Monitor agent progress in real-time

3. **Approve Execution**
   - Review the AI recommendation
   - Click "Approve Migration" to proceed or "Deny Migration" to stop

4. **Monitor Completion**
   - Watch real-time logs
   - Review final reports

### Option 2: Docker

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Access at http://localhost:8000
```

## Example Configuration

### Source Database
```
Host: source-db.example.com
Port: 5432
Database: production_db
User: postgres
Password: your_password
SSL Mode: require
```

### Destination Database
```
Host: dest-db.example.com
Port: 5432
Database: production_db_copy
User: postgres
Password: your_password
SSL Mode: require
```

### H2O.ai GPTe
```
API URL: https://h2ogpte.internal.dedicated.h2o.ai
API Key: sk-your-api-key
Model ID: gpt-4.1-mini
```

**Note**: Use the base URL without `/api` suffix when using the SDK.

## Testing the Setup

### Test Database Connection

```python
from db_operations import test_connection

config = {
    'host': 'localhost',
    'port': 5432,
    'database': 'test_db',
    'user': 'postgres',
    'password': 'password',
    'sslmode': 'prefer'
}

success, message = test_connection(config)
print(f"Connection: {message}")
```

### Run Tests

```bash
pytest test_db_operations.py -v
```

## Common Issues

### Issue: "Connection failed"
**Solution**: Check database credentials and network connectivity

### Issue: "GPTe initialization failed"
**Solution**: Verify API URL and API key

### Issue: Port 8000 already in use
**Solution**: Change port with `PORT=9000 python app.py`

## Next Steps

1. Read the full [README.md](README.md) for detailed documentation
2. Review the [API documentation](#api-endpoints) in README
3. Configure your production databases
4. Run a test migration on non-critical data first

## Support

For issues or questions:
- Check the [README.md](README.md)
- Review application logs
- Check the troubleshooting section

## Production Checklist

Before running in production:

- [ ] Test on non-production databases first
- [ ] Verify backup of source database exists
- [ ] Ensure sufficient storage on destination
- [ ] Review firewall and network rules
- [ ] Use SSL mode for database connections
- [ ] Secure API keys and passwords
- [ ] Test rollback procedures
- [ ] Schedule during maintenance window
- [ ] Monitor system resources during migration

---

**Ready to migrate!** Start the application and navigate to `http://localhost:8000`
