import React from 'react';
import { Box, Typography } from '@mui/material';
import { MOCK_DASHBOARD_STATS, MOCK_RECENT_ACTIVITY, MOCK_BAR_CHART_DATA, MOCK_DOUGHNUT_DATA } from '../../constants';
import { StatsGrid, ChartsSection, RecentActivityTable } from './';

// Chart.js Imports
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
} from 'chart.js';

// Register ChartJS Components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
);

/**
 * Main Dashboard Component
 * Displays overview of DPR Quality Assessment System
 */
const Dashboard: React.FC = () => {
  const stats = MOCK_DASHBOARD_STATS;
  const barChartData = MOCK_BAR_CHART_DATA;
  const doughnutData = MOCK_DOUGHNUT_DATA;
  const recentActivity = MOCK_RECENT_ACTIVITY;

  return (
    <Box sx={{ pb: 4 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" sx={{ fontWeight: 700, color: '#0f2c59', mb: 1 }}>
          Dashboard Overview
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Real-time insights and analytics for DPR Quality Assessment
        </Typography>
      </Box>

      {/* Statistics Cards */}
      <StatsGrid stats={stats} />

      {/* Charts Section */}
      <ChartsSection barChartData={barChartData} doughnutData={doughnutData} />

      {/* Recent Activity Table */}
      <RecentActivityTable activities={recentActivity} />
    </Box>
  );
};

export default Dashboard;
