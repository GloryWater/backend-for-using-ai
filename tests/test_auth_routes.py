"""
Tests for auth routes.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from src.routes.auth import check_loader_version


class TestCheckLoaderVersion:
    """Tests for /loader/version endpoint."""

    @pytest.mark.asyncio
    async def test_check_loader_version_success(self):
        """Tests successful version check."""
        mock_version_data = {"version": "1.0.0", "url": "http://test.com/loader.lua"}
        
        mock_file = AsyncMock()
        mock_file.read = AsyncMock(return_value=json.dumps(mock_version_data))
        mock_file.__aenter__ = AsyncMock(return_value=mock_file)
        mock_file.__aexit__ = AsyncMock(return_value=None)
        
        with patch('src.routes.auth.aiofiles.open', return_value=mock_file):
            with patch('src.routes.auth.settings') as mock_settings:
                mock_settings.LOADER_VERSION_FILE = "loader_version.json"
                
                result = await check_loader_version()
                
                assert result.version == "1.0.0"
                assert result.url == "http://test.com/loader.lua"

    @pytest.mark.asyncio
    async def test_check_loader_version_invalid_json(self):
        """Tests version check with invalid JSON."""
        mock_file = AsyncMock()
        mock_file.read = AsyncMock(return_value="invalid json")
        mock_file.__aenter__ = AsyncMock(return_value=mock_file)
        mock_file.__aexit__ = AsyncMock(return_value=None)
        
        with patch('src.routes.auth.aiofiles.open', return_value=mock_file):
            with patch('src.routes.auth.settings') as mock_settings:
                mock_settings.LOADER_VERSION_FILE = "loader_version.json"
                
                with pytest.raises(Exception):  # json.JSONDecodeError
                    await check_loader_version()
