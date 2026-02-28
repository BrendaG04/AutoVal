import axios from 'axios';

const SPRING_API_URL = import.meta.env.VITE_SPRING_API_URL || 'http://localhost:8080';
const REST_API_URL_AUTH = `${SPRING_API_URL}/auth`;

const getAuthHeaders = () => ({
  headers: {
    Authorization: `Bearer ${localStorage.getItem('token')}`
  },
});

export const signup = (signupData) => {
  return axios.post(`${REST_API_URL_AUTH}/signup`, signupData);
};
export const login = (loginData) => {
  return axios.post(`${REST_API_URL_AUTH}/login`, loginData);
};
export const verify = (loginData) => {
  return axios.post(`${REST_API_URL_AUTH}/verify`, loginData);
};
export const resend = (email) => {
  return axios.post(`${REST_API_URL_AUTH}/resend?email=${encodeURIComponent(email)}`);
};

const api = axios.create({
  baseURL: SPRING_API_URL,
});

api.interceptors.request.use(config => {
  const rawToken = localStorage.getItem('token');
  if (rawToken) {
    const cleanToken = rawToken.trim().replace(/^"|"$/g, '');
    config.headers.Authorization = `Bearer ${cleanToken}`;
  }
  return config;
});

export const getFavorites = () => api.get('/favorites', getAuthHeaders());
export const getSavedPredictions = getFavorites;

export const addPrediction = (carData) => {
  const payload = {
    brand: carData.brand ?? '',
    model: carData.model ?? '',
    mileage: Number(carData.mileage ?? carData.milage ?? 0),
    engine: Number(carData.engine ?? 0),
    modelYear: Number(carData.modelYear ?? carData.model_year ?? 0),
    fuelType: carData.fuelType ?? carData.fuel_type ?? '',
    transmission: carData.transmission ?? '',
    cleanTitle: Boolean(carData.cleanTitle ?? carData.clean_title),
    hasAccident: Boolean(carData.hasAccident ?? carData.has_accident),
    predictedPrice: Number(carData.predictedPrice ?? carData.prediction ?? 0),
  };

  return api.post('/favorites/add', payload, getAuthHeaders());
};

export const deletePrediction = (id) => api.delete(`/favorites/delete/${id}`, getAuthHeaders());



