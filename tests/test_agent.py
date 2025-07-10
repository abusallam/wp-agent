import pytest
import json
from unittest.mock import patch

def test_health_check(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json['status'] == 'healthy'

def test_missing_api_key(client):
    response = client.post('/a2a/task', 
                         json={'tool': 'get_system_information'})
    assert response.status_code == 401

def test_get_system_information(client, mock_wp_cli):
    mock_wp_cli.return_value = '{"php_version": "7.4"}'
    
    headers = {'X-API-KEY': 'test-key'}
    response = client.post('/a2a/task',
                         headers=headers,
                         json={'tool': 'get_system_information'})
    
    assert response.status_code == 200
    assert response.json['status'] == 'success'