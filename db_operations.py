"""
PostgreSQL Database Operations Module
Provides reusable functions for database discovery, migration, and validation.
"""

import psycopg2
from psycopg2 import sql, extras
import logging
from typing import Dict, List, Tuple, Optional
import hashlib
import json

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Manages PostgreSQL database connections with proper error handling."""

    def __init__(self, config: Dict[str, str]):
        """
        Initialize database connection.

        Args:
            config: Dictionary containing host, port, database, user, password, sslmode
        """
        self.config = config
        self.conn = None
        self.cursor = None

    def __enter__(self):
        """Context manager entry - establish connection."""
        try:
            self.conn = psycopg2.connect(
                host=self.config['host'],
                port=self.config.get('port', 5432),
                database=self.config['database'],
                user=self.config['user'],
                password=self.config['password'],
                sslmode=self.config.get('sslmode', 'prefer'),
                connect_timeout=10
            )
            self.cursor = self.conn.cursor(cursor_factory=extras.RealDictCursor)
            return self
        except psycopg2.Error as e:
            logger.error(f"Database connection failed: {e}")
            raise ConnectionError(f"Failed to connect to database: {str(e)}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

    def execute_query(self, query: str, params: Tuple = None) -> List[Dict]:
        """
        Execute a SELECT query and return results.

        Args:
            query: SQL query string
            params: Query parameters (for parameterized queries)

        Returns:
            List of dictionaries containing query results
        """
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except psycopg2.Error as e:
            logger.error(f"Query execution failed: {e}")
            raise

    def execute_command(self, command: str, params: Tuple = None):
        """
        Execute a non-SELECT command (INSERT, UPDATE, DELETE, etc.).

        Args:
            command: SQL command string
            params: Command parameters
        """
        try:
            self.cursor.execute(command, params)
            self.conn.commit()
        except psycopg2.Error as e:
            self.conn.rollback()
            logger.error(f"Command execution failed: {e}")
            raise


def test_connection(config: Dict[str, str]) -> Tuple[bool, str]:
    """
    Test database connection.

    Args:
        config: Database configuration dictionary

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        with DatabaseConnection(config):
            return True, "Connection successful"
    except Exception as e:
        return False, str(e)


def get_database_size(config: Dict[str, str]) -> Dict[str, any]:
    """
    Get database size information.

    Args:
        config: Database configuration dictionary

    Returns:
        Dictionary containing size information
    """
    with DatabaseConnection(config) as db:
        query = """
            SELECT
                pg_database.datname as database_name,
                pg_size_pretty(pg_database_size(pg_database.datname)) as size_pretty,
                pg_database_size(pg_database.datname) as size_bytes
            FROM pg_database
            WHERE datname = current_database()
        """
        result = db.execute_query(query)
        return dict(result[0]) if result else {}


def get_database_version(config: Dict[str, str]) -> str:
    """
    Get PostgreSQL version.

    Args:
        config: Database configuration dictionary

    Returns:
        Version string
    """
    with DatabaseConnection(config) as db:
        result = db.execute_query("SELECT version()")
        return result[0]['version'] if result else "Unknown"


def get_database_settings(config: Dict[str, str]) -> Dict[str, str]:
    """
    Get important database configuration settings.

    Args:
        config: Database configuration dictionary

    Returns:
        Dictionary of settings
    """
    with DatabaseConnection(config) as db:
        query = """
            SELECT name, setting, unit, category
            FROM pg_settings
            WHERE category IN (
                'Resource Usage / Memory',
                'Write-Ahead Log / Settings',
                'Replication / Sending Servers',
                'Client Connection Defaults / Locale and Formatting'
            )
            ORDER BY category, name
        """
        results = db.execute_query(query)
        return {row['name']: row['setting'] for row in results}


def get_schemas(config: Dict[str, str]) -> List[str]:
    """
    Get all schemas in the database (excluding system schemas).

    Args:
        config: Database configuration dictionary

    Returns:
        List of schema names
    """
    with DatabaseConnection(config) as db:
        query = """
            SELECT schema_name
            FROM information_schema.schemata
            WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
            ORDER BY schema_name
        """
        results = db.execute_query(query)
        return [row['schema_name'] for row in results]


