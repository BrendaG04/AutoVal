import {BrowserRouter as Router, Routes, Route, Link} from 'react-router-dom';
import Home from './components/HomePage/Home';
import Header from './components/Header/Header';
import Prediction from './components/PredictionPage/Prediction';
import Login from './components/Favorites/Login';
import Signup from './components/Favorites/Signup';
import Verify from './components/Favorites/Verify';
import Favorites from './components/Favorites/Favorites';
import ErrorBoundary from './components/ErrorBoundary';

function App() {

  return (
    <ErrorBoundary>
      <Router>
        <Header/>
        
        <main> 
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path='/predict' element={<Prediction/>}></Route>
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route path="/verify" element={<Verify />} />
            <Route path="/favorites" element={<Favorites />} />
          </Routes>
        </main>
      </Router>
    </ErrorBoundary>
  )
}

export default App
