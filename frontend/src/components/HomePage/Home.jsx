
import './Home.css'
import { Link } from 'react-router-dom';

function Home(){

return (
    <div className="home-container">

        <main className="main-content">
            <div className="hero-section">
                    <div className="hero-content">
                        <div className="hero-text">
                            <h1 className="main-heading">
                                Get the value of your car!
                            </h1>
                            <p className="hero-subtitle">
                                AI-powered price predictions trained on 338,000+ real vehicle listings.
                            </p>
                            <Link to='/predict'>
                                <button className="makePredictionButton">Make A Prediction</button>
                            </Link>
                        </div>
                        <div className="car-image-container">
                            <img src="/SilveradoHomePage.png" alt="SilveradoTruct" className="car-image"/>
                        </div>
                    </div>
            </div>
        </main>

        <section className="how-it-works">
            <h2 className="section-heading">How It Works</h2>
            <div className="steps-grid">
                <div className="step-card">
                    <span className="step-number">1</span>
                    <h3>Select Your Car</h3>
                    <p>Choose the make, model, year, and other details from our dropdown menus.</p>
                </div>
                <div className="step-card">
                    <span className="step-number">2</span>
                    <h3>Get a Prediction</h3>
                    <p>Our XGBoost ML model analyzes your inputs and returns a price estimate.</p>
                </div>
                <div className="step-card">
                    <span className="step-number">3</span>
                    <h3>Save & Compare</h3>
                    <p>Create an account to save predictions and compare different vehicles.</p>
                </div>
            </div>
        </section>

        <section className="stats-section">
            <div className="stats-grid">
                <div className="stat-card">
                    <span className="stat-number">338K+</span>
                    <span className="stat-label">Listings Trained On</span>
                </div>
                <div className="stat-card">
                    <span className="stat-number">92%</span>
                    <span className="stat-label">Model Accuracy (R²)</span>
                </div>
                <div className="stat-card">
                    <span className="stat-number">550+</span>
                    <span className="stat-label">Car Models Supported</span>
                </div>
            </div>
        </section>
    
    </div>
    );
}

export default Home;
