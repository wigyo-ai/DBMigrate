# Quick Start Guide

Get your Database Migration System up and running in 5 minutes.

## Prerequisites

Before you begin, ensure you have:
- ✅ Python 3.8 or higher
- ✅ PostgreSQL databases (source and destination) with access credentials
- ✅ H2O.ai GPTe API access with a valid API key (format: `sk-...`)
- ✅ Network connectivity to both databases and H2O.ai GPTe instance

## Installation (5 minutes)

### Step 1: Navigate to Project Directory

```bash
cd /Users/lmccoy/VIBE/DBMigrate
```

### Step 2: Create and Activate Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs all required packages including:
- Flask (web framework)
- psycopg2-binary (PostgreSQL adapter)
- **h2ogpte** (H2O.ai GPTe SDK)
- And other dependencies

**Installation should take 1-2 minutes.**

### Step 4: Verify Installation

Test that the H2O.ai GPTe SDK is working:

```bash
python test_h2ogpte_sdk.py
```

Expected output:
```
✓ h2ogpte SDK is installed
✓ Client initialized successfully
✓ SUCCESS! Response received
```

## Quick Start

### Option 1: Web Interface (Recommended)

#### 1. Start the Server

```bash
python app.py
```

You should see:
```
INFO:__main__:Starting Database Migration API on port 8000
 * Serving Flask app 'app'
 * Running on http://0.0.0.0:8000
```

#### 2. Open Your Browser

Navigate to: **http://localhost:8000**

#### 3. Configure Databases

In the web interface:

**Source Database:**
- Host: `your-source-host.com`
- Port: `5432`
- Database: `source_database`
- Username: `postgres`
- Password: `your_password`
- SSL Mode: `prefer` (or `require` for production)

**Destination Database:**
- Host: `your-destination-host.com`
- Port: `5432`
- Database: `destination_database`
- Username: `postgres`
- Password: `your_password`
- SSL Mode: `prefer` (or `require` for production)

**H2O.ai GPTe Configuration:**
- API URL: `https://h2ogpte.internal.dedicated.h2o.ai`
- API Key: `sk-your-api-key-here`
- Model ID: `gpt-4.1-mini`

**Important**:
- Do NOT include `/api` at the end of the API URL
- API key should start with `sk-`

#### 4. Save Configuration

Click **"Save Configuration"** button.

The system will:
- Test source database connection
- Test destination database connection
- Initialize H2O.ai GPTe client
- Enable the "Start Migration Workflow" button

#### 5. Start Migration Workflow

Click **"Start Migration Workflow"** button.

Watch the agents work:
1. **Discovery Agent** - Analyzes both databases (30-60 seconds)
2. **Validation Agent** - Tests migration feasibility (1-2 minutes)
3. **Generation Agent** - Creates migration plan (30-60 seconds)
4. **Awaiting Approval** - Human decision required

#### 6. Review and Approve

After Generation Agent completes:
- Review the AI recommendation (APPROVE or DENY)
- Review the risk assessment
- Review the migration plan
- Click **"Approve Migration"** or **"Deny Migration"**

#### 7. Watch Execution

If approved, the Execution Agent will:
- Migrate all tables
- Show real-time progress
- Validate each table
- Generate final report

#### 8. View Results

Review:
- Final migration statistics
- Agent reports (click on each agent card)
- Complete workflow logs

---

### Option 2: Docker (Alternative)

If you prefer Docker:

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f dbmigrate

# Access the interface
# Open browser to: http://localhost:8000
```

To stop:
```bash
docker-compose down
```

---

## Example Configuration

### Source Database Example
```
Host: prod-db.company.com
Port: 5432
Database: production_app
Username: migration_user
Password: secure_password_123
SSL Mode: require
```

### Destination Database Example
```
Host: staging-db.company.com
Port: 5432
Database: production_app_copy
Username: migration_user
Password: secure_password_456
SSL Mode: require
```

### H2O.ai GPTe Example
```
API URL: https://h2ogpte.internal.dedicated.h2o.ai
API Key: sk-3fQs4vrWxaHGDZslaZzaey71rH7sQj6trb8F7YiU9YxoOCkR
Model ID: gpt-4.1-mini
```

**Note**: Use the base URL without `/api` suffix when using the SDK.

---

## Testing the Setup

### Test 1: Database Connection

Create a test file `test_my_db.py`:

```python
from db_operations import test_connection

config = {
    'host': 'your-host',
    'port': 5432,
    'database': 'your_db',
    'user': 'postgres',
    'password': 'your_password',
    'sslmode': 'prefer'
}

success, message = test_connection(config)
print(f"Connection: {message}")
```

Run it:
```bash
python test_my_db.py
```

### Test 2: H2O.ai GPTe Connection

```bash
python test_h2ogpte_sdk.py
```

### Test 3: Full Integration

```bash
python test_full_integration.py
```

### Test 4: Run Database Operation Tests

```bash
python test_db_operations.py -v
```

---

## Common Issues and Solutions

### Issue 1: Port 8000 Already in Use

**Error**: `Address already in use`

**Solution**: Change the port
```bash
PORT=9000 python app.py
```

Then access at: `http://localhost:9000`