def get_tables(config: Dict[str, str], schema: str = 'public') -> List[Dict[str, any]]:
    """
    Get all tables in a schema with metadata.

    Args:
        config: Database configuration dictionary
        schema: Schema name (default: 'public')

    Returns:
        List of dictionaries containing table information
    """
    with DatabaseConnection(config) as db:
        query = """
            SELECT
                t.table_schema,
                t.table_name,
                pg_size_pretty(pg_total_relation_size(quote_ident(t.table_schema)||'.'||quote_ident(t.table_name))) as size,
                pg_total_relation_size(quote_ident(t.table_schema)||'.'||quote_ident(t.table_name)) as size_bytes,
                (SELECT COUNT(*) FROM information_schema.columns c
                 WHERE c.table_schema = t.table_schema AND c.table_name = t.table_name) as column_count
            FROM information_schema.tables t
            WHERE t.table_schema = %s AND t.table_type = 'BASE TABLE'
            ORDER BY size_bytes DESC
        """
        results = db.execute_query(query, (schema,))
        return [dict(row) for row in results]


def get_table_structure(config: Dict[str, str], schema: str, table: str) -> Dict[str, any]:
    """
    Get detailed table structure including columns, indexes, and constraints.

    Args:
        config: Database configuration dictionary
        schema: Schema name
        table: Table name

    Returns:
        Dictionary containing table structure details
    """
    with DatabaseConnection(config) as db:
        # Get columns
        columns_query = """
            SELECT
                column_name,
                data_type,
                character_maximum_length,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
        """
        columns = db.execute_query(columns_query, (schema, table))

        # Get indexes
        indexes_query = """
            SELECT
                indexname as index_name,
                indexdef as index_definition
            FROM pg_indexes
            WHERE schemaname = %s AND tablename = %s
        """
        indexes = db.execute_query(indexes_query, (schema, table))

        # Get constraints
        constraints_query = """
            SELECT
                tc.constraint_name,
                tc.constraint_type,
                kcu.column_name
            FROM information_schema.table_constraints tc
            LEFT JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            WHERE tc.table_schema = %s AND tc.table_name = %s
        """
        constraints = db.execute_query(constraints_query, (schema, table))

        return {
            'columns': [dict(col) for col in columns],
            'indexes': [dict(idx) for idx in indexes],
            'constraints': [dict(con) for con in constraints]
        }


def get_row_count(config: Dict[str, str], schema: str, table: str) -> int:
    """
    Get row count for a table.

    Args:
        config: Database configuration dictionary
        schema: Schema name
        table: Table name

    Returns:
        Number of rows
    """
    with DatabaseConnection(config) as db:
        query = sql.SQL("SELECT COUNT(*) as count FROM {}.{}").format(
            sql.Identifier(schema),
            sql.Identifier(table)
        )
        result = db.execute_query(query.as_string(db.conn))
        return result[0]['count'] if result else 0


def get_sample_data(config: Dict[str, str], schema: str, table: str, limit: int = 5) -> List[Dict]:
    """
    Get sample data from a table.

    Args:
        config: Database configuration dictionary
        schema: Schema name
        table: Table name
        limit: Number of rows to sample (default: 5)

    Returns:
        List of sample rows
    """
    with DatabaseConnection(config) as db:
        query = sql.SQL("SELECT * FROM {}.{} LIMIT %s").format(
            sql.Identifier(schema),
            sql.Identifier(table)
        )
        results = db.execute_query(query.as_string(db.conn), (limit,))
        return [dict(row) for row in results]


