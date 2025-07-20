import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';

import Landing from './page/landing/Landing';
import AgentDataUpload from './page/agentDataUpload/AgentDataUpload';
import Dashboard from './page/dashboard/Dashboard';
import UserType from './page/userType/UserType';
import SignUp from './page/auth/SignUp';
import Login from './page/auth/Login';
import AppIndex from './page/app/AppIndex';

const App = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/upload-data" element={<AgentDataUpload />} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<SignUp />} />
        <Route path="/dashboard/:analysisId" element={<Dashboard />} />
        <Route path="/user" element={<UserType />} />
        <Route path="/app/*" element={<AppIndex />} />
        <Route path="*" element={<Landing />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
