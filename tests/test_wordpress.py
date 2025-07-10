import pytest
from unittest.mock import patch

def test_create_wordpress_post(client, mocker):
    """Test creating a WordPress post"""
    mock_wp_cli = mocker.patch('agent.run_wp_cli_command')
    mock_wp_cli.return_value = "123"  # Mocked post ID

    response = client.post('/a2a/task',
        headers={'X-API-KEY': 'test-key'},
        json={
            'tool': 'create_wordpress_post',
            'args': {
                'title': 'Test Post',
                'content': 'Test Content'
            }
        }
    )
    
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert response.json['post_id'] == "123"

def test_get_system_information(client, mocker):
    """Test getting system information"""
    mock_wp_cli = mocker.patch('agent.run_wp_cli_command')
    mock_wp_cli.return_value = '{"php_version": "8.2"}'

    response = client.post('/a2a/task',
        headers={'X-API-KEY': 'test-key'},
        json={'tool': 'get_system_information'}
    )
    
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'php_version' in response.json['data']