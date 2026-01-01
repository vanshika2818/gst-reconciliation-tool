import { useState } from 'react'
import axios from 'axios'
import { useDropzone } from 'react-dropzone'
import './App.css'

function App() {
  const [fileCurrent, setFileCurrent] = useState(null)
  const [filePrev, setFilePrev] = useState(null)
  const [month, setMonth] = useState("DEC 2025")
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState({ type: '', msg: '' })
  const [results, setResults] = useState(null)

  // ---------------------------------------------------------
  // 1. DYNAMIC API URL CONFIGURATION
  // This automatically switches between Localhost and Render
  // ---------------------------------------------------------
// FORCE LOCALHOST for testing
const API_URL = 'http://127.0.0.1:5000';

//const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000';


  const FileDropzone = ({ file, setFile, label, icon }) => {
    const onDrop = (acceptedFiles) => {
      setFile(acceptedFiles[0])
      setResults(null)
      setStatus({ type: '', msg: '' })
    }
    const { getRootProps, getInputProps, isDragActive } = useDropzone({ 
      onDrop, 
      multiple: false,
      accept: { 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'] }
    })

    return (
      <div {...getRootProps()} className={`dropzone ${file ? 'active' : ''} ${isDragActive ? 'drag-active' : ''}`}>
        <input {...getInputProps()} />
        <div className="icon">{file ? '✅' : icon}</div>
        {file ? (
          <p className="file-name">{file.name}</p>
        ) : (
          <p className="dropzone-text">
            {isDragActive ? "Drop it here!" : label}
          </p>
        )}
      </div>
    )
  }

  const handleUpload = async () => {
    if (!fileCurrent || !filePrev) {
      alert("⚠️ Please upload both the Current and Previous month files.")
      return
    }

    setLoading(true)
    setStatus({ type: 'loading', msg: "⏳ Crunching the numbers... this might take a moment." })
    setResults(null)

    const formData = new FormData()
    formData.append('file_current', fileCurrent)
    formData.append('file_prev', filePrev)
    formData.append('month', month)

    try {
      // 2. USE DYNAMIC API_URL HERE
      const response = await axios.post(`${API_URL}/process`, formData)
      console.log("Success:", response.data)
      setResults(response.data)
      setStatus({ type: 'success', msg: "🎉 Processing Complete! Files are ready below." })
    } catch (error) {
      console.error(error)
      setStatus({ type: 'error', msg: "❌ Server Error. Please check the backend console." })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app-container">
      <div className="card">
        
        {/* Header */}
        <div className="header">
          <h1>GST Reconciliation Tool</h1>
          <p>Seamlessly merge, calculate, and analyze your tax data.</p>
        </div>

        {/* Month Input */}
        <div className="input-group">
          <label className="input-label">Processing Month</label>
          <input 
            className="text-input"
            type="text" 
            value={month} 
            onChange={(e) => setMonth(e.target.value)} 
            placeholder="e.g. DEC 2025"
          />
        </div>

        {/* File Upload Area */}
        <div className="upload-grid">
          <FileDropzone 
            file={fileCurrent} 
            setFile={setFileCurrent} 
            label="Drag & Drop CURRENT Month File" 
            icon="📂"
          />
          <FileDropzone 
            file={filePrev} 
            setFile={setFilePrev} 
            label="Drag & Drop PREVIOUS Month File" 
            icon="📅"
          />
        </div>

        {/* Action Button */}
        <button 
          className="btn-process"
          onClick={handleUpload} 
          disabled={loading}
        >
          {loading ? "Processing..." : "RUN RECONCILIATION"}
        </button>

        {/* Status Messages */}
        {status.msg && (
          <div className={`status-msg ${status.type}`}>
            {status.msg}
          </div>
        )}

        {/* Results Section */}
        {results && (
          <div className="results-section">
            <h3 className="results-title">Download Reports</h3>
            <div className="download-grid">
              
              {/* 3. USE DYNAMIC API_URL IN DOWNLOAD LINKS */}
              
              <a href={`${API_URL}/download/${results.current_file}`} className="btn-download btn-main" download>
                <span>📥</span> Main Data
              </a>

              <a href={`${API_URL}/download/${results.prev_file}`} className="btn-download btn-returns" download>
                <span>↩️</span> Returns Data
              </a>

              <a href={`${API_URL}/download/${results.summary_file}`} className="btn-download btn-summary" download>
                <span>📊</span> Pivot Summary
              </a>

            </div>
          </div>
        )}

      </div>
    </div>
  )
}

export default App
