def calculate_table_checksum(config: Dict[str, str], schema: str, table: str, sample_size: int = 1000) -> str:
    """
    Calculate a checksum for table data (sampling for large tables).

    Args:
        config: Database configuration dictionary
        schema: Schema name
        table: Table name
        sample_size: Number of rows to sample for checksum

    Returns:
        MD5 checksum string
    """
    with DatabaseConnection(config) as db:
        # Get column names
        columns_query = """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
        """
        columns = db.execute_query(columns_query, (schema, table))
        column_names = [col['column_name'] for col in columns]

        # Create a concatenated column list for checksum
        concat_expr = ' || '.join([f'COALESCE(CAST({sql.Identifier(col).as_string(db.conn)} AS TEXT), \'NULL\')'
                                    for col in column_names])

        query = f"""
            SELECT MD5(STRING_AGG(row_data, '' ORDER BY row_data)) as checksum
            FROM (
                SELECT {concat_expr} as row_data
                FROM {sql.Identifier(schema).as_string(db.conn)}.{sql.Identifier(table).as_string(db.conn)}
                ORDER BY {sql.Identifier(column_names[0]).as_string(db.conn)}
                LIMIT %s
            ) subquery
        """

        result = db.execute_query(query, (sample_size,))
        return result[0]['checksum'] if result and result[0]['checksum'] else ''


def migrate_table(source_config: Dict[str, str], dest_config: Dict[str, str],
                  schema: str, table: str, batch_size: int = 1000, max_rows: int = None) -> Dict[str, any]:
    """
    Migrate a table from source to destination database.

    Args:
        source_config: Source database configuration
        dest_config: Destination database configuration
        schema: Schema name
        table: Table name
        batch_size: Number of rows to migrate per batch
        max_rows: Maximum number of rows to migrate (None for all rows)

    Returns:
        Dictionary containing migration results
    """
    total_rows = 0
    rows_migrated = 0

    try:
        # Get row count
        logger.info(f"    → Analyzing source table...")
        total_rows = get_row_count(source_config, schema, table)
        logger.info(f"      Total rows in source: {total_rows}")

        # Limit total rows if max_rows is specified
        if max_rows is not None:
            total_rows = min(total_rows, max_rows)
            logger.info(f"      Limited to: {total_rows} rows for testing")

        # Get table structure
        logger.info(f"    → Retrieving table structure...")
        structure = get_table_structure(source_config, schema, table)
        column_names = [col['column_name'] for col in structure['columns']]
        logger.info(f"      Columns: {len(column_names)}, Indexes: {len(structure.get('indexes', []))}, Constraints: {len(structure.get('constraints', []))}")

        # Create table in destination if it doesn't exist
        with DatabaseConnection(dest_config) as dest_db:
            # Check if table exists
            check_query = """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = %s AND table_name = %s
                )
            """
            exists = dest_db.execute_query(check_query, (schema, table))

            if not exists[0]['exists']:
                logger.info(f"    → Creating table in destination...")
                # Create table structure
                create_cols = []
                for col in structure['columns']:
                    col_def = f"{col['column_name']} {col['data_type']}"
                    if col['character_maximum_length']:
                        col_def += f"({col['character_maximum_length']})"
                    if col['is_nullable'] == 'NO':
                        col_def += " NOT NULL"
                    if col['column_default']:
                        col_def += f" DEFAULT {col['column_default']}"
                    create_cols.append(col_def)

                create_table = f"CREATE TABLE {schema}.{table} ({', '.join(create_cols)})"
                dest_db.execute_command(create_table)
                logger.info(f"      ✓ Table created successfully")
            else:
                logger.info(f"    → Table already exists in destination")

        # Migrate data in batches
        logger.info(f"    → Migrating data in batches of {batch_size}...")
        with DatabaseConnection(source_config) as source_db:
            with DatabaseConnection(dest_config) as dest_db:
                offset = 0
                batch_num = 0
                while offset < total_rows:
                    batch_num += 1
                    # Fetch batch from source
                    select_query = sql.SQL("SELECT * FROM {}.{} ORDER BY {} LIMIT %s OFFSET %s").format(
                        sql.Identifier(schema),
                        sql.Identifier(table),
                        sql.Identifier(column_names[0])
                    )
                    batch = source_db.execute_query(
                        select_query.as_string(source_db.conn),
                        (batch_size, offset)
                    )

                    if not batch:
                        break

                    # Insert batch into destination
                    batch_rows = 0
                    for row in batch:
                        placeholders = ','.join(['%s'] * len(column_names))
                        insert_query = f"INSERT INTO {schema}.{table} ({','.join(column_names)}) VALUES ({placeholders})"
                        values = tuple(row[col] for col in column_names)
                        dest_db.execute_command(insert_query, values)
                        rows_migrated += 1
                        batch_rows += 1

                    logger.info(f"      Batch {batch_num}: Migrated {batch_rows} rows (Total: {rows_migrated}/{total_rows})")
                    offset += batch_size

        logger.info(f"    ✓ Migration completed: {rows_migrated} rows migrated")
        return {
            'success': True,
            'total_rows': total_rows,
            'rows_migrated': rows_migrated,
            'message': f"Successfully migrated {rows_migrated} rows"
        }

    except Exception as e:
        logger.error(f"    ✗ Table migration failed: {e}")
        logger.error(f"      Rows migrated before failure: {rows_migrated}/{total_rows}")
        return {
            'success': False,
            'total_rows': total_rows,
            'rows_migrated': rows_migrated,
            'error': str(e),
            'message': f"Migration failed after {rows_migrated} rows: {str(e)}"
        }