### Issue 2: "Connection failed" for Database

**Possible Causes**:
- Wrong credentials
- Database not accessible from your network
- Firewall blocking connection

**Solution**:
1. Verify credentials
2. Test with psql: `psql -h host -U user -d database`
3. Check firewall rules
4. Verify database is running

### Issue 3: "GPTe initialization failed"

**Possible Causes**:
- Wrong API URL format
- Invalid API key
- Network connectivity issues

**Solutions**:
1. Verify API URL is correct (no `/api` suffix)
2. Check API key starts with `sk-`
3. Test with: `python test_h2ogpte_sdk.py`
4. Verify network access to H2O.ai GPTe instance

### Issue 4: SSL Certificate Errors

**Error**: `[SSL: CERTIFICATE_VERIFY_FAILED]`

**Solution**: The application is already configured to handle this. SSL verification is disabled for internal instances in `gpte_client.py`.

If you still see this error, check that you're using the SDK version:
```bash
pip install h2ogpte==1.6.47
```

### Issue 5: Version Mismatch Warning

**Warning**: `Server version 1.6.47 doesn't match client version 1.6.48`

**Solution**: Install the exact matching version
```bash
pip install h2ogpte==1.6.47
```

### Issue 6: Module Not Found

**Error**: `ModuleNotFoundError: No module named 'h2ogpte'`

**Solution**: Ensure virtual environment is activated and install dependencies
```bash
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## What Each Agent Does

### 1. Discovery Agent (30-60 seconds)
- Connects to both databases
- Identifies schemas, tables, and their sizes
- Compares database versions
- Analyzes compatibility
- **Output**: Comparison report with AI analysis

### 2. Validation Agent (1-2 minutes)
- Creates sample backups
- Performs test migration on a small table
- Validates data integrity (row counts, checksums)
- **Output**: Feasibility assessment with AI recommendations

### 3. Generation Agent (30-60 seconds)
- Reviews all previous findings
- Assesses risks (HIGH/MEDIUM/LOW)
- Creates detailed migration plan
- **Output**: Migration plan and APPROVE/DENY recommendation

### 4. Execution Agent (varies by database size)
- Executes full migration
- Migrates tables in batches
- Validates each table
- **Output**: Final migration report with statistics

---

## Next Steps

### Production Use

1. **Review the full [README.md](README.md)** for:
   - Complete API documentation
   - Security considerations
   - Production deployment options
   - Troubleshooting guide

2. **Review [SDK_MIGRATION_NOTES.md](SDK_MIGRATION_NOTES.md)** for:
   - H2O.ai GPTe SDK details
   - Configuration specifics
   - Migration from REST API information

3. **Test on non-production databases first**
   - Always test with copies or dev databases
   - Verify the migration plan before approving
   - Have a rollback plan ready

4. **Configure for production**:
   - Use SSL mode: `require`
   - Use strong passwords
   - Configure proper network security
   - Set up monitoring and logging

---

## Production Checklist

Before running in production:

- [ ] Tested on non-production databases
- [ ] Verified backup of source database exists
- [ ] Confirmed sufficient storage on destination
- [ ] Reviewed firewall and network rules
- [ ] Using SSL connections for databases
- [ ] Secured all API keys and passwords
- [ ] Tested rollback procedures
- [ ] Scheduled during maintenance window
- [ ] Stakeholders notified
- [ ] Monitoring in place

---

## Quick Reference Commands

```bash
# Start application
python app.py

# Start with custom port
PORT=9000 python app.py

# Test GPTe connection
python test_h2ogpte_sdk.py

# Test full integration
python test_full_integration.py

# Run database tests
python test_db_operations.py -v

# Docker deployment
docker-compose up -d

# View Docker logs
docker-compose logs -f

# Stop Docker
docker-compose down
```

---

## Getting Help

1. **Check logs**: Review workflow logs in the web interface
2. **Run diagnostics**: Use test scripts to identify issues
3. **Review documentation**: Check README.md for detailed information
4. **Test components**: Test database and GPTe connections separately

---

## Success Indicators

You know everything is working when:

✅ Server starts without errors on port 8000
✅ Web interface loads at http://localhost:8000
✅ Database connections test successfully
✅ H2O.ai GPTe client initializes
✅ "Start Migration Workflow" button becomes enabled
✅ Agents run and complete successfully
✅ Real-time logs show progress

---

**Ready to migrate!**

Start the application and navigate to **http://localhost:8000**

For detailed documentation, see [README.md](README.md)

---

**Quick Start Guide Version**: 1.0.0
**Last Updated**: December 9, 2025
**Estimated Setup Time**: 5 minutes ⏱️
