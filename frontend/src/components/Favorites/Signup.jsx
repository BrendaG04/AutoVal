import React, {useState} from "react";
import {signup} from "../../services/sbServices";
import { useNavigate } from "react-router-dom";
import './registration.css'

function Signup() {

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

    const signupData = {email, password };

    try {
      await signup(signupData);
      setLoading(false);
      //direct to verification code page
      navigate("/verify", {state: {email} });

    } catch (err) {
      setError(err?.response?.data?.message || "Signup Failed, Try again!");
      setLoading(false);
    }
  };

  return (
    <>
    <div className= "registrationContainer">
      <form onSubmit={handleSubmit} className="form">
        <p className="form-title">Create an Account</p>
        {error && <div className="auth-error">{error}</div>}

          <div className="input-container">
            <input type="email" placeholder="Enter email" value={email} onChange={(e) => setEmail(e.target.value)} required  />
            <span/>
          </div>

          <div className="input-container">
            <input type="password" placeholder="Enter password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </div>

          <button type="submit" disabled={loading} className="submit" > {loading ? "Signing up..." : "Sign Up"} </button>
          
          <p className="signup-link"> Already have an account? <a href="/login">Login</a></p>
      </form>
    </div>
    </>
  );
}
export default Signup;