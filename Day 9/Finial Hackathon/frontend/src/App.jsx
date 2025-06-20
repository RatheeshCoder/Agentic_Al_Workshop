import React from 'react'
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Home from './page/home/Home';
import AgentDataUpload from './page/agentDataUpload/AgentDataUpload';
import Dashboard from './page/dashboard/Dashboard';
const App = () => {
  return (
    <BrowserRouter>
      <Routes>
          <Route index element={<Home />} />
          <Route path="upload-data" element={<AgentDataUpload />} />
          <Route path="dashboard/:analysisId" element={<Dashboard />} />
          <Route path="*" element={<Home />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
