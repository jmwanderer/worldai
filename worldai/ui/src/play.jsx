//
// Creates play client
//
//    Jim Wanderer
//    http://github.com/jmwanderer
//

import React from 'react'
import ReactDOM from 'react-dom/client'
import { PlayClient } from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <PlayClient />
  </React.StrictMode>,
)
