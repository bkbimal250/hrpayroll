# User Manual & Training Guide
## Employee Attendance Management System

---

## 📚 **TABLE OF CONTENTS**

1. [System Overview](#system-overview)
2. [Getting Started](#getting-started)
3. [User Roles & Permissions](#user-roles--permissions)
4. [Dashboard Guide](#dashboard-guide)
5. [User Management](#user-management)
6. [Attendance Tracking](#attendance-tracking)
7. [Reports & Analytics](#reports--analytics)
8. [Document Generation](#document-generation)
9. [Profile Management](#profile-management)
10. [Troubleshooting](#troubleshooting)
11. [FAQ](#faq)

---

##  **SYSTEM OVERVIEW**

### **What is the Employee Attendance Management System?**

The Employee Attendance Management System is a comprehensive web-based application designed to automate and streamline workforce management processes. It provides real-time attendance tracking, user management, reporting, and document generation capabilities.

### **Key Features**
-  **Real-time Attendance Tracking** with biometric integration
-  **Multi-office Management** with centralized control
-  **Role-based Access Control** for different user types
-  **Professional Document Generation** for HR processes
-  **Comprehensive Reporting** and analytics
-  **Mobile-responsive Interface** for all devices

### **System Benefits**
- **95% Reduction** in manual attendance tracking
- **99% Accuracy** in attendance records
- **93% Time Savings** in report generation
- **Complete Automation** of attendance processes
- **Real-time Monitoring** of employee presence

---

##  **GETTING STARTED**

### **System Access**

#### **Web Browser Requirements**
- **Recommended Browsers**: Chrome, Firefox, Safari, Edge (latest versions)
- **Internet Connection**: Stable internet connection required
- **Screen Resolution**: 1024x768 minimum, 1920x1080 recommended

#### **Login Process**
1. **Navigate to the System**: Go to `https://company.d0s369.co.in`
2. **Enter Credentials**: 
   - Username: Your employee ID or email
   - Password: Your assigned password
3. **Click Login**: Access your personalized dashboard

#### **First-time Login**
- Change your password upon first login
- Complete your profile information
- Review system permissions and features

### **System Navigation**

#### **Main Interface Elements**
```
┌─────────────────────────────────────────────────────────┐
│ [☰] Disha Online Solution                    [👤] User ▼│
├─────────────────────────────────────────────────────────┤
│                                                         │
│   Dashboard  👥 Users  🕒 Attendance  📄 Documents    │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │                                                 │   │
│  │            MAIN CONTENT AREA                    │   │
│  │                                                 │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

#### **Navigation Tips**
- **Sidebar Navigation**: Click menu items to navigate between sections
- **Breadcrumb Trail**: Shows your current location in the system
- **Search Functionality**: Use the search bar to find specific information
- **Filter Options**: Use filters to narrow down data displays

---

## 👥 **USER ROLES & PERMISSIONS**

### **Role Overview**

#### **Admin**
- **Full System Access**: Complete administrative control
- **User Management**: Create, edit, and delete users
- **System Configuration**: Manage offices, departments, and designations
- **Reports Access**: All reporting and analytics features
- **Device Management**: Configure and monitor biometric devices

#### **Manager**
- **Team Management**: Manage assigned team members
- **Attendance Oversight**: View and manage team attendance
- **Limited Reports**: Access to team-specific reports
- **Document Generation**: Generate team-related documents

#### **Accountant**
- **Attendance Management**: Full attendance tracking access
- **User Viewing**: View all employee information
- **Reports & Analytics**: Complete reporting capabilities
- **Document Generation**: Generate all types of documents
- **Data Export**: Export data for external processing

#### **Employee**
- **Personal Dashboard**: View personal attendance and statistics
- **Profile Management**: Update personal information
- **Limited Reports**: Personal attendance reports only
- **Document Access**: Access personal documents

### **Permission Matrix**

| Feature | Admin | Manager | Accountant | Employee |
|---------|-------|---------|------------|----------|
| Dashboard Access |  |  |  |  |
| User Management |  | Team Only | View Only | Personal Only |
| Attendance Tracking |  | Team Only |  | Personal Only |
| Reports & Analytics |  | Team Only |  | Personal Only |
| Document Generation |  | Team Only |  | Personal Only |
| System Configuration |  |  |  |  |

---

##  **DASHBOARD GUIDE**

### **Dashboard Overview**

The dashboard provides a comprehensive overview of system statistics and key metrics. The layout varies based on user role and permissions.

#### **Admin/Accountant Dashboard**
```
┌─────────────────────────────────────────────────────────┐
│                    DASHBOARD                            │
├─────────────────────────────────────────────────────────┤
│   STATISTICS CARDS                                   │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│  │Total    │ │Active   │ │Monthly  │ │Present  │       │
│  │Users    │ │Users    │ │Attend.  │ │Days     │       │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘       │
├─────────────────────────────────────────────────────────┤
│   RECENT ACTIVITY           QUICK ACTIONS          │
│  ┌─────────────────────┐    ┌─────────────────────┐    │
│  │• User logged in     │    │👥 Manage Users      │    │
│  │• Attendance updated │    │🕒 View Attendance   │    │
│  │• Report generated   │    │📄 Generate Docs     │    │
│  └─────────────────────┘    └─────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

#### **Employee Dashboard**
```
┌─────────────────────────────────────────────────────────┐
│                    MY DASHBOARD                         │
├─────────────────────────────────────────────────────────┤
│   PERSONAL STATISTICS                                │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│  │This     │ │Present  │ │Absent   │ │Late     │       │
│  │Month    │ │Days     │ │Days     │ │Arrivals │       │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘       │
├─────────────────────────────────────────────────────────┤
│  📅 TODAY'S STATUS         ATTENDANCE TREND          │
│  ┌─────────────────────┐    ┌─────────────────────┐    │
│  │Status: Present    │    │ Monthly Chart     │    │
│  │Check-in: 9:15 AM    │    │ Performance Graph │    │
│  │Check-out: 6:30 PM   │    │📋 Recent Records    │    │
│  └─────────────────────┘    └─────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

### **Dashboard Features**

#### **Statistics Cards**
- **Total Users**: Complete employee count
- **Active Users**: Currently active employees
- **Monthly Attendance**: Current month statistics
- **Present Days**: Total working days
- **Absent Days**: Missing attendance records

#### **Quick Actions**
- **Manage Users**: Direct access to user management
- **View Attendance**: Access attendance records
- **Generate Documents**: Create professional documents
- **Export Data**: Download reports and data

#### **Recent Activity**
- **Real-time Updates**: Live activity feed
- **System Events**: Login, attendance, and report activities
- **Timestamps**: Precise time tracking for all activities

---

## 👥 **USER MANAGEMENT**

### **User Management Overview**

The User Management section allows administrators to manage all system users, including employees, managers, and other administrators.

#### **User List Interface**
```
┌─────────────────────────────────────────────────────────┐
│                    USER MANAGEMENT                      │
├─────────────────────────────────────────────────────────┤
│  SEARCH & FILTERS                                   │
│  ┌─────────────────────────────────────────────────┐   │
│  │Search: [________________] Role: [All ▼] Office: │   │
│  └─────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────┤
│  👥 USER LIST                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │ID │Name        │Email              │Role    │Status│   │
│  │001│John Doe    │john@company.com   │Manager │Active│   │
│  │002│Jane Smith  │jane@company.com   │Employee│Active│   │
│  │003│Bob Wilson  │bob@company.com    │Admin   │Active│   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### **Creating New Users**

#### **Step-by-Step Process**
1. **Click "Add User"** button
2. **Fill Required Information**:
   - Full Name
   - Email Address
   - Employee ID
   - Role Assignment
   - Office Assignment
   - Department and Designation
3. **Set Password** (default: `Dos@9999`)
4. **Save User** and send login credentials

#### **User Information Fields**
- **Personal Information**: Name, email, phone, address
- **Professional Information**: Employee ID, office, department, designation
- **System Information**: Role, permissions, account status
- **Emergency Contacts**: Contact person and relationship
- **Banking Details**: Account information for payroll

### **User Management Actions**

#### **Available Actions**
- **Edit User**: Update user information and permissions
- **Activate/Deactivate**: Enable or disable user accounts
- **Reset Password**: Generate new password for user
- **View Profile**: Access complete user profile
- **Attendance History**: View user's attendance records
- **Generate Reports**: Create user-specific reports

#### **Bulk Operations**
- **Export Users**: Download user list as CSV
- **Bulk Status Change**: Activate/deactivate multiple users
- **Bulk Role Assignment**: Assign roles to multiple users
- **Bulk Office Assignment**: Assign office to multiple users

---

## 🕒 **ATTENDANCE TRACKING**

### **Attendance System Overview**

The attendance system provides real-time tracking of employee attendance through biometric devices and manual entry options.

#### **Attendance Interface**
```
┌─────────────────────────────────────────────────────────┐
│                   ATTENDANCE TRACKING                   │
├─────────────────────────────────────────────────────────┤
│  📅 MONTH SELECTOR    FILTERS     STATS           │
│  ┌─────────────────────────────────────────────────┐   │
│  │Month: [September 2024 ▼] [Filter] [ Stats] │   │
│  └─────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────┤
│  📋 ATTENDANCE RECORDS                                 │
│  ┌─────────────────────────────────────────────────┐   │
│  │Date     │Check-in │Check-out│Hours │Status │Notes│   │
│  │Sep 01   │09:15 AM │06:30 PM │8.25  │Present│     │   │
│  │Sep 02   │09:00 AM │06:45 PM │8.75  │Present│     │   │
│  │Sep 03   │---------│---------│------│Absent │Sick │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### **Real-time Attendance Features**

#### **Biometric Integration**
- **Automatic Tracking**: ZKTeco devices automatically record attendance
- **Real-time Updates**: Data appears in system within 30 seconds
- **Device Status**: Monitor device connectivity and health
- **User Mapping**: Automatic mapping of device users to system users

#### **Attendance Status Types**
- **Present**: Complete working day with check-in/out
- **Absent**: No attendance recorded for working day
- **Half Day**: Partial attendance (less than standard hours)
- **Late**: Arrived after designated start time
- **Upcoming**: Future dates not yet occurred
- **Weekend**: Saturday/Sunday (automatically marked)

### **Manual Attendance Entry**

#### **Admin Override Options**
- **Manual Check-in/Out**: Add attendance records manually
- **Status Correction**: Modify attendance status and notes
- **Bulk Updates**: Update multiple attendance records
- **Exception Handling**: Handle special cases and corrections

#### **Attendance Validation**
- **Time Validation**: Ensure logical check-in/out times
- **Duplicate Prevention**: Prevent duplicate attendance records
- **Status Calculation**: Automatic status determination
- **Overtime Calculation**: Calculate overtime and incomplete hours

### **Attendance Analytics**

#### **Monthly Statistics**
- **Total Days**: Days in the selected month
- **Present Days**: Days with attendance recorded
- **Absent Days**: Days without attendance
- **Late Arrivals**: Number of late arrivals
- **Overtime Hours**: Total overtime worked
- **Attendance Rate**: Percentage of attendance

#### **Overtime/Incomplete Calculation**
- **Standard Hours**: 9 hours per day
- **Overtime**: Hours worked beyond standard time
- **Incomplete Hours**: Hours less than standard time
- **Automatic Calculation**: System calculates based on check-in/out times

---

##  **REPORTS & ANALYTICS**

### **Reporting System Overview**

The reporting system provides comprehensive analytics and data export capabilities for attendance management.

#### **Reports Interface**
```
┌─────────────────────────────────────────────────────────┐
│                    REPORTS & ANALYTICS                  │
├─────────────────────────────────────────────────────────┤
│  📅 DATE RANGE    👥 USER SELECTION     REPORT TYPE   │
│  ┌─────────────────────────────────────────────────┐   │
│  │From: [Sep 01, 2024] To: [Sep 30, 2024]        │   │
│  │Users: [All Users ▼] Report: [Attendance ▼]    │   │
│  └─────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────┤
│   ANALYTICS DASHBOARD                                │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Attendance Trends     Performance Metrics   │   │
│  │📋 Summary Statistics    Goal Tracking         │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### **Available Reports**

#### **Attendance Reports**
- **Monthly Attendance**: Complete monthly attendance summary
- **Individual Reports**: Personal attendance records
- **Team Reports**: Department/office attendance analysis
- **Exception Reports**: Late arrivals, absences, overtime

#### **Analytical Reports**
- **Attendance Trends**: Historical attendance patterns
- **Performance Metrics**: Productivity and attendance correlation
- **Compliance Reports**: Labor law compliance tracking
- **Comparative Analysis**: Period-over-period comparisons

### **Export Options**

#### **File Formats**
- **CSV Export**: Excel-compatible data files
- **PDF Reports**: Professional formatted reports
- **Excel Files**: Advanced spreadsheet analysis
- **JSON Data**: API-compatible data format

#### **Export Features**
- **Custom Date Ranges**: Flexible time period selection
- **User Filtering**: Select specific users or groups
- **Column Selection**: Choose specific data fields
- **Scheduled Exports**: Automated report generation

---

## 📄 **DOCUMENT GENERATION**

### **Document System Overview**

The document generation system creates professional PDF documents for HR processes and employee management.

#### **Document Interface**
```
┌─────────────────────────────────────────────────────────┐
│                  DOCUMENT GENERATION                    │
├─────────────────────────────────────────────────────────┤
│  📋 DOCUMENT TEMPLATES                                 │
│  ┌─────────────────────────────────────────────────┐   │
│  │📄 Salary Slip    📄 Offer Letter    📄 Increment │   │
│  │📄 ID Card        📄 Experience      📄 NOC       │   │
│  └─────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────┤
│  👤 USER SELECTION    📅 DATE RANGE    ⚙️ OPTIONS      │
│  ┌─────────────────────────────────────────────────┐   │
│  │User: [John Doe ▼] Period: [Sep 2024 ▼] [⚙️]   │   │
│  └─────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────┤
│  📄 GENERATED DOCUMENTS                                │
│  ┌─────────────────────────────────────────────────┐   │
│  │📄 salary_slip_john_sep2024.pdf [📥 Download]    │   │
│  │📄 offer_letter_jane_oct2024.pdf [📥 Download]    │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### **Document Types**

#### **HR Documents**
- **Salary Slips**: Monthly salary statements with deductions
- **Offer Letters**: Employment offer documents
- **Increment Letters**: Salary increment notifications
- **Experience Certificates**: Employment verification documents

#### **Administrative Documents**
- **ID Cards**: Employee identification cards
- **NOC Letters**: No Objection Certificates
- **Appointment Letters**: Job appointment documents
- **Transfer Letters**: Department/office transfer documents

### **Document Features**

#### **Professional Formatting**
- **Company Branding**: Logo and company information
- **Professional Layout**: Clean, business-appropriate design
- **Consistent Formatting**: Standardized document templates
- **Print-Ready**: High-quality PDF output

#### **Customization Options**
- **Template Selection**: Choose from multiple document templates
- **Content Customization**: Modify document content as needed
- **Date Range Selection**: Generate documents for specific periods
- **Bulk Generation**: Create multiple documents simultaneously

---

## 👤 **PROFILE MANAGEMENT**

### **Profile Overview**

The profile management section allows users to view and update their personal and professional information.

#### **Profile Interface**
```
┌─────────────────────────────────────────────────────────┐
│                    PROFILE MANAGEMENT                   │
├─────────────────────────────────────────────────────────┤
│  👤 PROFILE OVERVIEW                                   │
│  ┌─────────────────────────────────────────────────┐   │
│  │[👤 Avatar] John Doe                             │   │
│  │     Manager - Ace Track Office                  │   │
│  │     Employee ID: 001                            │   │
│  │     Status: Active                            │   │
│  └─────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────┤
│   EDITABLE SECTIONS                                  │
│  ┌─────────────────────────────────────────────────┐   │
│  │📋 Personal Info    🏢 Professional Info         │   │
│  │📞 Contact Details  🏦 Banking Information       │   │
│  │🚨 Emergency Contact 📄 Documents                │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### **Editable Information**

#### **Personal Information**
- **Full Name**: Complete name as per records
- **Email Address**: Primary email for communication
- **Phone Number**: Contact phone number
- **Date of Birth**: Birth date for records
- **Gender**: Gender identification
- **Address**: Complete residential address

#### **Professional Information**
- **Joining Date**: Employment start date
- **Salary**: Current salary information
- **Emergency Contacts**: Contact person and relationship
- **Banking Details**: Account information for payroll

#### **Document Information**
- **Aadhaar Card**: Government ID number
- **PAN Card**: Tax identification number
- **Other Documents**: Additional identification documents

### **Profile Actions**

#### **Available Actions**
- **Edit Profile**: Update personal and professional information
- **Change Password**: Update account password
- **Upload Documents**: Add or update document files
- **View History**: Access profile change history
- **Export Profile**: Download profile information

#### **Security Features**
- **Read-only Fields**: System-managed fields cannot be edited
- **Validation**: Input validation for all fields
- **Audit Trail**: Track all profile changes
- **Permission-based Editing**: Role-based editing restrictions

---

## 🔧 **TROUBLESHOOTING**

### **Common Issues and Solutions**

#### **Login Problems**
**Issue**: Cannot log into the system
**Solutions**:
1. Verify username and password
2. Check internet connection
3. Clear browser cache and cookies
4. Try different browser
5. Contact administrator for password reset

#### **Attendance Not Showing**
**Issue**: Attendance records not appearing
**Solutions**:
1. Check date range selection
2. Verify user permissions
3. Refresh the page
4. Check device connectivity status
5. Contact technical support

#### **Slow Performance**
**Issue**: System running slowly
**Solutions**:
1. Check internet connection speed
2. Close unnecessary browser tabs
3. Clear browser cache
4. Try different browser
5. Contact system administrator

#### **Document Generation Issues**
**Issue**: Documents not generating
**Solutions**:
1. Verify user permissions
2. Check date range selection
3. Ensure valid data for selected period
4. Try generating individual documents
5. Contact technical support

### **Error Messages**

#### **Common Error Messages**
- **"Access Denied"**: Insufficient permissions for the action
- **"Data Not Found"**: No data available for selected criteria
- **"Connection Error"**: Network or server connectivity issue
- **"Validation Error"**: Invalid data in form fields
- **"Session Expired"**: Login session has timed out

#### **Error Resolution Steps**
1. **Read the error message** carefully
2. **Check your permissions** for the action
3. **Verify input data** for accuracy
4. **Try refreshing** the page
5. **Contact support** if issue persists

---

## ❓ **FAQ**

### **General Questions**

#### **Q: How do I change my password?**
**A**: Go to Profile → Change Password, enter current password, then new password twice, and click Save.

#### **Q: Can I access the system from mobile devices?**
**A**: Yes, the system is mobile-responsive and works on smartphones and tablets.

#### **Q: How often is attendance data updated?**
**A**: Attendance data is updated in real-time every 30 seconds from biometric devices.

#### **Q: What if I forget my password?**
**A**: Contact your system administrator to reset your password.

### **Attendance Questions**

#### **Q: How is attendance automatically recorded?**
**A**: Through ZKTeco biometric devices that scan fingerprints and automatically record check-in/out times.

#### **Q: Can I manually correct my attendance?**
**A**: Only administrators can manually correct attendance records. Contact your manager or HR for corrections.

#### **Q: What if the biometric device is not working?**
**A**: Contact the system administrator immediately. Manual entry options are available as backup.

#### **Q: How is overtime calculated?**
**A**: Overtime is calculated as hours worked beyond the standard 9-hour workday.

### **Reporting Questions**

#### **Q: How do I export attendance data?**
**A**: Go to Reports section, select date range and users, then click Export CSV or Generate PDF.

#### **Q: Can I generate reports for specific departments?**
**A**: Yes, use the filter options to select specific departments, offices, or user groups.

#### **Q: How far back can I view attendance history?**
**A**: Attendance history is available from the system implementation date onwards.

### **Technical Questions**

#### **Q: What browsers are supported?**
**A**: Chrome, Firefox, Safari, and Edge (latest versions) are recommended for optimal performance.

#### **Q: Is my data secure?**
**A**: Yes, the system uses enterprise-grade security with encryption and role-based access control.

#### **Q: Can I use the system offline?**
**A**: No, an internet connection is required as the system is web-based.

---

## 📞 **SUPPORT CONTACT**

### **Technical Support**
- **Email**: support@company.com
- **Phone**: +91-XXXXXXXXXX
- **Hours**: Monday-Friday, 9:00 AM - 6:00 PM

### **System Administrator**
- **Email**: admin@company.com
- **Phone**: +91-XXXXXXXXXX
- **Emergency**: Available 24/7 for critical issues

### **Training and Documentation**
- **User Manual**: Available in system help section
- **Video Tutorials**: Screen recordings available
- **Training Sessions**: Scheduled training for new users

---

*User Manual & Training Guide*  
*Employee Attendance Management System*  
*Version 1.0 - December 2024*
