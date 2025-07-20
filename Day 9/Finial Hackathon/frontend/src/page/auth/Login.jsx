import React, { useState } from 'react';
import { login } from '../../service/Agent.service';
import './style.scss';
import { useNavigate } from 'react-router-dom';

export default function Login() {
  const nav = useNavigate();
  const [form, setForm] = useState({ email: '', password: '' });

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const res = await login(form);
      console.log('res :', res);
      localStorage.setItem('token', res.access_token);
      if(res?.success){
        nav('/app/profile');
      }
    } catch (err) {
      console.log(err);
    }
  };

  return (
    <section className='form-section'>

    <form className="modern-form" onSubmit={handleLogin}>
      <div className="form-title">Login</div>

      <div className="form-body">
        {/* Email */}
        <div className="input-group">
          <div className="input-wrapper">
            <svg fill="none" viewBox="0 0 24 24" className="input-icon">
              <path
                strokeWidth="1.5"
                stroke="currentColor"
                d="M3 8L10.8906 13.2604C11.5624 13.7083 12.4376 13.7083 13.1094 13.2604L21 8M5 19H19C20.1046 19 21 18.1046 21 17V7C21 5.89543 20.1046 5 19 5H5C3.89543 5 3 5.89543 3 7V17C3 18.1046 3.89543 19 5 19Z"
                ></path>
            </svg>
            <input
              required
              placeholder="Email"
              className="form-input"
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              />
          </div>
        </div>

        {/* Password */}
        <div className="input-group">
          <div className="input-wrapper">
            <svg fill="none" viewBox="0 0 24 24" className="input-icon">
              <path
                strokeWidth="1.5"
                stroke="currentColor"
                d="M12 10V14M8 6H16C17.1046 6 18 6.89543 18 8V16C18 17.1046 17.1046 18 16 18H8C6.89543 18 6 17.1046 6 16V8C6 6.89543 6.89543 6 8 6Z"
                ></path>
            </svg>
            <input
              required
              placeholder="Password"
              className="form-input"
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              />
            <button className="password-toggle" type="button">
              <svg fill="none" viewBox="0 0 24 24" className="eye-icon">
                <path
                  strokeWidth="1.5"
                  stroke="currentColor"
                  d="M2 12C2 12 5 5 12 5C19 5 22 12 22 12C22 12 19 19 12 19C5 19 2 12 2 12Z"
                ></path>
                <circle strokeWidth="1.5" stroke="currentColor" r="3" cy="12" cx="12"></circle>
              </svg>
            </button>
          </div>
        </div>
      </div>

      <button className="submit-button" type="submit">
        <span className="button-text">Login</span>
        <div className="button-glow"></div>
      </button>

      <div className="form-footer">
        <div className="login-link" onClick={() => nav('/signup')}>
          Don't have an account? <span>Sign Up</span>
        </div>
      </div>
    </form>
                  </section>
  );
}
