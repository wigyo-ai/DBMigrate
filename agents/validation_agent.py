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

        logger.info(f"╔═══════════════════════════════════════════════════════════════")
        logger.info(f"║ TEST MIGRATION: {schema}.{table}")
        logger.info(f"║ Max rows to migrate: {max_rows}")
        logger.info(f"╚═══════════════════════════════════════════════════════════════")

        result = {
            'table': f"{schema}.{table}",
            'migration': {},
            'validation': {}
        }

        try:
            # Perform migration with limited rows for testing
            logger.info(f"→ Step 1: Migrating table structure and data...")
            migration_result = migrate_table(
                source_config, dest_config, schema, table,
                batch_size=100, max_rows=max_rows
            )
            result['migration'] = migration_result

            if not migration_result['success']:
                logger.error(f"✗ FAILED: Test migration failed")
                logger.error(f"  Error: {migration_result.get('error')}")
                logger.error(f"  Rows migrated before failure: {migration_result.get('rows_migrated', 0)}")
                return result

            logger.info(f"✓ PASSED: Migration completed successfully")
            logger.info(f"  Total rows: {migration_result.get('total_rows', 0)}")
            logger.info(f"  Rows migrated: {migration_result.get('rows_migrated', 0)}")

            # Validate migration
            logger.info(f"→ Step 2: Validating migrated data...")
            validation_result = validate_migration(
                source_config, dest_config, schema, table
            )
            result['validation'] = validation_result

            if validation_result.get('validation_passed'):
                logger.info(f"✓ PASSED: All validation checks passed")
            else:
                logger.error(f"✗ FAILED: Validation checks failed")

            # Log detailed validation results
            self._log_validation_details(validation_result)

        except Exception as e:
            logger.error(f"✗ FAILED: Test migration error: {e}")
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
        logger.info(f"→ Creating sample backup for schema '{schema}'...")

        backup_data = {
            'schema': schema,
            'tables': []
        }

        try:
            tables = get_tables(config, schema)
            logger.info(f"  Found {len(tables)} tables in schema")

            # Sample up to 5 tables
            sample_tables = tables[:5] if len(tables) > 5 else tables
            logger.info(f"  Sampling {len(sample_tables)} tables for backup")

            for i, table_info in enumerate(sample_tables, 1):
                table_name = table_info['table_name']
                try:
                    logger.info(f"  [{i}/{len(sample_tables)}] Processing table: {table_name}")
                    row_count = get_row_count(config, schema, table_name)
                    sample_data = get_sample_data(config, schema, table_name, limit=3)
                    checksum = calculate_table_checksum(config, schema, table_name, sample_size=100)

                    backup_data['tables'].append({
                        'table': table_name,
                        'row_count': row_count,
                        'sample_data': sample_data,
                        'checksum': checksum
                    })
                    logger.info(f"    ✓ Row count: {row_count}, Checksum: {checksum[:8]}...")
                except Exception as e:
                    logger.warning(f"    ✗ Failed to backup table {table_name}: {e}")
                    backup_data['tables'].append({
                        'table': table_name,
                        'error': str(e)
                    })

            logger.info(f"✓ Sample backup completed: {len([t for t in backup_data['tables'] if 'error' not in t])}/{len(sample_tables)} tables successful")

        except Exception as e:
            logger.error(f"✗ Sample backup failed: {e}")
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
        logger.info("═" * 70)
        logger.info("VALIDATION AGENT STARTING")
        logger.info("═" * 70)

        result = {
            'status': 'running',
            'sample_backups': {},
            'test_migration': {},
            'recommendations': {}
        }

        try:
            # Create sample backups
            logger.info("")
            logger.info("PHASE 1: CREATING SAMPLE BACKUPS")
            logger.info("─" * 70)
            logger.info("→ Backing up SOURCE database...")
            source_backup = self.create_sample_backups(source_config, 'public')
            logger.info("")
            logger.info("→ Backing up DESTINATION database...")
            dest_backup = self.create_sample_backups(dest_config, 'public')

            result['sample_backups'] = {
                'source': source_backup,
                'destination': dest_backup
            }

            # Select and perform test migration
            logger.info("")
            logger.info("PHASE 2: TEST MIGRATION")
            logger.info("─" * 70)
            logger.info("→ Selecting test table...")
            test_table = self.select_test_table(source_config, 'public')

            if test_table:
                logger.info(f"  Selected: {test_table['schema']}.{test_table['table']} ({test_table['size']})")
                logger.info("")
                test_result = self.perform_test_migration(
                    source_config, dest_config, test_table
                )
                result['test_migration'] = test_result
            else:
                logger.warning("✗ No suitable test table found")
                result['test_migration'] = {
                    'error': 'No suitable table found for test migration'
                }

            # Store validation data
            self.validation_data = result

            # Generate recommendations using GPTe
            logger.info("")
            logger.info("PHASE 3: GENERATING AI RECOMMENDATIONS")
            logger.info("─" * 70)
            recommendations = self._generate_recommendations(discovery_data)
            result['recommendations'] = recommendations
            logger.info("✓ Recommendations generated")

            result['status'] = 'completed'
            logger.info("")
            logger.info("═" * 70)
            logger.info("✓ VALIDATION AGENT COMPLETED SUCCESSFULLY")
            logger.info("═" * 70)

        except Exception as e:
            logger.error(f"✗ VALIDATION AGENT FAILED: {e}")
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

    def _log_validation_details(self, validation_result: Dict[str, any]):
        """
        Log detailed validation check results.

        Args:
            validation_result: Dictionary containing validation results
        """
        checks = validation_result.get('checks', {})

        logger.info("  " + "─" * 60)
        logger.info("  VALIDATION CHECKS DETAIL:")
        logger.info("  " + "─" * 60)

        # Row Count Check
        if 'row_count' in checks:
            row_check = checks['row_count']
            source_count = row_check.get('source', 0)
            dest_count = row_check.get('destination', 0)
            match = row_check.get('match', False)

            if match:
                logger.info(f"  ✓ ROW COUNT CHECK: PASSED")
                logger.info(f"    Source: {source_count} rows")
                logger.info(f"    Destination: {dest_count} rows")
            else:
                logger.error(f"  ✗ ROW COUNT CHECK: FAILED")
                logger.error(f"    Source: {source_count} rows")
                logger.error(f"    Destination: {dest_count} rows")
                logger.error(f"    Difference: {abs(source_count - dest_count)} rows")

        # Checksum Check
        if 'checksum' in checks:
            checksum_check = checks['checksum']
            source_checksum = checksum_check.get('source', '')
            dest_checksum = checksum_check.get('destination', '')
            match = checksum_check.get('match', False)

            if match:
                logger.info(f"  ✓ CHECKSUM CHECK: PASSED")
                logger.info(f"    Source: {source_checksum[:16]}...")
                logger.info(f"    Destination: {dest_checksum[:16]}...")
            else:
                logger.error(f"  ✗ CHECKSUM CHECK: FAILED")
                logger.error(f"    Source: {source_checksum}")
                logger.error(f"    Destination: {dest_checksum}")
                logger.error(f"    Data integrity issue detected!")

        # Sample Data Check
        if 'sample_data' in checks:
            sample_check = checks['sample_data']
            source_sample_count = sample_check.get('source_count', 0)
            dest_sample_count = sample_check.get('destination_count', 0)
            match = sample_check.get('match', False)

            if match:
                logger.info(f"  ✓ SAMPLE DATA CHECK: PASSED")
                logger.info(f"    Compared {source_sample_count} sample rows")
            else:
                logger.error(f"  ✗ SAMPLE DATA CHECK: FAILED")
                logger.error(f"    Source samples: {source_sample_count}")
                logger.error(f"    Destination samples: {dest_sample_count}")
                logger.error(f"    Sample data mismatch detected!")

        logger.info("  " + "─" * 60)

        # Overall Result
        overall = validation_result.get('validation_passed', False)
        if overall:
            logger.info("  ✓ OVERALL VALIDATION: PASSED - All checks successful")
        else:
            logger.error("  ✗ OVERALL VALIDATION: FAILED - One or more checks failed")

        logger.info("  " + "─" * 60)

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
