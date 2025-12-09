"""
Discovery Agent
Discovers and analyzes source and destination PostgreSQL databases.
"""

import logging
from typing import Dict
import json
from db_operations import (
    test_connection, get_database_size, get_database_version,
    get_database_settings, get_schemas, get_tables
)
from gpte_client import GPTeClient

logger = logging.getLogger(__name__)


class DiscoveryAgent:
    """Agent responsible for discovering database structure and configuration."""

    def __init__(self, gpte_client: GPTeClient):
        """
        Initialize Discovery Agent.

        Args:
            gpte_client: Configured GPTe client for AI assistance
        """
        self.client = gpte_client
        self.discovery_data = {}

    def discover_database(self, config: Dict[str, str], db_label: str) -> Dict[str, any]:
        """
        Discover database information.

        Args:
            config: Database configuration dictionary
            db_label: Label for the database (e.g., "source" or "destination")

        Returns:
            Dictionary containing discovery results
        """
        logger.info(f"Starting discovery for {db_label} database")
        result = {
            'label': db_label,
            'connection': {},
            'version': '',
            'size': {},
            'settings': {},
            'schemas': [],
            'tables': {}
        }

        try:
            # Test connection
            conn_success, conn_msg = test_connection(config)
            result['connection'] = {
                'success': conn_success,
                'message': conn_msg
            }

            if not conn_success:
                logger.error(f"Connection failed for {db_label}: {conn_msg}")
                return result

            # Get version
            result['version'] = get_database_version(config)
            logger.info(f"{db_label} version: {result['version']}")

            # Get size
            result['size'] = get_database_size(config)
            logger.info(f"{db_label} size: {result['size'].get('size_pretty', 'Unknown')}")

            # Get important settings
            result['settings'] = get_database_settings(config)

            # Get schemas
            result['schemas'] = get_schemas(config)
            logger.info(f"{db_label} schemas: {', '.join(result['schemas'])}")

            # Get tables for each schema
            for schema in result['schemas']:
                tables = get_tables(config, schema)
                result['tables'][schema] = tables
                logger.info(f"{db_label} schema '{schema}' has {len(tables)} tables")

        except Exception as e:
            logger.error(f"Discovery failed for {db_label}: {e}")
            result['error'] = str(e)

        return result

    def run(self, source_config: Dict[str, str], dest_config: Dict[str, str]) -> Dict[str, any]:
        """
        Run complete discovery process for both databases.

        Args:
            source_config: Source database configuration
            dest_config: Destination database configuration

        Returns:
            Dictionary containing complete discovery report
        """
        logger.info("Discovery Agent starting...")

        # Discover source database
        source_data = self.discover_database(source_config, "source")

        # Discover destination database
        dest_data = self.discover_database(dest_config, "destination")

        # Store discovery data
        self.discovery_data = {
            'source': source_data,
            'destination': dest_data
        }

        # Generate comparison report using GPTe
        comparison_report = self._generate_comparison_report()

        return {
            'status': 'completed',
            'source': source_data,
            'destination': dest_data,
            'comparison': comparison_report
        }

    def _generate_comparison_report(self) -> Dict[str, any]:
        """
        Use GPTe to analyze and compare source and destination databases.

        Returns:
            Dictionary containing AI-generated comparison analysis
        """
        logger.info("Generating comparison report with GPTe...")

        role = """Analyze and compare two PostgreSQL databases (source and destination)
        to prepare for a migration. Identify compatibility issues, size differences,
        schema mismatches, and potential migration risks."""

        tasks = [
            "Compare PostgreSQL versions and identify compatibility concerns",
            "Compare database sizes and estimate storage requirements",
            "Identify schemas that exist in source but not in destination",
            "Identify tables that exist in source but not in destination",
            "Compare table structures for common tables",
            "Assess overall migration feasibility and complexity",
            "Provide recommendations for the migration approach"
        ]

        response = self.client.send_agent_prompt(
            agent_name="Discovery Agent",
            role=role,
            tasks=tasks,
            context=self.discovery_data
        )

        if not response['success']:
            logger.error("Failed to generate comparison report")
            return {
                'error': response.get('error', 'Unknown error'),
                'analysis': 'Failed to generate analysis'
            }

        # Try to parse structured response
        parsed = self.client.parse_json_response(response['response'])
        if parsed:
            return parsed

        # Return raw response if parsing fails
        return {
            'analysis': response['response'],
            'raw': True
        }

    def get_summary(self) -> Dict[str, any]:
        """
        Get a summary of discovery findings.

        Returns:
            Dictionary containing discovery summary
        """
        if not self.discovery_data:
            return {'error': 'No discovery data available'}

        source = self.discovery_data.get('source', {})
        dest = self.discovery_data.get('destination', {})

        # Count total tables
        source_table_count = sum(len(tables) for tables in source.get('tables', {}).values())
        dest_table_count = sum(len(tables) for tables in dest.get('tables', {}).values())

        return {
            'source': {
                'connected': source.get('connection', {}).get('success', False),
                'version': source.get('version', 'Unknown'),
                'size': source.get('size', {}).get('size_pretty', 'Unknown'),
                'schemas': len(source.get('schemas', [])),
                'tables': source_table_count
            },
            'destination': {
                'connected': dest.get('connection', {}).get('success', False),
                'version': dest.get('version', 'Unknown'),
                'size': dest.get('size', {}).get('size_pretty', 'Unknown'),
                'schemas': len(dest.get('schemas', [])),
                'tables': dest_table_count
            }
        }
