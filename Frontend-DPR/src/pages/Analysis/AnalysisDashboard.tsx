import React, { useState, useCallback, useEffect } from 'react';
import {
  Box, Container, Typography, Grid, Card, CardContent, Button, Alert, CircularProgress, Chip, LinearProgress
} from '@mui/material';
import { CloudUpload as UploadIcon, Analytics as AnalyticsIcon } from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';
import { useLocation, useNavigate } from 'react-router-dom';

const API_BASE_URL = 'http://localhost:8000';

export const AnalysisDashboard: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();

  const [file, setFile] = useState<File | null>(null);
  const [activeStep, setActiveStep] = useState<'upload' | 'processing' | 'results'>('upload');
  const [jobId, setJobId] = useState<string | null>(null);
  const [report, setReport] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  // Load a report passed from the Reports history page
  useEffect(() => {
    if (location.state && location.state.historicReport) {
      setReport(location.state.historicReport);
      setActiveStep('results');
      // Clear state so it doesn't get stuck if they press "Upload Another"
      navigate(location.pathname, { replace: true });
    }
  }, [location, navigate]);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setFile(acceptedFiles[0]);
      setError(null);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1
  });

  const handleUploadAndAnalyze = async () => {
    if (!file) return;
    setActiveStep('processing');
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const uploadRes = await fetch(`${API_BASE_URL}/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!uploadRes.ok) throw new Error('Failed to upload file');
      const uploadData = await uploadRes.json();
      setJobId(uploadData.job_id);

    } catch (err: any) {
      setError(err.message);
      setActiveStep('upload');
    }
  };

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (activeStep === 'processing' && jobId) {
      interval = setInterval(async () => {
        try {
          const res = await fetch(`${API_BASE_URL}/status/${jobId}`);
          if (!res.ok) throw new Error('Status polling failed');
          const data = await res.json();
          
          if (data.status === 'COMPLETED') {
            setReport(data.report);
            
            // Save to localStorage for Reports page
            try {
              const existingReports = JSON.parse(localStorage.getItem('dpr_reports') || '[]');
              const newReport = {
                ...data.report,
                fileName: file?.name || 'Uploaded Document',
                date: new Date().toISOString()
              };
              localStorage.setItem('dpr_reports', JSON.stringify([newReport, ...existingReports]));
            } catch (e) { console.error('Failed to save to local storage', e); }

            setActiveStep('results');
            clearInterval(interval);
          } else if (data.status === 'FAILED') {
            setError(data.report?.error_message || 'Analysis failed');
            setActiveStep('upload');
            clearInterval(interval);
          }
        } catch (err) {
          console.error(err);
        }
      }, 3000);
    }
    return () => clearInterval(interval);
  }, [activeStep, jobId]);

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <AnalyticsIcon sx={{ fontSize: 40, color: '#0f2c59' }} />
          <Typography variant="h4" sx={{ fontWeight: 700, color: '#0f2c59' }}>
            DPR Analysis Dashboard
          </Typography>
        </Box>
        <Typography variant="body1" color="text.secondary" sx={{ mt: 1 }}>
          Upload and evaluate Detailed Project Reports through automated assessment
        </Typography>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      {activeStep === 'upload' && (
        <Card sx={{ borderRadius: 3, maxWidth: 800, mx: 'auto' }}>
          <CardContent sx={{ p: 4, textAlign: 'center' }}>
            <Box
              {...getRootProps()}
              sx={{
                p: 6, border: '2px dashed #1976d2', borderRadius: 3,
                bgcolor: isDragActive ? '#e3f2fd' : '#f8f9fa', cursor: 'pointer', mb: 3
              }}
            >
              <input {...getInputProps()} />
              <UploadIcon sx={{ fontSize: 48, color: '#1976d2', mb: 2 }} />
              <Typography variant="h6">{isDragActive ? 'Drop file' : 'Drag & drop DPR PDF here'}</Typography>
            </Box>
            {file && <Typography sx={{ mb: 2, fontWeight: 'bold' }}>Selected: {file.name}</Typography>}
            <Button
              variant="contained" size="large" onClick={handleUploadAndAnalyze} disabled={!file}
              sx={{ bgcolor: '#0f2c59' }}
            >
              Analyze DPR
            </Button>
            <Button
              variant="outlined" size="large" 
              onClick={async () => {
                try {
                  const res = await fetch('/real_DPR.pdf');
                  const blob = await res.blob();
                  setFile(new File([blob], 'real_DPR.pdf', { type: 'application/pdf' }));
                } catch (err) {
                  console.error(err);
                }
              }}
              sx={{ ml: 2 }}
            >
              Load Test DPR
            </Button>
          </CardContent>
        </Card>
      )}

      {activeStep === 'processing' && (
        <Box sx={{ textAlign: 'center', py: 8 }}>
          <CircularProgress size={80} sx={{ mb: 4 }} />
          <Typography variant="h5">Analyzing Document via RAG & AI...</Typography>
          <Typography color="text.secondary">Extracting images, chunking text, and querying compliance</Typography>
        </Box>
      )}

      {activeStep === 'results' && report && (
        <Grid container spacing={3}>
          <Grid item xs={12} sx={{ display: 'flex', justifyContent: 'space-between', '@media print': { display: 'none' } }}>
            <Button onClick={() => { setActiveStep('upload'); setFile(null); setReport(null); }} sx={{ mb: 2 }}>
              Upload Another
            </Button>
            <Button 
              variant="contained" 
              color="primary" 
              onClick={() => window.print()}
              sx={{ mb: 2, bgcolor: '#0f2c59' }}
            >
              Export Report PDF
            </Button>
          </Grid>
          <Grid item xs={12}>
            <Card sx={{ borderRadius: 3, mb: 3, bgcolor: '#f4f6f8' }}>
              <CardContent>
                <Typography variant="h5" sx={{ mb: 2, fontWeight: 'bold', color: '#0f2c59' }}>
                  Executive Summary
                </Typography>
                <Typography variant="body1" sx={{ whiteSpace: 'pre-line' }}>
                  {report.executive_summary}
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          {report.evaluation_summary && (
            <Grid item xs={12}>
              <Typography variant="h5" sx={{ mb: 2, fontWeight: 'bold' }}>AI Assessment Report Card</Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} md={4}>
                  <Card sx={{ height: '100%', borderRadius: 3, borderTop: '6px solid #d32f2f', bgcolor: '#fff5f5' }}>
                    <CardContent>
                      <Typography variant="h6" sx={{ color: '#d32f2f', mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                        🚨 Flagged Risks
                      </Typography>
                      <ul style={{ paddingLeft: '20px', margin: 0 }}>
                        {report.evaluation_summary.flagged_risks.map((risk: string, i: number) => (
                          <li key={i} style={{ marginBottom: '8px' }}><Typography variant="body2">{risk}</Typography></li>
                        ))}
                      </ul>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} md={4}>
                  <Card sx={{ height: '100%', borderRadius: 3, borderTop: '6px solid #ed6c02', bgcolor: '#fff8f0' }}>
                    <CardContent>
                      <Typography variant="h6" sx={{ color: '#ed6c02', mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                        ⚠️ Missing Context
                      </Typography>
                      <ul style={{ paddingLeft: '20px', margin: 0 }}>
                        {report.evaluation_summary.missing_sections.map((item: string, i: number) => (
                          <li key={i} style={{ marginBottom: '8px' }}><Typography variant="body2">{item}</Typography></li>
                        ))}
                      </ul>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} md={4}>
                  <Card sx={{ height: '100%', borderRadius: 3, borderTop: '6px solid #2e7d32', bgcolor: '#f0fdf4' }}>
                    <CardContent>
                      <Typography variant="h6" sx={{ color: '#2e7d32', mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                        💡 Recommendations
                      </Typography>
                      <ul style={{ paddingLeft: '20px', margin: 0 }}>
                        {report.evaluation_summary.recommendations.map((rec: string, i: number) => (
                          <li key={i} style={{ marginBottom: '8px' }}><Typography variant="body2">{rec}</Typography></li>
                        ))}
                      </ul>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            </Grid>
          )}
          
          <Grid item xs={12}>
            <Typography variant="h5" sx={{ mb: 2, fontWeight: 'bold' }}>Dynamic AI Insights</Typography>
            <Grid container spacing={2}>
              {report.insights?.map((insight: any, i: number) => (
                <Grid item xs={12} md={6} key={i}>
                  <Card sx={{ height: '100%', borderRadius: 2, borderLeft: '4px solid #1976d2' }}>
                    <CardContent>
                      <Typography variant="h6" color="primary" gutterBottom>
                        {insight.topic}
                      </Typography>
                      <Typography variant="body2" sx={{ mb: 2 }}>
                        {insight.details}
                      </Typography>
                      {insight.extracted_values && Object.keys(insight.extracted_values).length > 0 && (
                        <Box sx={{ mb: 2, p: 2, bgcolor: '#f4f6f8', borderRadius: 2 }}>
                          <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1, color: '#0f2c59' }}>Key Data & Costs</Typography>
                          <Grid container spacing={2}>
                            {Object.entries(insight.extracted_values).map(([key, value], idx) => (
                              <Grid item xs={6} key={idx}>
                                <Typography variant="caption" color="text.secondary" display="block">{key}</Typography>
                                <Typography variant="body1" fontWeight="bold">{String(value)}</Typography>
                              </Grid>
                            ))}
                          </Grid>
                        </Box>
                      )}
                      {insight.risks?.length > 0 && (
                        <Box>
                          <Typography variant="subtitle2" color="error">Identified Risks:</Typography>
                          <ul>
                            {insight.risks.map((risk: string, j: number) => (
                              <li key={j}><Typography variant="body2" color="error">{risk}</Typography></li>
                            ))}
                          </ul>
                        </Box>
                      )}
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Grid>

          {report.extracted_images?.length > 0 && (
            <Grid item xs={12}>
              <Typography variant="h5" sx={{ mt: 4, mb: 2, fontWeight: 'bold' }}>Extracted Visuals</Typography>
              <Grid container spacing={2}>
                {report.extracted_images.map((img: any, i: number) => (
                  <Grid item xs={12} sm={6} md={4} key={i}>
                    <Card sx={{ height: '100%', borderRadius: 2 }}>
                      <CardContent>
                        <Chip label={`Page Data`} size="small" sx={{ mb: 1 }} />
                        <Typography variant="body2" color="text.secondary">{img.caption}</Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            </Grid>
          )}

        </Grid>
      )}
    </Container>
  );
};

export default AnalysisDashboard;