def validate_migration(source_config: Dict[str, str], dest_config: Dict[str, str],
                       schema: str, table: str) -> Dict[str, any]:
    """
    Validate that a table was migrated correctly.

    Args:
        source_config: Source database configuration
        dest_config: Destination database configuration
        schema: Schema name
        table: Table name

    Returns:
        Dictionary containing validation results
    """
    results = {
        'table': f"{schema}.{table}",
        'checks': {}
    }

    try:
        logger.info(f"    → Running validation checks...")

        # Compare row counts
        logger.info(f"      Check 1/3: Comparing row counts...")
        source_count = get_row_count(source_config, schema, table)
        dest_count = get_row_count(dest_config, schema, table)
        row_match = source_count == dest_count
        results['checks']['row_count'] = {
            'source': source_count,
            'destination': dest_count,
            'match': row_match
        }
        if row_match:
            logger.info(f"        ✓ Row counts match: {source_count}")
        else:
            logger.error(f"        ✗ Row count mismatch! Source: {source_count}, Destination: {dest_count}")

        # Compare checksums
        logger.info(f"      Check 2/3: Comparing data checksums...")
        source_checksum = calculate_table_checksum(source_config, schema, table)
        dest_checksum = calculate_table_checksum(dest_config, schema, table)
        checksum_match = source_checksum == dest_checksum
        results['checks']['checksum'] = {
            'source': source_checksum,
            'destination': dest_checksum,
            'match': checksum_match
        }
        if checksum_match:
            logger.info(f"        ✓ Checksums match: {source_checksum[:16]}...")
        else:
            logger.error(f"        ✗ Checksum mismatch! Data integrity issue detected")

        # Compare sample data
        logger.info(f"      Check 3/3: Comparing sample data...")
        source_sample = get_sample_data(source_config, schema, table, 5)
        dest_sample = get_sample_data(dest_config, schema, table, 5)
        sample_match = source_sample == dest_sample
        results['checks']['sample_data'] = {
            'source_count': len(source_sample),
            'destination_count': len(dest_sample),
            'match': sample_match
        }
        if sample_match:
            logger.info(f"        ✓ Sample data matches ({len(source_sample)} rows compared)")
        else:
            logger.error(f"        ✗ Sample data mismatch detected!")

        # Overall validation
        all_checks_passed = all(
            check.get('match', False) for check in results['checks'].values()
        )
        results['validation_passed'] = all_checks_passed

        if all_checks_passed:
            logger.info(f"    ✓ All validation checks passed!")
        else:
            logger.error(f"    ✗ Validation failed: {sum(1 for c in results['checks'].values() if not c.get('match', False))}/3 checks failed")

    except Exception as e:
        logger.error(f"    ✗ Validation error: {e}")
        results['error'] = str(e)
        results['validation_passed'] = False

    return results
