import pytest
from flask import url_for

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json['status'] == 'healthy'

def test_missing_api_key(client):
    """Test API key authentication"""
    response = client.post('/a2a/task', json={
        'tool': 'get_system_information'
    })
    assert response.status_code == 401

def test_invalid_tool(client):
    """Test invalid tool request"""
    response = client.post('/a2a/task', 
        headers={'X-API-KEY': 'test-key'},
        json={'tool': 'invalid_tool'}
    )
    assert response.status_code == 404