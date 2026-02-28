import { verify, resend } from "../../services/sbServices";
import React, {useState, useEffect} from 'react';
import { useNavigate, useLocation } from "react-router-dom";
import "./registration.css"


function Verify(){

    const navigate = useNavigate();
    const location = useLocation();
    const emailSent = location.state?.email;
    const [email] = useState(emailSent || '');
    const [code, setCode] = useState("");
    const [msg, setMsg] = useState("")
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);
    const [resendLoading, setResendLoading] = useState(false);

    useEffect(()=>{
        if (!email) 
            navigate("/signup");
    }, [email, navigate]);
    

    const verificationHandler = async e=> {
        e.preventDefault();
        setLoading(true);
        setError("");
        setMsg("");

        try {
            await verify({ email, verificationCode: code });
            setMsg("Account verified successfully, you can now log in.");
            setTimeout(() => navigate("/login"), 1500);
        } catch (err) {
            
            const backendMsg = err.response?.data?.message || err.response?.data || err.message;
            
            if (backendMsg.includes("expired")) {
                setError("Your verification code expired. Please click 'Resend Code'.");
            } else if (backendMsg.includes("invalid")) {
                setError("Invalid verification code. Check and try again.");
            } else if (backendMsg.includes("not found")) {
                setError("Account not found. Please sign up.");
            } else {
                setError(backendMsg || "Verification failed. Please try again.");
            }
        } finally {
            setLoading(false);
        }
    };


    const resendHandler = async () => {
        setResendLoading(true);
        setError("");
        setMsg("");

        try {
            await resend (email);
            setMsg("Verification code resent!");

        } catch (err){
            const backendMsg = err.response?.data?.message || "Resend failed";
            setError(backendMsg.includes("already verified") 
            ? "Account already verified. Please login." 
            : backendMsg
          );
        } finally {
            setResendLoading(false);
        }
    }

    
    return (
    <>
    <div className="registrationContainer">
        <form onSubmit={verificationHandler} className="form">
            <p className="form-title">Verify Your Email</p>

            <p className="verify-hint">We sent a 6-digit code to <b>{email}</b>.
                <br /> Enter it below to activate your account.
            </p>

            {error && <div className="auth-error">{error}</div>}
            {msg   && <div className="auth-success">{msg}</div>}

        <div className="input-container">
            <input type="text" placeholder="123456" value={code} onChange={e => setCode(e.target.value)} required/>
            <span/>
        </div>

        <button type="submit" className="submit" disabled={loading}>
          {loading ? "Verifying…" : "Verify"}
        </button>

        <button type="button" className="submit resend-btn" disabled={resendLoading} onClick={resendHandler}>
          {resendLoading ? "Sending…" : "Resend Code"}
        </button>

        </form>
    </div>
    
    
    </>
    )
}

export default Verify;