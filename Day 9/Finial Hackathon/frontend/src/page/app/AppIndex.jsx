import React from "react";
import { Routes, Route } from "react-router-dom";
import routes from "./appIndex.routes";
import Layout from "../../layout/homeLayout/Layout";

const AppIndex = () => {
  return (
    <Routes>
      <Route element={<Layout />}>
        {routes.map((route) => (
          <Route key={route.path} path={route.path} element={route.element} />
        ))}
      </Route>
    </Routes>
  );
};

export default AppIndex;
