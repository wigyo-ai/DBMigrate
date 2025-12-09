"""
Database Migration Flask API
Main application file providing RESTful API for database migration orchestration.
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import logging
import os
from typing import Dict
import threading

from gpte_client import GPTeClient, AgentOrchestrator
from agents.discovery_agent import DiscoveryAgent
from agents.validation_agent import ValidationAgent
from agents.generation_agent import GenerationAgent
from agents.execution_agent import ExecutionAgent
from db_operations import test_connection

# Global state management (defined before logging handler)
app_state = {
    'configured': False,
    'source_config': None,
    'dest_config': None,
    'gpte_config': None,
    'workflow_status': 'idle',  # idle, running, completed, failed
    'current_agent': None,
    'results': {
        'discovery': None,
        'validation': None,
        'generation': None,
        'execution': None
    },
    'logs': [],
    'gpte_client': None,
    'orchestrator': None
}

# Thread lock for state management
state_lock = threading.Lock()


# Custom logging handler to capture all logs for UI display
class UILogHandler(logging.Handler):
    """Custom handler that adds log messages to app_state for UI display."""

    # Loggers to exclude from UI (too noisy)
    EXCLUDED_LOGGERS = {
        'werkzeug',  # Flask HTTP server logs
        'urllib3',   # HTTP library logs
    }

    def emit(self, record):
        try:
            # Filter out noisy loggers
            if record.name in self.EXCLUDED_LOGGERS:
                return

            # Also filter out werkzeug child loggers
            if any(record.name.startswith(excluded + '.') for excluded in self.EXCLUDED_LOGGERS):
                return

            # Map logging levels to UI levels
            level_map = {
                logging.DEBUG: 'info',
                logging.INFO: 'info',
                logging.WARNING: 'warning',
                logging.ERROR: 'error',
                logging.CRITICAL: 'error'
            }

            level = level_map.get(record.levelno, 'info')
            message = self.format(record)

            # Remove timestamp and logger name prefix for cleaner UI display
            # Format is: "2024-01-01 12:00:00 - module.name - LEVEL - message"
            parts = message.split(' - ', 3)
            if len(parts) >= 4:
                clean_message = parts[3]  # Just the message
            else:
                clean_message = message

            with state_lock:
                app_state['logs'].append({
                    'message': clean_message,
                    'level': level,
                    'timestamp': record.created
                })
        except Exception:
            self.handleError(record)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add UI log handler to root logger to capture all logs
ui_handler = UILogHandler()
ui_handler.setLevel(logging.INFO)
ui_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logging.getLogger().addHandler(ui_handler)

# Initialize Flask app
app = Flask(__name__, static_folder='static')
CORS(app)


def add_log(message: str, level: str = 'info'):
    """Add a log entry to the application logs."""
    # Use logger instead of directly adding to app_state
    # The UILogHandler will capture it and add it to app_state automatically
    if level == 'error':
        logger.error(message)
    elif level == 'warning':
        logger.warning(message)
    else:
        logger.info(message)


def sanitize_config(config: Dict) -> Dict:
    """Remove password from config for logging."""
    safe_config = config.copy()
    if 'password' in safe_config:
        safe_config['password'] = '***'
    return safe_config


@app.route('/')
def index():
    """Serve the main index page."""
    return send_from_directory('static', 'index.html')


@app.route('/test')
def test_page():
    """Serve the test/diagnostic page."""
    return send_from_directory('static', 'test.html')


@app.route('/api/configure', methods=['POST'])
def configure():
    """
    Configure database connections and GPTe API.

    Expected JSON body:
    {
        "source": {...database config...},
        "destination": {...database config...},
        "gpte": {
            "api_url": "...",
            "api_key": "...",
            "model_id": "..."
        }
    }
    """
    try:
        data = request.get_json()

        if not data or 'source' not in data or 'destination' not in data or 'gpte' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required configuration'
            }), 400

        # Test source connection
        add_log("Testing source database connection...")
        source_success, source_msg = test_connection(data['source'])
        if not source_success:
            return jsonify({
                'success': False,
                'error': f'Source connection failed: {source_msg}'
            }), 400

        # Test destination connection
        add_log("Testing destination database connection...")
        dest_success, dest_msg = test_connection(data['destination'])
        if not dest_success:
            return jsonify({
                'success': False,
                'error': f'Destination connection failed: {dest_msg}'
            }), 400

        # Initialize GPTe client
        add_log("Initializing H2O.ai GPTe client...")
        try:
            gpte_client = GPTeClient(
                api_url=data['gpte']['api_url'],
                api_key=data['gpte']['api_key'],
                model_id=data['gpte'].get('model_id', 'gpt-4-turbo-2024-04-09')
            )
            gpte_client.create_session()
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'GPTe initialization failed: {str(e)}'
            }), 400

        # Store configuration
        with state_lock:
            app_state['configured'] = True
            app_state['source_config'] = data['source']
            app_state['dest_config'] = data['destination']
            app_state['gpte_config'] = data['gpte']
            app_state['gpte_client'] = gpte_client
            app_state['orchestrator'] = AgentOrchestrator(gpte_client)

        add_log("Configuration completed successfully")
        logger.info(f"Configured source: {sanitize_config(data['source'])}")
        logger.info(f"Configured destination: {sanitize_config(data['destination'])}")

        return jsonify({
            'success': True,
            'message': 'Configuration saved and validated successfully'
        })

    except Exception as e:
        logger.error(f"Configuration failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/workflow/start', methods=['POST'])
def start_workflow():
    """Start the migration workflow."""
    with state_lock:
        if not app_state['configured']:
            return jsonify({
                'success': False,
                'error': 'Application not configured. Call /api/configure first.'
            }), 400

        if app_state['workflow_status'] == 'running':
            return jsonify({
                'success': False,
                'error': 'Workflow already running'
            }), 400

        # Reset state
        app_state['workflow_status'] = 'running'
        app_state['current_agent'] = 'discovery'
        app_state['results'] = {
            'discovery': None,
            'validation': None,
            'generation': None,
            'execution': None
        }
        app_state['logs'] = []

    # Run workflow in background thread
    thread = threading.Thread(target=run_workflow)
    thread.daemon = True
    thread.start()

    return jsonify({
        'success': True,
        'message': 'Workflow started'
    })


def run_workflow():
    """Run the complete migration workflow."""
    try:
        add_log("Starting migration workflow...")

        # Discovery Phase
        add_log("Starting Discovery Agent...")
        with state_lock:
            app_state['current_agent'] = 'discovery'
            app_state['orchestrator'].update_agent_status('discovery', 'running')

        discovery_agent = DiscoveryAgent(app_state['gpte_client'])
        discovery_results = discovery_agent.run(
            app_state['source_config'],
            app_state['dest_config']
        )

        with state_lock:
            app_state['results']['discovery'] = discovery_results
            app_state['orchestrator'].update_agent_status('discovery', 'completed', discovery_results)

        add_log("Discovery Agent completed")

        # Validation Phase
        add_log("Starting Validation Agent...")
        with state_lock:
            app_state['current_agent'] = 'validation'
            app_state['orchestrator'].update_agent_status('validation', 'running')

        validation_agent = ValidationAgent(app_state['gpte_client'])
        validation_results = validation_agent.run(
            app_state['source_config'],
            app_state['dest_config'],
            discovery_results
        )

        with state_lock:
            app_state['results']['validation'] = validation_results
            app_state['orchestrator'].update_agent_status('validation', 'completed', validation_results)

        add_log("Validation Agent completed")

        # Generation Phase
        add_log("Starting Generation Agent...")
        with state_lock:
            app_state['current_agent'] = 'generation'
            app_state['orchestrator'].update_agent_status('generation', 'running')

        generation_agent = GenerationAgent(app_state['gpte_client'])
        generation_results = generation_agent.run(
            discovery_results,
            validation_results
        )

        with state_lock:
            app_state['results']['generation'] = generation_results
            app_state['orchestrator'].update_agent_status('generation', 'completed', generation_results)
            app_state['generation_agent'] = generation_agent  # Store for approval handling

        recommendation = generation_results.get('recommendation', {}).get('decision', 'DENY')
        add_log(f"Generation Agent completed with recommendation: {recommendation}")

        # Wait for human approval before execution
        with state_lock:
            app_state['current_agent'] = 'awaiting_approval'
            app_state['workflow_status'] = 'awaiting_approval'

        add_log("Waiting for human approval to proceed with execution...")

    except Exception as e:
        logger.error(f"Workflow failed: {e}")
        add_log(f"Workflow failed: {str(e)}", 'error')
        with state_lock:
            app_state['workflow_status'] = 'failed'


@app.route('/api/workflow/approve', methods=['POST'])
def approve_workflow():
    """Approve the migration and proceed to execution."""
    try:
        with state_lock:
            if app_state['workflow_status'] != 'awaiting_approval':
                return jsonify({
                    'success': False,
                    'error': 'Workflow not awaiting approval'
                }), 400

            if 'generation_agent' not in app_state:
                return jsonify({
                    'success': False,
                    'error': 'Generation agent not available'
                }), 400

            # Record approval
            generation_agent = app_state['generation_agent']
            generation_agent.set_human_decision(True, "Approved via API")

            app_state['workflow_status'] = 'running'

        add_log("Migration approved by user. Starting Execution Agent...")

        # Run execution in background thread
        thread = threading.Thread(target=run_execution)
        thread.daemon = True
        thread.start()

        return jsonify({
            'success': True,
            'message': 'Migration approved and execution started'
        })

    except Exception as e:
        logger.error(f"Approval failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/workflow/deny', methods=['POST'])
def deny_workflow():
    """Deny the migration."""
    try:
        data = request.get_json() or {}
        reason = data.get('reason', 'Denied by user')

        with state_lock:
            if app_state['workflow_status'] != 'awaiting_approval':
                return jsonify({
                    'success': False,
                    'error': 'Workflow not awaiting approval'
                }), 400

            if 'generation_agent' in app_state:
                generation_agent = app_state['generation_agent']
                generation_agent.set_human_decision(False, reason)

            app_state['workflow_status'] = 'denied'

        add_log(f"Migration denied by user: {reason}")

        return jsonify({
            'success': True,
            'message': 'Migration denied'
        })

    except Exception as e:
        logger.error(f"Denial failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def run_execution():
    """Run the execution phase."""
    try:
        with state_lock:
            app_state['current_agent'] = 'execution'
            app_state['orchestrator'].update_agent_status('execution', 'running')

        def progress_callback(log_entry):
            """Callback for execution progress updates."""
            # No longer needed - UILogHandler captures all logger.info() calls
            # The execution agent already logs via logger, so we don't need to duplicate
            pass

        execution_agent = ExecutionAgent(app_state['gpte_client'], progress_callback)

        # Get migration plan from generation results
        migration_plan = app_state['results']['generation'].get('migration_plan', {})

        execution_results = execution_agent.run(
            app_state['source_config'],
            app_state['dest_config'],
            migration_plan,
            schemas=['public']  # Could be made configurable
        )

        with state_lock:
            app_state['results']['execution'] = execution_results
            app_state['orchestrator'].update_agent_status('execution', 'completed', execution_results)
            app_state['workflow_status'] = 'completed'

        add_log("Execution Agent completed. Migration finished!")

    except Exception as e:
        logger.error(f"Execution failed: {e}")
        add_log(f"Execution failed: {str(e)}", 'error')
        with state_lock:
            app_state['workflow_status'] = 'failed'


@app.route('/api/workflow/status', methods=['GET'])
def get_status():
    """Get current workflow status."""
    with state_lock:
        return jsonify({
            'configured': app_state['configured'],
            'workflow_status': app_state['workflow_status'],
            'current_agent': app_state['current_agent'],
            'orchestrator_state': (
                app_state['orchestrator'].get_workflow_state()
                if app_state['orchestrator'] else None
            )
        })


@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Get workflow logs."""
    with state_lock:
        return jsonify({
            'logs': app_state['logs']
        })


