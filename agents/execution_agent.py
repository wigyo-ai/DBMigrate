"""
Execution Agent
Executes the full database migration based on approved plan.
"""

import logging
from typing import Dict, List, Callable, Optional
import time
from db_operations import (
    get_tables, migrate_table, validate_migration,
    get_row_count, get_table_structure
)
from gpte_client import GPTeClient

logger = logging.getLogger(__name__)


class ExecutionAgent:
    """Agent responsible for executing the full database migration."""

    def __init__(self, gpte_client: GPTeClient, progress_callback: Optional[Callable] = None):
        """
        Initialize Execution Agent.

        Args:
            gpte_client: Configured GPTe client for AI assistance
            progress_callback: Optional callback function for progress updates
        """
        self.client = gpte_client
        self.progress_callback = progress_callback
        self.execution_results = {}
        self.migration_log = []

    def _log_progress(self, message: str, level: str = 'info'):
        """
        Log progress message and call progress callback if provided.

        Args:
            message: Progress message
            level: Log level (info, warning, error)
        """
        log_entry = {
            'timestamp': time.time(),
            'message': message,
            'level': level
        }
        self.migration_log.append(log_entry)

        # Log using standard logger
        if level == 'error':
            logger.error(message)
        elif level == 'warning':
            logger.warning(message)
        else:
            logger.info(message)

        # Call progress callback if provided
        if self.progress_callback:
            self.progress_callback(log_entry)

    def run(self, source_config: Dict[str, str], dest_config: Dict[str, str],
            migration_plan: Dict, schemas: List[str] = None) -> Dict[str, any]:
        """
        Execute full database migration.

        Args:
            source_config: Source database configuration
            dest_config: Destination database configuration
            migration_plan: Migration plan from Generation Agent
            schemas: List of schemas to migrate (default: ['public'])

        Returns:
            Dictionary containing execution results
        """
        logger.info("Execution Agent starting...")
        self._log_progress("Starting full database migration")

        if schemas is None:
            schemas = ['public']

        result = {
            'status': 'running',
            'start_time': time.time(),
            'schemas_migrated': [],
            'tables_migrated': [],
            'tables_failed': [],
            'validation_results': [],
            'statistics': {
                'total_tables': 0,
                'successful_tables': 0,
                'failed_tables': 0,
                'total_rows_migrated': 0
            }
        }

        try:
            # Migrate each schema
            for schema in schemas:
                self._log_progress(f"Starting migration for schema: {schema}")
                schema_result = self._migrate_schema(source_config, dest_config, schema)

                result['schemas_migrated'].append(schema)
                result['tables_migrated'].extend(schema_result['tables_migrated'])
                result['tables_failed'].extend(schema_result['tables_failed'])
                result['validation_results'].extend(schema_result['validation_results'])

                # Update statistics
                result['statistics']['total_tables'] += schema_result['total_tables']
                result['statistics']['successful_tables'] += schema_result['successful_tables']
                result['statistics']['failed_tables'] += schema_result['failed_tables']
                result['statistics']['total_rows_migrated'] += schema_result['total_rows_migrated']

            result['end_time'] = time.time()
            result['duration_seconds'] = result['end_time'] - result['start_time']

            # Determine overall status
            if result['statistics']['failed_tables'] == 0:
                result['status'] = 'completed_success'
                self._log_progress("Migration completed successfully!")
            else:
                result['status'] = 'completed_with_errors'
                self._log_progress(
                    f"Migration completed with {result['statistics']['failed_tables']} failures",
                    'warning'
                )

            # Store results
            self.execution_results = result

            # Generate final report using GPTe
            self._log_progress("Generating final migration report...")
            final_report = self._generate_final_report(result)
            result['final_report'] = final_report

        except Exception as e:
            logger.error(f"Execution failed: {e}")
            self._log_progress(f"Migration failed: {str(e)}", 'error')
            result['status'] = 'failed'
            result['error'] = str(e)

        return result

    def _migrate_schema(self, source_config: Dict[str, str], dest_config: Dict[str, str],
                        schema: str) -> Dict[str, any]:
        """
        Migrate all tables in a schema.

        Args:
            source_config: Source database configuration
            dest_config: Destination database configuration
            schema: Schema name to migrate

        Returns:
            Dictionary containing schema migration results
        """
        result = {
            'schema': schema,
            'tables_migrated': [],
            'tables_failed': [],
            'validation_results': [],
            'total_tables': 0,
            'successful_tables': 0,
            'failed_tables': 0,
            'total_rows_migrated': 0
        }

        try:
            # Get all tables in schema
            tables = get_tables(source_config, schema)
            result['total_tables'] = len(tables)

            self._log_progress(f"Found {len(tables)} tables in schema '{schema}'")

            # Migrate each table
            for i, table_info in enumerate(tables, 1):
                table_name = table_info['table_name']
                self._log_progress(
                    f"Migrating table {i}/{len(tables)}: {schema}.{table_name} "
                    f"({table_info['size']})"
                )

                # Perform migration
                migration_result = self._migrate_table(
                    source_config, dest_config, schema, table_name
                )

                if migration_result['success']:
                    result['tables_migrated'].append(f"{schema}.{table_name}")
                    result['successful_tables'] += 1
                    result['total_rows_migrated'] += migration_result.get('rows_migrated', 0)
                    self._log_progress(
                        f"Successfully migrated {schema}.{table_name} "
                        f"({migration_result.get('rows_migrated', 0)} rows)"
                    )

                    # Validate migration
                    self._log_progress(f"Validating {schema}.{table_name}...")
                    validation_result = validate_migration(
                        source_config, dest_config, schema, table_name
                    )
                    validation_result['table'] = f"{schema}.{table_name}"
                    result['validation_results'].append(validation_result)

                    if validation_result.get('validation_passed', False):
                        self._log_progress(f"Validation passed for {schema}.{table_name}")
                    else:
                        self._log_progress(
                            f"Validation failed for {schema}.{table_name}",
                            'warning'
                        )
                else:
                    result['tables_failed'].append({
                        'table': f"{schema}.{table_name}",
                        'error': migration_result.get('error', 'Unknown error')
                    })
                    result['failed_tables'] += 1
                    self._log_progress(
                        f"Failed to migrate {schema}.{table_name}: "
                        f"{migration_result.get('error', 'Unknown error')}",
                        'error'
                    )

        except Exception as e:
            logger.error(f"Schema migration failed: {e}")
            self._log_progress(f"Schema '{schema}' migration failed: {str(e)}", 'error')
            result['error'] = str(e)

        return result

    def _migrate_table(self, source_config: Dict[str, str], dest_config: Dict[str, str],
                       schema: str, table: str) -> Dict[str, any]:
        """
        Migrate a single table with error handling and retry logic.

        Args:
            source_config: Source database configuration
            dest_config: Destination database configuration
            schema: Schema name
            table: Table name

        Returns:
            Dictionary containing migration result
        """
        max_retries = 2
        batch_size = 1000

        for attempt in range(max_retries):
            try:
                result = migrate_table(
                    source_config, dest_config, schema, table, batch_size
                )

                if result['success']:
                    return result
                elif attempt < max_retries - 1:
                    self._log_progress(
                        f"Retry {attempt + 1}/{max_retries - 1} for {schema}.{table}",
                        'warning'
                    )
                    time.sleep(2)  # Wait before retry

            except Exception as e:
                if attempt < max_retries - 1:
                    self._log_progress(
                        f"Error migrating {schema}.{table}, retrying: {str(e)}",
                        'warning'
                    )
                    time.sleep(2)
                else:
                    return {
                        'success': False,
                        'error': str(e),
                        'rows_migrated': 0
                    }

        return {
            'success': False,
            'error': 'Max retries exceeded',
            'rows_migrated': 0
        }

    def _generate_final_report(self, execution_results: Dict) -> Dict[str, any]:
        """
        Generate final migration report using GPTe.

        Args:
            execution_results: Results from execution

        Returns:
            Dictionary containing final report
        """
        logger.info("Generating final report with GPTe...")

        role = """Analyze the results of a completed database migration and generate
        a comprehensive final report. Assess the overall success, identify any issues,
        and provide recommendations for post-migration actions."""

        tasks = [
            "Summarize the overall migration outcome (success, partial success, or failure)",
            "Report on total tables migrated and any failures",
            "Analyze validation results and data integrity",
            "Calculate success rate and migration efficiency",
            "Identify any tables that need attention or re-migration",
            "Provide post-migration recommendations and next steps",
            "Assess overall data quality and completeness",
            "Generate executive summary for stakeholders"
        ]

        context = {
            'execution_results': execution_results,
            'migration_log': self.migration_log[-50:]  # Last 50 log entries
        }

        response = self.client.send_agent_prompt(
            agent_name="Execution Agent (Final Report)",
            role=role,
            tasks=tasks,
            context=context
        )

        if not response['success']:
            logger.error("Failed to generate final report")
            return {
                'error': response.get('error', 'Unknown error'),
                'report': 'Failed to generate final report'
            }

        # Try to parse structured response
        parsed = self.client.parse_json_response(response['response'])
        if parsed:
            return parsed

        # Return raw response if parsing fails
        return {
            'report_text': response['response'],
            'raw': True
        }

    def get_progress_log(self) -> List[Dict]:
        """
        Get the migration progress log.

        Returns:
            List of log entries
        """
        return self.migration_log.copy()

    def get_summary(self) -> Dict[str, any]:
        """
        Get a summary of execution results.

        Returns:
            Dictionary containing execution summary
        """
        if not self.execution_results:
            return {'error': 'No execution data available'}

        stats = self.execution_results.get('statistics', {})

        return {
            'status': self.execution_results.get('status', 'unknown'),
            'duration_seconds': self.execution_results.get('duration_seconds', 0),
            'total_tables': stats.get('total_tables', 0),
            'successful_tables': stats.get('successful_tables', 0),
            'failed_tables': stats.get('failed_tables', 0),
            'total_rows_migrated': stats.get('total_rows_migrated', 0),
            'success_rate': (
                (stats.get('successful_tables', 0) / stats.get('total_tables', 1)) * 100
                if stats.get('total_tables', 0) > 0 else 0
            )
        }
