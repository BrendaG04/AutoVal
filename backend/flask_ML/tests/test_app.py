import pytest
import sys
import os

# Add the parent directory (flask_ML root) to path so we can import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module


@pytest.fixture
def client():
    """Test client fixture for the Flask app."""
    app_module.app.config['TESTING'] = True
    with app_module.app.test_client() as test_client:
        yield test_client


class TestCarOptions:
    """Tests for the GET /api/car_options endpoint."""
    
    def test_car_options_returns_200(self, client):
        """Test that GET /api/car_options returns 200 status code."""
        response = client.get('/api/car_options')
        assert response.status_code == 200
    
    def test_car_options_structure(self, client):
        """Test that response has all expected keys."""
        response = client.get('/api/car_options')
        data = response.get_json()
        
        expected_keys = {
            'brands_models',
            'fuel_types',
            'transmissions',
            'conditions',
            'drive_types',
            'vehicle_types',
        }
        assert set(data.keys()) == expected_keys, \
            f"Expected keys {expected_keys}, got {set(data.keys())}"
    
    def test_car_options_has_brands(self, client):
        """Test that brands_models has at least 30 brands."""
        response = client.get('/api/car_options')
        data = response.get_json()
        
        brands_models = data.get('brands_models', {})
        assert isinstance(brands_models, dict), \
            f"brands_models should be a dict, got {type(brands_models)}"
        assert len(brands_models) >= 30, \
            f"Expected at least 30 brands, got {len(brands_models)}"


class TestPredict:
    """Tests for the POST /predict endpoint."""
    
    def test_predict_success(self, client):
        """Test POST /predict with valid 2020 Toyota Camry data returns 200 + prediction field."""
        payload = {
            'year': 2020,
            'manufacturer': 'toyota',
            'model': 'camry',
            'odometer': 50000,
            'fuel': 'gas',
            'transmission': 'automatic',
            'condition': 'good',
            'drive': 'fwd',
            'type': 'sedan',
            'cylinders': '4 cylinders',
            'title_status': 'clean',
        }
        response = client.post('/predict', json=payload)
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'prediction' in data, \
            f"Response missing 'prediction' field. Got: {data}"
        assert 'status' in data, \
            f"Response missing 'status' field. Got: {data}"
        assert data['status'] == 'success'
        assert isinstance(data['prediction'], (int, float))
    
    def test_predict_price_range(self, client):
        """Test that prediction is between $500 and $65000 (the price cap)."""
        payload = {
            'year': 2020,
            'manufacturer': 'toyota',
            'model': 'camry',
            'odometer': 50000,
            'fuel': 'gas',
            'transmission': 'automatic',
            'condition': 'good',
            'drive': 'fwd',
            'type': 'sedan',
            'cylinders': '4 cylinders',
            'title_status': 'clean',
        }
        response = client.post('/predict', json=payload)
        data = response.get_json()
        prediction = data['prediction']
        
        assert 500 <= prediction <= 65000, \
            f"Prediction {prediction} is outside expected range [500, 65000]"
    
    def test_predict_missing_mileage(self, client):
        """Test that POST /predict returns 400 when odometer/mileage is missing."""
        payload = {
            'year': 2020,
            'manufacturer': 'toyota',
            'model': 'camry',
            'fuel': 'gas',
            'transmission': 'automatic',
            'condition': 'good',
            'drive': 'fwd',
            'type': 'sedan',
        }
        response = client.post('/predict', json=payload)
        assert response.status_code == 400
        
        data = response.get_json()
        assert 'error' in data, \
            f"Response should have 'error' field. Got: {data}"
        assert 'mileage' in data['error'].lower() or 'odometer' in data['error'].lower(), \
            f"Error message should mention mileage/odometer. Got: {data['error']}"
    
    def test_predict_different_cars(self, client):
        """Test that a BMW X5 returns higher price than a Honda Civic."""
        civic_payload = {
            'year': 2020,
            'manufacturer': 'honda',
            'model': 'civic',
            'odometer': 50000,
            'fuel': 'gas',
            'transmission': 'automatic',
            'condition': 'good',
            'drive': 'fwd',
            'type': 'sedan',
            'cylinders': '4 cylinders',
            'title_status': 'clean',
        }
        
        bmw_payload = {
            'year': 2020,
            'manufacturer': 'bmw',
            'model': 'x5',
            'odometer': 50000,
            'fuel': 'gas',
            'transmission': 'automatic',
            'condition': 'good',
            'drive': 'awd',
            'type': 'suv',
            'cylinders': '6 cylinders',
            'title_status': 'clean',
        }
        
        civic_response = client.post('/predict', json=civic_payload)
        bmw_response = client.post('/predict', json=bmw_payload)
        
        assert civic_response.status_code == 200
        assert bmw_response.status_code == 200
        
        civic_price = civic_response.get_json()['prediction']
        bmw_price = bmw_response.get_json()['prediction']
        
        assert bmw_price > civic_price, \
            f"BMW X5 price ({bmw_price}) should be higher than Honda Civic price ({civic_price})"
