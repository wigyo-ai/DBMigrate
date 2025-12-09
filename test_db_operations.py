"""
Basic tests for database operations module.
Run with: pytest test_db_operations.py
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from db_operations import (
    DatabaseConnection,
    test_connection,
    get_database_size,
    get_database_version
)


class TestDatabaseConnection:
    """Tests for DatabaseConnection context manager."""

    @patch('db_operations.psycopg2.connect')
    def test_connection_success(self, mock_connect):
        """Test successful database connection."""
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'user': 'postgres',
            'password': 'password',
            'sslmode': 'prefer'
        }

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        with DatabaseConnection(config) as db:
            assert db.conn == mock_conn
            assert db.cursor == mock_cursor

        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch('db_operations.psycopg2.connect')
    def test_connection_failure(self, mock_connect):
        """Test database connection failure."""
        config = {
            'host': 'invalid_host',
            'port': 5432,
            'database': 'test_db',
            'user': 'postgres',
            'password': 'password'
        }

        mock_connect.side_effect = Exception("Connection failed")

        with pytest.raises(ConnectionError):
            with DatabaseConnection(config) as db:
                pass


class TestConnectionTest:
    """Tests for test_connection function."""

    @patch('db_operations.DatabaseConnection')
    def test_connection_success(self, mock_db_conn):
        """Test successful connection test."""
        config = {'host': 'localhost'}
        mock_db_conn.return_value.__enter__ = Mock()
        mock_db_conn.return_value.__exit__ = Mock()

        success, message = test_connection(config)

        assert success is True
        assert message == "Connection successful"

    @patch('db_operations.DatabaseConnection')
    def test_connection_failure(self, mock_db_conn):
        """Test failed connection test."""
        config = {'host': 'invalid'}
        mock_db_conn.return_value.__enter__.side_effect = Exception("Failed")

        success, message = test_connection(config)

        assert success is False
        assert "Failed" in message


class TestDatabaseInfo:
    """Tests for database information functions."""

    @patch('db_operations.DatabaseConnection')
    def test_get_database_size(self, mock_db_conn):
        """Test getting database size."""
        config = {'host': 'localhost'}

        mock_db = Mock()
        mock_db.execute_query.return_value = [{
            'database_name': 'test_db',
            'size_pretty': '100 MB',
            'size_bytes': 104857600
        }]

        mock_db_conn.return_value.__enter__.return_value = mock_db
        mock_db_conn.return_value.__exit__ = Mock()

        result = get_database_size(config)

        assert result['database_name'] == 'test_db'
        assert result['size_pretty'] == '100 MB'
        assert result['size_bytes'] == 104857600

    @patch('db_operations.DatabaseConnection')
    def test_get_database_version(self, mock_db_conn):
        """Test getting database version."""
        config = {'host': 'localhost'}

        mock_db = Mock()
        mock_db.execute_query.return_value = [{
            'version': 'PostgreSQL 15.2'
        }]

        mock_db_conn.return_value.__enter__.return_value = mock_db
        mock_db_conn.return_value.__exit__ = Mock()

        result = get_database_version(config)

        assert result == 'PostgreSQL 15.2'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
