import React from "react";
import { Navigate } from "react-router-dom";
import Profile from "./profile/Profile";
import ViewProfile from "./profile/ViewProfile";


const routes = [
  { path: "profile", element: <Profile /> },
  { path: "view-profile", element: <ViewProfile /> },
  { path: "*", element: <Navigate to="profile" replace /> },
];

export default routes;