@app.route('/api/reports/<agent>', methods=['GET'])
def get_report(agent):
    """Get report for a specific agent."""
    if agent not in ['discovery', 'validation', 'generation', 'execution']:
        return jsonify({
            'success': False,
            'error': 'Invalid agent name'
        }), 400

    with state_lock:
        result = app_state['results'].get(agent)

    if result is None:
        return jsonify({
            'success': False,
            'error': f'No results available for {agent} agent'
        }), 404

    return jsonify({
        'success': True,
        'agent': agent,
        'results': result
    })


@app.route('/api/reports', methods=['GET'])
def get_all_reports():
    """Get all agent reports."""
    with state_lock:
        return jsonify({
            'success': True,
            'results': app_state['results']
        })


@app.route('/api/reset', methods=['POST'])
def reset_workflow():
    """Reset the workflow to initial state."""
    with state_lock:
        app_state['workflow_status'] = 'idle'
        app_state['current_agent'] = None
        app_state['results'] = {
            'discovery': None,
            'validation': None,
            'generation': None,
            'execution': None
        }
        app_state['logs'] = []
        if app_state['orchestrator']:
            app_state['orchestrator'].reset_workflow()

    add_log("Workflow reset")

    return jsonify({
        'success': True,
        'message': 'Workflow reset successfully'
    })


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'configured': app_state['configured']
    })


# Catch-all route for static files (must be last)
@app.route('/<path:path>')
def serve_static(path):
    """Serve static files."""
    try:
        return send_from_directory('static', path)
    except:
        # If file not found, return 404
        return jsonify({'error': 'File not found'}), 404


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'

    logger.info(f"Starting Database Migration API on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
