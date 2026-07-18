import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { ToastProvider } from './components/ui'
import { UploadJobProvider } from './lib/uploadJob'
import './styles/globals.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ToastProvider>
      <UploadJobProvider>
        <App />
      </UploadJobProvider>
    </ToastProvider>
  </React.StrictMode>,
)
