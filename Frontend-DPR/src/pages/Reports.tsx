import React, { useState, useEffect } from 'react';
import { Box, Typography, Card, CardContent, Button, Stack, Grid, Chip } from '@mui/material';
import DescriptionIcon from '@mui/icons-material/Description';
import AssessmentIcon from '@mui/icons-material/Assessment';

import { useNavigate } from 'react-router-dom';

const Reports: React.FC = () => {
    const navigate = useNavigate();
    const [reports, setReports] = useState<any[]>([]);

    useEffect(() => {
        try {
            const saved = JSON.parse(localStorage.getItem('dpr_reports') || '[]');
            setReports(saved);
        } catch (e) { console.error(e); }
    }, []);

    return (
        <Box>
            <Box sx={{ mb: 3 }}>
                <Typography variant="h4" sx={{ fontWeight: 700, color: '#0f2c59', mb: 1 }}>
                    DPR Analysis Reports
                </Typography>
                <Typography variant="body1" color="text.secondary">
                    Access your previously analysed Detailed Project Reports
                </Typography>
            </Box>

            {reports.length === 0 ? (
                <Card sx={{ boxShadow: '0 2px 10px rgba(0,0,0,0.05)', borderRadius: 2, minHeight: 400, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <CardContent sx={{ textAlign: 'center' }}>
                        <Stack spacing={2} alignItems="center">
                            <DescriptionIcon sx={{ fontSize: 60, color: '#9e9e9e' }} />
                            <Typography variant="h6" sx={{ fontWeight: 600, color: '#333' }}>
                                No Reports Available
                            </Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                                Upload and analyze DPR documents to generate reports
                            </Typography>
                            <Button
                                variant="contained"
                                color="primary"
                                onClick={() => navigate('/analysis')}
                                sx={{
                                    px: 4,
                                    py: 1,
                                    bgcolor: '#1976d2',
                                    textTransform: 'none',
                                    fontWeight: 500,
                                    '&:hover': {
                                        bgcolor: '#1565c0'
                                    }
                                }}
                            >
                                Go to Analysis
                            </Button>
                        </Stack>
                    </CardContent>
                </Card>
            ) : (
                <Grid container spacing={3}>
                    {reports.map((report, idx) => (
                        <Grid item xs={12} md={6} lg={4} key={idx}>
                            <Card sx={{ borderRadius: 3, boxShadow: '0 4px 12px rgba(0,0,0,0.05)', height: '100%', display: 'flex', flexDirection: 'column' }}>
                                <CardContent sx={{ flexGrow: 1 }}>
                                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                                        <AssessmentIcon color="primary" sx={{ fontSize: 40 }} />
                                        <Chip label={new Date(report.date).toLocaleDateString()} size="small" variant="outlined" />
                                    </Box>
                                    <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 1 }} noWrap>
                                        {report.fileName || 'Document Analysis'}
                                    </Typography>
                                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2, display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                                        {report.executive_summary}
                                    </Typography>

                                    {report.evaluation_summary && (
                                        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }}>
                                            <Chip label={`${report.evaluation_summary.flagged_risks?.length || 0} Risks`} color="error" size="small" />
                                            <Chip label={`${report.evaluation_summary.recommendations?.length || 0} Recs`} color="success" size="small" />
                                        </Box>
                                    )}
                                </CardContent>
                                <Box sx={{ p: 2, mt: 'auto', borderTop: '1px solid #eee' }}>
                                    <Button 
                                        fullWidth 
                                        variant="outlined" 
                                        onClick={() => navigate('/analysis', { state: { historicReport: report } })}
                                    >
                                        View Full Report PDF
                                    </Button>
                                </Box>
                            </Card>
                        </Grid>
                    ))}
                </Grid>
            )}
        </Box>
    );
};

export default Reports;
