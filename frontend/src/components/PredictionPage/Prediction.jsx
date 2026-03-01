import React, { useState, useEffect } from 'react';
import { useAuth } from '../Favorites/useAuth.js';
import './Prediction.css';
import { addPrediction } from '../../services/sbServices';
import { useNavigate } from 'react-router-dom';

const FLASK_API_URL = import.meta.env.VITE_FLASK_API_URL || 'http://localhost:5000';

function Prediction() {
  const navigate = useNavigate();

  const [carData, setCarData] = useState({
    brand: "",
    model: "",
    year: 2021,
    odometer: 30000,
    fuel: "",
    transmission: "",
    condition: "",
    drive: "",
    type: "",
    cylinders: "4 cylinders",
    clean_title: true,
  });

  const [prediction, setPrediction] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [optionsLoading, setOptionsLoading] = useState(true);
  const [error, setError] = useState(null);

  const { isAuthenticated } = useAuth();

  const [dropdownOptions, setDropdownOptions] = useState({
    brands: [],
    models: [],
    fuelTypes: [],
    transmissions: [],
    conditions: [],
    driveTypes: [],
    vehicleTypes: [],
  });

  useEffect(() => {
    const fetchOptions = async () => {
      try {
        const response = await fetch(`${FLASK_API_URL}/api/car_options`);

        if (!response.ok) {
          throw new Error('Failed to fetch car options');
        }

        const data = await response.json();

        const brandNames = Object.keys(data.brands_models).sort();

        sessionStorage.setItem('brandsModels', JSON.stringify(data.brands_models));

        setDropdownOptions({
          brands: brandNames,
          models: [],
          fuelTypes: data.fuel_types || [],
          transmissions: data.transmissions || [],
          conditions: data.conditions || [],
          driveTypes: data.drive_types || [],
          vehicleTypes: data.vehicle_types || [],
        });
      } catch (err) {
        setError('Failed to load car options.');
      } finally {
        setOptionsLoading(false);
      }
    };

    fetchOptions();
  }, []);

  const handleBrandChange = (e) => {
    const brand = e.target.value;
    const brandsModels = JSON.parse(sessionStorage.getItem('brandsModels'));

    setCarData(prev => ({
      ...prev,
      brand,
      model: ""
    }));

    const sortedModels = brandsModels?.[brand]
      ? [...brandsModels[brand]].sort((a, b) => a.localeCompare(b))
      : [];

    setDropdownOptions(prev => ({
      ...prev,
      models: sortedModels
    }));
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setCarData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleNumberChange = (name, value) => {
    let processedValue = parseFloat(value);

    if (name === 'odometer') {
      processedValue = Math.min(processedValue, 300000);
    }

    setCarData(prev => ({
      ...prev,
      [name]: isNaN(processedValue) ? "" : processedValue
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    await handlePredict();
  };

  const handlePredict = async () => {
    try {
      setError(null);
      setIsLoading(true);

      const payload = {
        manufacturer: carData.brand,
        model: carData.model,
        year: Number(carData.year ?? 0),
        odometer: Number(carData.odometer ?? 0),
        fuel: carData.fuel,
        transmission: carData.transmission,
        condition: carData.condition,
        drive: carData.drive,
        type: carData.type,
        cylinders: carData.cylinders,
        clean_title: Boolean(carData.clean_title),
      };

      const response = await fetch(`${FLASK_API_URL}/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await response.json().catch(() => null);

      if (!response.ok) {
        setError(data?.error || "Prediction failed. Please try again.");
        return;
      }

      setPrediction(data?.prediction ?? null);
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const savePrediction = async () => {
    const saveData = {
      brand: carData.brand,
      model: carData.model,
      mileage: Number(carData.odometer ?? 0),
      engine: 0,
      modelYear: Number(carData.year ?? 0),
      fuelType: carData.fuel,
      transmission: carData.transmission,
      cleanTitle: Boolean(carData.clean_title),
      hasAccident: false,
      predictedPrice: Number(prediction ?? 0),
    };

    try {
      await addPrediction(saveData);
      navigate('/favorites');
    } catch {
      setError("Failed to save prediction. Please log in first.");
    }
  };

  return (
    <div className="prediction-container">
      <h1 className="CarMakeInfo-Title">Car Price Prediction</h1>
      <p className="prediction-subtitle">Enter your vehicle details to get an instant AI-powered estimate</p>

      {error && <div className="error-banner">{error}</div>}

      {optionsLoading ? (
        <div className="options-loading">
          <span className="spinner" />
          <p>Loading car data… This may take a moment on first visit.</p>
        </div>
      ) : (
      <form className="form-grid" onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Brand</label>
          <select
            name="brand"
            value={carData.brand}
            onChange={handleBrandChange}
            required
          >
            <option value="">Select Brand</option>
            {dropdownOptions.brands.map(brand => (
              <option key={brand} value={brand}>{brand}</option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label>Model</label>
          <select
            name="model"
            value={carData.model}
            onChange={handleChange}
            disabled={!carData.brand}
            required
          >
            <option value="">{carData.brand ? "Select Model" : "Select brand first"}</option>
            {dropdownOptions.models.map(model => (
              <option key={model} value={model}>{model}</option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label>Fuel Type</label>
          <select
            name="fuel"
            value={carData.fuel}
            onChange={handleChange}
            required
          >
            <option value="">Select Fuel Type</option>
            {dropdownOptions.fuelTypes.map(fuel => (
              <option key={fuel} value={fuel}>{fuel}</option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label>Transmission</label>
          <select
            name="transmission"
            value={carData.transmission}
            onChange={handleChange}
            required
          >
            <option value="">Select Transmission</option>
            {dropdownOptions.transmissions.map(trans => (
              <option key={trans} value={trans}>{trans}</option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label>Condition</label>
          <select
            name="condition"
            value={carData.condition}
            onChange={handleChange}
            required
          >
            <option value="">Select Condition</option>
            {dropdownOptions.conditions.map(cond => (
              <option key={cond} value={cond}>{cond}</option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label>Drive Type</label>
          <select
            name="drive"
            value={carData.drive}
            onChange={handleChange}
            required
          >
            <option value="">Select Drive Type</option>
            {dropdownOptions.driveTypes.map(d => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label>Vehicle Type</label>
          <select
            name="type"
            value={carData.type}
            onChange={handleChange}
            required
          >
            <option value="">Select Vehicle Type</option>
            {dropdownOptions.vehicleTypes.map(t => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label>Cylinders</label>
          <select
            name="cylinders"
            value={carData.cylinders}
            onChange={handleChange}
          >
            <option value="3 cylinders">3 Cylinders</option>
            <option value="4 cylinders">4 Cylinders</option>
            <option value="5 cylinders">5 Cylinders</option>
            <option value="6 cylinders">6 Cylinders</option>
            <option value="8 cylinders">8 Cylinders</option>
            <option value="10 cylinders">10 Cylinders</option>
            <option value="12 cylinders">12 Cylinders</option>
          </select>
        </div>

        <div className="form-group">
          <div className="range-display">
            <label>Model Year</label>
            <span className="range-value">{carData.year}</span>
          </div>
          <input
            type="range"
            name="year"
            min="2000"
            max={new Date().getFullYear()}
            value={carData.year}
            onChange={(e) => handleChange({
              target: {
                name: 'year',
                value: parseInt(e.target.value)
              }
            })}
          />
        </div>

        <div className="form-group">
          <div className="range-display">
            <label>Mileage</label>
            <span className="range-value">{carData.odometer?.toLocaleString() ?? 0} mi</span>
          </div>
          <input
            type="range"
            name="odometer"
            min="0"
            max="300000"
            step="1000"
            value={carData.odometer}
            onChange={(e) => handleNumberChange('odometer', e.target.value)}
          />
        </div>

        <div className="form-group checkbox-group">
          <label>
            <input
              type="checkbox"
              name="clean_title"
              checked={carData.clean_title}
              onChange={handleChange}
            />
            Clean Title
          </label>
        </div>

        <button type="submit" className="predict-button" disabled={isLoading}>
          {isLoading ? (
            <span className="spinner-wrapper">
              <span className="spinner" />
              Predicting…
            </span>
          ) : (
            "Predict Price"
          )}
        </button>
      </form>
      )}

      {prediction !== null && (
        <div className="prediction-result">
          <h2>Estimated Price: ${prediction.toLocaleString()}</h2>
          {isAuthenticated ? (
            <button onClick={savePrediction} className="save-button">
              Save to Favorites
            </button>
          ) : (
            <p className="login-prompt">
              <a href="/login">Log in</a> to save this prediction.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export default Prediction;