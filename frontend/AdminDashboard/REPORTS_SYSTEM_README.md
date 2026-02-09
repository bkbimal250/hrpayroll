# Reports System - Frontend Documentation

## Overview

The Reports system provides comprehensive reporting capabilities for attendance, leave, and office data. It integrates with the Django backend API endpoints and provides a user-friendly interface for generating and viewing reports.

## Features

### ✅ **Report Types**
- **Attendance Reports**: Monthly attendance data with present/absent/late statistics
- **Leave Reports**: Leave application data with approval statistics
- **Office Reports**: Office-level statistics and employee distribution

### ✅ **Functionality**
- **Monthly Filtering**: Select year and month for reports
- **Data Visualization**: Charts and graphs for better data understanding
- **Export Capability**: CSV export for all report types
- **Sorting & Pagination**: Interactive tables with sorting and pagination
- **Real-time Data**: Live data from backend API

## Backend Integration

### API Endpoints Used
- `/api/reports/attendance/` - Attendance reports
- `/api/reports/leave/` - Leave reports  
- `/api/reports/office/` - Office reports

### Data Structure
The system expects data in the following format from the backend:

```json
{
  "type": "attendance",
  "summary": {
    "totalRecords": 150,
    "presentCount": 120,
    "absentCount": 20,
    "lateCount": 10,
    "attendanceRate": 80.0
  },
  "dailyStats": [...],
  "rawData": [...]
}
```

## Components

### 1. ReportsDashboard
Main container component that manages:
- Report type selection (tabs)
- Date filtering (year/month)
- Report generation
- Data display coordination

### 2. ReportCard
Displays key metrics in card format:
- Total Records
- Present/Absent counts
- Attendance/Approval rates
- Employee/Device counts

### 3. ReportChart
Visualizes data with:
- **Attendance**: Daily breakdown charts
- **Leave**: Leave type distribution
- **Office**: Employee distribution charts

### 4. ReportTable
Interactive data tables with:
- Sortable columns
- Pagination (10 items per page)
- Status badges
- Formatted dates and times

### 5. ReportExport
CSV export functionality:
- Automatic column mapping
- Proper data formatting
- File naming with date stamps

### 6. ReportFilters
Advanced filtering options:
- Year/Month selection
- Office filtering
- Employee filtering
- Reset functionality

## Usage

### Basic Report Generation
1. Select the desired report type (Attendance/Leave/Office)
2. Choose year and month
3. Click "Generate Report"
4. View summary cards and detailed data

### Advanced Filtering
1. Use the filters section to narrow down data
2. Select specific office or employee
3. Apply filters and regenerate report

### Data Export
1. Generate the desired report
2. Click the export button
3. Download CSV file with formatted data

## Access Control

- **Admin Users**: Full access to all reports
- **Manager Users**: Access to reports (can be restricted by office)
- **Employee Users**: No access to reports

## Technical Details

### State Management
- Local state for report data
- Separate state for each report type
- Loading and error states

### API Integration
- Uses `reportsAPI` service functions
- Proper error handling
- Loading states during API calls

### Responsive Design
- Mobile-friendly layout
- Responsive grid systems
- Touch-friendly interactions

## Customization

### Adding New Report Types
1. Add new tab in `ReportsDashboard`
2. Create corresponding API endpoint
3. Update data processing logic
4. Add chart and table configurations

### Modifying Charts
- Update `ReportChart` component
- Add new chart rendering functions
- Customize colors and layouts

### Table Customization
- Modify `ReportTable` component
- Add new column definitions
- Customize cell rendering

## Error Handling

- API error display
- Loading states
- Empty data states
- User-friendly error messages

## Performance

- Pagination for large datasets
- Efficient data processing
- Optimized re-renders
- Lazy loading where appropriate

## Browser Support

- Modern browsers (Chrome, Firefox, Safari, Edge)
- ES6+ JavaScript features
- CSS Grid and Flexbox
- Responsive design patterns
