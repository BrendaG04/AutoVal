import React, {useState} from "react";
import {login} from "../../services/sbServices";
import { useNavigate } from "react-router-dom";
import './registration.css'

function Login() {

  //States for email, password and error message
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();

  //form submission handler
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      //calls login function from CarServices file
      const response = await login({ email, password });
      //saves the token in local storage
      const { token } = response.data;
      if (!token || typeof token !== 'string') {
        throw new Error('Invalid token received from server');
      }
      const cleanToken = token.trim();
      if (!cleanToken) {
          throw new Error('Empty token after trimming');
      }

      localStorage.setItem("token", cleanToken);
      navigate("/favorites");

    } catch (err) {

      const backendMsg = err?.response?.data?.message || "";
      if (backendMsg.includes("not found")) {
        setError("User not found. Please sign up first.");
      } else if (backendMsg.includes("not verified")) {
        setError("Your account is not verified. Please check your email.");
      } else {
        setError("Invalid email or password.");
      }
      setLoading(false);
    }

  };

  return (
    <>
    <div className= "registrationContainer">
      
      <form onSubmit={handleSubmit} className="form">
        <p className="form-title">Welcome Back</p>
        {error && <div className="auth-error">{error}</div>}

          <div className="input-container">
            <input type="email" placeholder="Enter email" value={email} onChange={(e) => setEmail(e.target.value)} required  />
            <span/>
          </div>

          <div className="input-container">
            <input type="password" placeholder="Enter password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </div>

          <button type="submit" disabled={loading} className="submit" > {loading ? "Logging in..." : "Log In"} </button>
          
          <p className="signup-link">Don't have an account? <a href="/signup">Signup</a></p>
      </form>

    </div>
    </>
  );
}

export default Login;