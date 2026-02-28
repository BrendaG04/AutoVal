import React, {useState, useEffect} from 'react';
import { useNavigate } from 'react-router-dom';
import { deletePrediction, getFavorites } from '../../services/sbServices';
import { useAuth } from './useAuth.js';
import './Favorites.css';

function Favorites() {
  const [favorites, setFavorites] = useState([]);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const { isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const fetchFavorites = async () => {
      try {
        setIsLoading(true);
        setError("");
        
        if (!isAuthenticated) {
          throw new Error("Please log in to view favorites");
        }

        const response = await getFavorites();
        setFavorites(response.data);
      } catch (err) {
        setError(err.response?.data?.message || err.message || "Failed to load favorites");
      } finally {
        setIsLoading(false);
      }
    };

    fetchFavorites();
  }, [isAuthenticated]);

  const formatBoolean = (val) => (val ? "Yes" : "No");

  const handleDeleteFavorite = async (carId) => {
    try {
      await deletePrediction(carId);
      setFavorites(prev => prev.filter((car) => car.id !== carId));
    } catch(err){
      setError("Failed to remove favorite car. Please try again.");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    logout();
    navigate('/login');
  };

  return (
    <div className="favorites-container">
      <h1 className="CarMakeInfo-Title">Saved Predictions</h1>
      <p className="favorites-subtitle">Your saved car price estimates</p>

      {error && <div className="favorites-error">{error}</div>}

      <div className="favorites-actions">
        {isAuthenticated ? (
          <button onClick={handleLogout} className="btn-logout">Log Out</button>
        ) : (
          <button onClick={() => navigate("/login")} className="btn-login">Log In</button>
        )}
      </div>

      {isLoading ? (
        <div className="favorites-loading">Loading your favorites…</div>
      ) : favorites.length === 0 && !error ? (
        <div className="favorites-empty">
          <div className="empty-icon">📋</div>
          <p>No saved predictions yet</p>
          <p className="empty-hint">Make a prediction and save it to see it here</p>
        </div>
      ) : (
        <table className="favorites-table">
          <thead>
            <tr>
              <th>Brand</th>
              <th>Model</th>
              <th>Year</th>
              <th>Mileage</th>
              <th>Fuel</th>
              <th>Transmission</th>
              <th>Clean Title</th>
              <th>Price</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {favorites.map((favorite) => (
              <tr key={favorite.id}>
                <td>{favorite.brand || '-'}</td>
                <td>{favorite.model || '-'}</td>
                <td>{favorite.modelYear || '-'}</td>
                <td>{favorite.mileage ? `${favorite.mileage.toLocaleString()} mi` : '-'}</td>
                <td>{favorite.fuelType || '-'}</td>
                <td>{favorite.transmission || '-'}</td>
                <td>{formatBoolean(favorite.cleanTitle)}</td>
                <td className="price-cell">${favorite.predictedPrice?.toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 0}) || '0'}</td>
                <td>
                  <button
                    className="delete-btn"
                    onClick={() => handleDeleteFavorite(favorite.id)}
                    title="Remove"
                  >
                    🗑️
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default Favorites;