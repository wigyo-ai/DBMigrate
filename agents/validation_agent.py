"""
Validation Agent
Validates migration feasibility through test migrations and data integrity checks.
"""

import logging
from typing import Dict, Optional
import json
from db_operations import (
    get_tables, migrate_table, validate_migration,
    get_row_count, get_sample_data, calculate_table_checksum
)
from gpte_client import GPTeClient

logger = logging.getLogger(__name__)


class ValidationAgent:
    """Agent responsible for validating migration feasibility."""

    def __init__(self, gpte_client: GPTeClient):
        """
        Initialize Validation Agent.

        Args:
            gpte_client: Configured GPTe client for AI assistance
        """
        self.client = gpte_client
        self.validation_data = {}

    def select_test_table(self, source_config: Dict[str, str], schema: str = 'public') -> Optional[Dict[str, str]]:
        """
        Select a suitable table for test migration.

        Args:
            source_config: Source database configuration
            schema: Schema to search (default: 'public')

        Returns:
            Dictionary with schema and table name, or None if no suitable table found
        """
        try:
            tables = get_tables(source_config, schema)

            if not tables:
                logger.warning(f"No tables found in schema '{schema}'")
                return None

            # Sort by size (prefer smaller tables for testing)
            tables_sorted = sorted(tables, key=lambda t: t['size_bytes'])

            # Filter tables that are not too large (< 100MB) and have some data
            suitable_tables = [
                t for t in tables_sorted
                if t['size_bytes'] < 100 * 1024 * 1024 and t['size_bytes'] > 0
            ]

            if suitable_tables:
                selected = suitable_tables[0]
                logger.info(f"Selected test table: {schema}.{selected['table_name']} "
                           f"({selected['size']})")
                return {
                    'schema': schema,
                    'table': selected['table_name'],
                    'size': selected['size'],
                    'size_bytes': selected['size_bytes']
                }

            # If no suitable table, just pick the smallest one
            if tables:
                selected = tables_sorted[0]
                logger.info(f"Selected test table (fallback): {schema}.{selected['table_name']} "
                           f"({selected['size']})")
                return {
                    'schema': schema,
                    'table': selected['table_name'],
                    'size': selected['size'],
                    'size_bytes': selected['size_bytes']
                }

        except Exception as e:
            logger.error(f"Failed to select test table: {e}")

        return None

    def perform_test_migration(self, source_config: Dict[str, str],
                               dest_config: Dict[str, str],
                               test_table: Dict[str, str],
                               max_rows: int = 100) -> Dict[str, any]:
        """
        Perform a test migration on a selected table.

        Args:
            source_config: Source database configuration
            dest_config: Destination database configuration
            test_table: Dictionary with schema and table name
            max_rows: Maximum number of rows to migrate for testing (default: 100)

        Returns:
            Dictionary containing test migration results
        """
        schema = test_table['schema']
        table = test_table['table']

        logger.info(f"Starting test migration for {schema}.{table} (max {max_rows} rows)")

        result = {
            'table': f"{schema}.{table}",
            'migration': {},
            'validation': {}
        }

        try:
            # Perform migration with limited rows for testing
            migration_result = migrate_table(
                source_config, dest_config, schema, table,
                batch_size=100, max_rows=max_rows
            )
            result['migration'] = migration_result

            if not migration_result['success']:
                logger.error(f"Test migration failed: {migration_result.get('error')}")
                return result

            # Validate migration
            validation_result = validate_migration(
                source_config, dest_config, schema, table
            )
            result['validation'] = validation_result

            logger.info(f"Test migration validation passed: {validation_result.get('validation_passed')}")

        except Exception as e:
            logger.error(f"Test migration error: {e}")
            result['error'] = str(e)

        return result

    def create_sample_backups(self, config: Dict[str, str], schema: str = 'public') -> Dict[str, any]:
        """
        Create sample backups by collecting metadata and sample data from tables.

        Args:
            config: Database configuration
            schema: Schema to backup (default: 'public')

        Returns:
            Dictionary containing backup information
        """
        logger.info(f"Creating sample backup for schema '{schema}'")

        backup_data = {
            'schema': schema,
            'tables': []
        }

        try:
            tables = get_tables(config, schema)

            # Sample up to 5 tables
            sample_tables = tables[:5] if len(tables) > 5 else tables

            for table_info in sample_tables:
                table_name = table_info['table_name']
                try:
                    row_count = get_row_count(config, schema, table_name)
                    sample_data = get_sample_data(config, schema, table_name, limit=3)
                    checksum = calculate_table_checksum(config, schema, table_name, sample_size=100)

                    backup_data['tables'].append({
                        'table': table_name,
                        'row_count': row_count,
                        'sample_data': sample_data,
                        'checksum': checksum
                    })
                except Exception as e:
                    logger.warning(f"Failed to backup table {table_name}: {e}")
                    backup_data['tables'].append({
                        'table': table_name,
                        'error': str(e)
                    })

        except Exception as e:
            logger.error(f"Sample backup failed: {e}")
            backup_data['error'] = str(e)

        return backup_data

    def run(self, source_config: Dict[str, str], dest_config: Dict[str, str],
            discovery_data: Optional[Dict] = None) -> Dict[str, any]:
        """
        Run complete validation process.

        Args:
            source_config: Source database configuration
            dest_config: Destination database configuration
            discovery_data: Optional discovery data from Discovery Agent

        Returns:
            Dictionary containing complete validation report
        """
        logger.info("Validation Agent starting...")

        result = {
            'status': 'running',
            'sample_backups': {},
            'test_migration': {},
            'recommendations': {}
        }

        try:
            # Create sample backups
            logger.info("Creating sample backups...")
            source_backup = self.create_sample_backups(source_config, 'public')
            dest_backup = self.create_sample_backups(dest_config, 'public')

            result['sample_backups'] = {
                'source': source_backup,
                'destination': dest_backup
            }

            # Select and perform test migration
            logger.info("Selecting test table...")
            test_table = self.select_test_table(source_config, 'public')

            if test_table:
                logger.info("Performing test migration...")
                test_result = self.perform_test_migration(
                    source_config, dest_config, test_table
                )
                result['test_migration'] = test_result
            else:
                logger.warning("No suitable test table found")
                result['test_migration'] = {
                    'error': 'No suitable table found for test migration'
                }

            # Store validation data
            self.validation_data = result

            # Generate recommendations using GPTe
            logger.info("Generating validation recommendations...")
            recommendations = self._generate_recommendations(discovery_data)
            result['recommendations'] = recommendations

            result['status'] = 'completed'

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            result['status'] = 'failed'
            result['error'] = str(e)

        return result

    def _generate_recommendations(self, discovery_data: Optional[Dict] = None) -> Dict[str, any]:
        """
        Use GPTe to analyze validation results and generate recommendations.

        Args:
            discovery_data: Optional discovery data for context

        Returns:
            Dictionary containing AI-generated recommendations
        """
        logger.info("Generating recommendations with GPTe...")

        role = """Analyze the validation results from a test database migration.
        Review the sample backups and test migration results to assess data integrity
        and identify potential issues for the full migration."""

        tasks = [
            "Assess the success of the test migration",
            "Analyze data integrity validation results (row counts, checksums, sample data)",
            "Identify any data loss or corruption issues",
            "Evaluate the reliability of the migration process",
            "Determine if the migration is ready to proceed to the generation phase",
            "Provide specific recommendations for the full migration",
            "Highlight any risks or concerns that need to be addressed"
        ]

        context = {
            'validation_results': self.validation_data
        }

        if discovery_data:
            context['discovery_data'] = discovery_data

        response = self.client.send_agent_prompt(
            agent_name="Validation Agent",
            role=role,
            tasks=tasks,
            context=context
        )

        if not response['success']:
            logger.error("Failed to generate recommendations")
            return {
                'error': response.get('error', 'Unknown error'),
                'recommendations': 'Failed to generate recommendations'
            }

        # Try to parse structured response
        parsed = self.client.parse_json_response(response['response'])
        if parsed:
            return parsed

        # Return raw response if parsing fails
        return {
            'recommendations': response['response'],
            'raw': True
        }

    def get_summary(self) -> Dict[str, any]:
        """
        Get a summary of validation findings.

        Returns:
            Dictionary containing validation summary
        """
        if not self.validation_data:
            return {'error': 'No validation data available'}

        test_migration = self.validation_data.get('test_migration', {})
        validation = test_migration.get('validation', {})

        return {
            'test_migration_performed': bool(test_migration),
            'test_table': test_migration.get('table', 'N/A'),
            'migration_success': test_migration.get('migration', {}).get('success', False),
            'validation_passed': validation.get('validation_passed', False),
            'sample_backups_created': 'sample_backups' in self.validation_data
        }
