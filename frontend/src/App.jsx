import { useState } from 'react'
import axios from 'axios'
import { useDropzone } from 'react-dropzone'
import './App.css'

function App() {
  const [fileCurrent, setFileCurrent] = useState(null)
  const [filePrev, setFilePrev] = useState(null)
  const [month, setMonth] = useState("DEC 2025")
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState("")
  
  // This state holds the filenames sent back from the server
  const [results, setResults] = useState(null)

  const FileDropzone = ({ file, setFile, label, color }) => {
    const onDrop = (acceptedFiles) => {
      setFile(acceptedFiles[0])
      setResults(null) 
      setMessage("")
    }
    const { getRootProps, getInputProps } = useDropzone({ 
      onDrop, 
      multiple: false,
      accept: { 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'] }
    })

    return (
      <div {...getRootProps()} style={{
        border: `2px dashed ${color}`, 
        padding: '30px', 
        borderRadius: '10px',
        backgroundColor: file ? '#e8f5e9' : '#f8f9fa',
        cursor: 'pointer',
        marginBottom: '15px'
      }}>
        <input {...getInputProps()} />
        {file ? (
          <p style={{ color: "green", fontWeight: "bold", margin: 0 }}>✅ {file.name}</p>
        ) : (
          <p style={{ color: "#666", margin: 0 }}>{label}</p>
        )}
      </div>
    )
  }

  const handleUpload = async () => {
    if (!fileCurrent || !filePrev) {
      alert("Please upload BOTH files!")
      return
    }

    setLoading(true)
    setMessage("⏳ Processing... Please wait.")
    setResults(null)

    const formData = new FormData()
    formData.append('file_current', fileCurrent)
    formData.append('file_prev', filePrev)
    formData.append('month', month)

    try {
      // We removed 'responseType: blob' because we now expect JSON text
      const response = await axios.post('http://localhost:5000/process', formData)
      
      console.log("Server Response:", response.data) // Debugging
      setResults(response.data)
      setMessage("✅ Processing Done! Download your files below.")
    } catch (error) {
      console.error(error)
      setMessage("❌ Error processing files. Check console.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: "700px", margin: "40px auto", textAlign: "center", fontFamily: "Arial, sans-serif" }}>
      <h1 style={{ color: "#333" }}>GST Reconciliation Tool</h1>
      
      <div style={{ marginBottom: "20px", textAlign: "left" }}>
        <label style={{ fontWeight: "bold", display: "block", marginBottom: "5px" }}>Current Month Name:</label>
        <input 
          type="text" 
          value={month} 
          onChange={(e) => setMonth(e.target.value)} 
          style={{ width: "100%", padding: "10px", fontSize: "16px" }}
        />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        <FileDropzone 
          file={fileCurrent} 
          setFile={setFileCurrent} 
          label="📂 Upload CURRENT Month" 
          color="#007bff"
        />
        <FileDropzone 
          file={filePrev} 
          setFile={setFilePrev} 
          label="📂 Upload PREVIOUS Month" 
          color="#ff9800"
        />
      </div>

      <button 
        onClick={handleUpload} 
        disabled={loading}
        style={{
          width: "100%",
          padding: "15px", 
          fontSize: "18px", 
          backgroundColor: loading ? "#6c757d" : "#28a745", 
          color: "white", 
          border: "none", 
          borderRadius: "5px",
          cursor: loading ? "not-allowed" : "pointer",
          fontWeight: "bold",
          marginTop: "10px"
        }}
      >
        {loading ? "Processing..." : "RUN PROCESS"}
      </button>

      {message && <p style={{ marginTop: "20px", fontSize: "18px", fontWeight: "bold" }}>{message}</p>}

      {/* THIS IS THE DOWNLOAD SECTION */}
      {results && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginTop: '20px' }}>
          
          <a href={`http://localhost:5000/download/${results.current_file}`} download>
            <button style={{
              width: "100%", padding: "15px", fontSize: "16px",
              backgroundColor: "#007bff", color: "white", border: "none", borderRadius: "5px", cursor: "pointer"
            }}>
              📥 Download {month}
            </button>
          </a>

          <a href={`http://localhost:5000/download/${results.prev_file}`} download>
            <button style={{
              width: "100%", padding: "15px", fontSize: "16px",
              backgroundColor: "#ff9800", color: "white", border: "none", borderRadius: "5px", cursor: "pointer"
            }}>
              📥 Download Prev Month
            </button>
          </a>

        </div>
      )}
    </div>
  )
}

export default App