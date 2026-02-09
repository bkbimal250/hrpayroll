# 🤝 Contributing Guidelines

Thank you for your interest in contributing to the Employee Attendance Manager Dashboard! This document provides guidelines and information for contributors.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)

## 📜 Code of Conduct

### Our Pledge
We are committed to providing a welcoming and inspiring community for all. Please read and follow our code of conduct:

- **Be respectful**: Treat everyone with respect and kindness
- **Be inclusive**: Welcome newcomers and help them learn
- **Be constructive**: Provide helpful feedback and suggestions
- **Be patient**: Remember that everyone is learning

### Unacceptable Behavior
- Harassment, discrimination, or inappropriate language
- Personal attacks or trolling
- Spam or off-topic discussions
- Sharing private information without permission

## 🚀 Getting Started

### Prerequisites
- **Node.js**: 16.x or higher
- **npm**: 8.x or higher
- **Git**: Latest version
- **Code Editor**: VS Code, WebStorm, or similar
- **Browser**: Chrome, Firefox, Safari, or Edge

### Fork and Clone
```bash
# Fork the repository on GitHub
# Then clone your fork
git clone https://github.com/your-username/EmployeeAttendance.git
cd EmployeeAttendance/frontend/ManagerDashboard

# Add upstream remote
git remote add upstream https://github.com/original-owner/EmployeeAttendance.git
```

### Development Setup
```bash
# Install dependencies
npm install

# Create environment file
cp .env.example .env.local

# Start development server
npm run dev
```

## 🛠️ Development Setup

### Environment Configuration
Create a `.env.local` file with the following variables:

```env
# API Configuration
VITE_API_BASE_URL=http://localhost:8000/api
VITE_WEBSOCKET_URL=ws://localhost:8000/ws/attendance/

# Development Features
VITE_ENABLE_DEBUG=true
VITE_ENABLE_HOT_RELOAD=true
VITE_ENABLE_ANALYTICS=false

# Authentication (for testing)
VITE_TEST_USERNAME=test@company.com
VITE_TEST_PASSWORD=testpassword
```

### Development Tools
Install recommended VS Code extensions:

```json
// .vscode/extensions.json
{
  "recommendations": [
    "esbenp.prettier-vscode",
    "dbaeumer.vscode-eslint",
    "bradlc.vscode-tailwindcss",
    "ms-vscode.vscode-typescript-next",
    "formulahendry.auto-rename-tag",
    "christian-kohler.path-intellisense"
  ]
}
```

### VS Code Settings
```json
// .vscode/settings.json
{
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  },
  "emmet.includeLanguages": {
    "javascript": "javascriptreact"
  },
  "tailwindCSS.includeLanguages": {
    "javascript": "javascript",
    "html": "HTML"
  }
}
```

## 📝 Coding Standards

### JavaScript/React Standards

#### Component Structure
```jsx
// ✅ Good: Functional component with hooks
import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';

const EmployeeCard = ({ employee, onEdit, onDelete }) => {
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    // Component logic
  }, []);

  const handleEdit = () => {
    onEdit(employee.id);
  };

  return (
    <div className="employee-card">
      <h3>{employee.name}</h3>
      <button onClick={handleEdit}>Edit</button>
    </div>
  );
};

EmployeeCard.propTypes = {
  employee: PropTypes.object.isRequired,
  onEdit: PropTypes.func.isRequired,
  onDelete: PropTypes.func.isRequired
};

export default EmployeeCard;
```

#### Naming Conventions
```javascript
// ✅ Good: Descriptive names
const employeeAttendanceData = [];
const isUserAuthenticated = true;
const handleSubmitForm = () => {};

// ❌ Bad: Unclear names
const data = [];
const flag = true;
const handleClick = () => {};
```

#### File Organization
```
src/
├── Components/
│   ├── AttendanceFiles/
│   │   ├── AttendanceOverview.jsx
│   │   ├── AttendanceTable.jsx
│   │   └── index.js
│   └── common/
│       ├── Button.jsx
│       └── Input.jsx
├── hooks/
│   ├── useAuth.js
│   └── useApi.js
├── services/
│   ├── api.js
│   └── websocket.js
└── utils/
    ├── dateUtils.js
    └── validation.js
```

### CSS/Styling Standards

#### Tailwind CSS Usage
```jsx
// ✅ Good: Semantic class names
<div className="flex items-center justify-between p-4 bg-white rounded-lg shadow-md">
  <h2 className="text-xl font-semibold text-gray-900">Employee List</h2>
  <button className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">
    Add Employee
  </button>
</div>

// ❌ Bad: Inline styles or non-semantic classes
<div style={{ display: 'flex', padding: '16px' }}>
  <h2 className="big-title">Employee List</h2>
</div>
```

#### Custom CSS Guidelines
```css
/* ✅ Good: Component-specific styles */
.employee-card {
  @apply bg-white rounded-lg shadow-md p-4 hover:shadow-lg transition-shadow;
}

.employee-card__header {
  @apply flex items-center justify-between mb-4;
}

.employee-card__title {
  @apply text-lg font-semibold text-gray-900;
}

/* ❌ Bad: Global styles without purpose */
.big-text {
  font-size: 20px;
}

.red-button {
  background-color: red;
}
```

### API Integration Standards

#### Service Layer Pattern
```javascript
// ✅ Good: Centralized API service
// services/employeeAPI.js
import api from './api';

export const employeeAPI = {
  getEmployees: (params) => api.get('/employees/', { params }),
  getEmployee: (id) => api.get(`/employees/${id}/`),
  createEmployee: (data) => api.post('/employees/', data),
  updateEmployee: (id, data) => api.put(`/employees/${id}/`, data),
  deleteEmployee: (id) => api.delete(`/employees/${id}/`)
};

// ❌ Bad: Direct API calls in components
const MyComponent = () => {
  const [employees, setEmployees] = useState([]);
  
  useEffect(() => {
    fetch('/api/employees/')
      .then(res => res.json())
      .then(data => setEmployees(data));
  }, []);
};
```

#### Error Handling
```javascript
// ✅ Good: Comprehensive error handling
const fetchEmployees = async () => {
  try {
    setIsLoading(true);
    const response = await employeeAPI.getEmployees();
    setEmployees(response.data);
  } catch (error) {
    console.error('Failed to fetch employees:', error);
    setError('Failed to load employees. Please try again.');
  } finally {
    setIsLoading(false);
  }
};

// ❌ Bad: No error handling
const fetchEmployees = async () => {
  const response = await employeeAPI.getEmployees();
  setEmployees(response.data);
};
```

## 📋 Commit Guidelines

### Commit Message Format
```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Types
- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, etc.)
- **refactor**: Code refactoring
- **test**: Adding or updating tests
- **chore**: Maintenance tasks

### Examples
```bash
# ✅ Good commit messages
feat(attendance): add real-time attendance tracking
fix(api): resolve CORS issues with authentication
docs(readme): update installation instructions
style(components): format code with prettier
refactor(utils): optimize date formatting functions
test(api): add unit tests for employee service
chore(deps): update dependencies to latest versions

# ❌ Bad commit messages
fix stuff
update
changes
work in progress
```

### Commit Process
```bash
# 1. Stage your changes
git add .

# 2. Commit with descriptive message
git commit -m "feat(attendance): add real-time WebSocket integration"

# 3. Push to your fork
git push origin feature/websocket-integration

# 4. Create pull request
```

## 🔄 Pull Request Process

### Before Submitting
- [ ] Code follows project standards
- [ ] All tests pass
- [ ] Documentation updated
- [ ] No console errors or warnings
- [ ] Responsive design tested
- [ ] Cross-browser compatibility verified

### PR Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Screenshots (if applicable)
Add screenshots to help explain your changes

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes
```

### Review Process
1. **Automated Checks**: CI/CD pipeline runs tests
2. **Code Review**: At least one maintainer reviews
3. **Testing**: Manual testing by reviewer
4. **Approval**: Maintainer approves and merges

## 🐛 Issue Reporting

### Bug Reports
When reporting bugs, include:

```markdown
## Bug Description
Clear description of the bug

## Steps to Reproduce
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

## Expected Behavior
What you expected to happen

## Actual Behavior
What actually happened

## Environment
- OS: [e.g., Windows 10, macOS 12]
- Browser: [e.g., Chrome 91, Firefox 89]
- Node.js: [e.g., 16.14.0]
- npm: [e.g., 8.3.0]

## Additional Context
Any other relevant information
```

### Feature Requests
```markdown
## Feature Description
Clear description of the feature

## Use Case
Why is this feature needed?

## Proposed Solution
How should this feature work?

## Alternatives
Any alternative solutions considered?

## Additional Context
Any other relevant information
```

## 🧪 Testing Guidelines

### Unit Testing
```javascript
// ✅ Good: Comprehensive unit tests
import { render, screen, fireEvent } from '@testing-library/react';
import EmployeeCard from '../EmployeeCard';

describe('EmployeeCard', () => {
  const mockEmployee = {
    id: 1,
    name: 'John Doe',
    email: 'john@example.com'
  };

  it('renders employee information correctly', () => {
    render(<EmployeeCard employee={mockEmployee} />);
    
    expect(screen.getByText('John Doe')).toBeInTheDocument();
    expect(screen.getByText('john@example.com')).toBeInTheDocument();
  });

  it('calls onEdit when edit button is clicked', () => {
    const mockOnEdit = jest.fn();
    render(<EmployeeCard employee={mockEmployee} onEdit={mockOnEdit} />);
    
    fireEvent.click(screen.getByText('Edit'));
    expect(mockOnEdit).toHaveBeenCalledWith(1);
  });
});
```

### Integration Testing
```javascript
// ✅ Good: API integration tests
import { employeeAPI } from '../services/employeeAPI';

describe('Employee API', () => {
  it('fetches employees successfully', async () => {
    const mockResponse = { data: [{ id: 1, name: 'John Doe' }] };
    jest.spyOn(api, 'get').mockResolvedValue(mockResponse);
    
    const result = await employeeAPI.getEmployees();
    expect(result.data).toEqual(mockResponse.data);
  });
});
```

### E2E Testing
```javascript
// ✅ Good: End-to-end tests
describe('Employee Management', () => {
  it('allows creating a new employee', () => {
    cy.visit('/employees');
    cy.get('[data-testid="add-employee-btn"]').click();
    cy.get('[data-testid="employee-name"]').type('Jane Smith');
    cy.get('[data-testid="employee-email"]').type('jane@example.com');
    cy.get('[data-testid="save-employee-btn"]').click();
    cy.get('[data-testid="employee-list"]').should('contain', 'Jane Smith');
  });
});
```

### Test Commands
```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:coverage

# Run E2E tests
npm run test:e2e
```

## 📚 Documentation

### Code Documentation
```javascript
/**
 * Fetches employee attendance data for a specific date range
 * @param {string} employeeId - The employee ID
 * @param {string} startDate - Start date in YYYY-MM-DD format
 * @param {string} endDate - End date in YYYY-MM-DD format
 * @returns {Promise<Object>} Promise that resolves to attendance data
 * @throws {Error} Throws error if API request fails
 */
const fetchEmployeeAttendance = async (employeeId, startDate, endDate) => {
  // Implementation
};
```

### Component Documentation
```jsx
/**
 * EmployeeCard component for displaying employee information
 * 
 * @param {Object} props - Component props
 * @param {Object} props.employee - Employee data object
 * @param {Function} props.onEdit - Callback function for edit action
 * @param {Function} props.onDelete - Callback function for delete action
 * @param {boolean} props.isLoading - Loading state indicator
 * 
 * @example
 * <EmployeeCard 
 *   employee={employeeData}
 *   onEdit={handleEdit}
 *   onDelete={handleDelete}
 *   isLoading={false}
 * />
 */
const EmployeeCard = ({ employee, onEdit, onDelete, isLoading }) => {
  // Component implementation
};
```

### README Updates
When adding new features, update relevant documentation:

- [Main README](./README.md) - Feature overview
- [API README](./API_README.md) - API endpoints
- [Deployment README](./DEPLOYMENT_README.md) - Deployment changes
- Feature-specific READMEs - Detailed feature documentation

## 🎯 Development Workflow

### Feature Development
1. **Create Branch**: `git checkout -b feature/your-feature-name`
2. **Develop**: Write code following standards
3. **Test**: Write and run tests
4. **Document**: Update documentation
5. **Commit**: Follow commit guidelines
6. **Push**: Push to your fork
7. **PR**: Create pull request

### Bug Fix Workflow
1. **Create Branch**: `git checkout -b fix/issue-description`
2. **Reproduce**: Reproduce the bug
3. **Fix**: Implement the fix
4. **Test**: Ensure fix works and doesn't break other features
5. **Commit**: Follow commit guidelines
6. **Push**: Push to your fork
7. **PR**: Create pull request

### Hotfix Workflow
1. **Create Branch**: `git checkout -b hotfix/critical-issue`
2. **Fix**: Implement minimal fix
3. **Test**: Thoroughly test the fix
4. **Commit**: Follow commit guidelines
5. **Push**: Push to your fork
6. **PR**: Create urgent pull request

## 🏷️ Release Process

### Version Numbering
We follow [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Checklist
- [ ] All tests pass
- [ ] Documentation updated
- [ ] Changelog updated
- [ ] Version bumped
- [ ] Release notes prepared
- [ ] Deployment tested

## 🆘 Getting Help

### Resources
- **Documentation**: Check project documentation
- **Issues**: Search existing issues
- **Discussions**: Use GitHub Discussions
- **Code Review**: Ask for help in PR comments

### Contact
- **Maintainers**: @project-maintainers
- **Community**: GitHub Discussions
- **Email**: project@company.com

## 🎉 Recognition

### Contributors
We recognize all contributors in our:
- **README**: Contributors section
- **Changelog**: Release notes
- **Website**: Contributors page

### Types of Contributions
- **Code**: Bug fixes, features, improvements
- **Documentation**: README updates, guides, tutorials
- **Testing**: Test cases, bug reports
- **Design**: UI/UX improvements, mockups
- **Community**: Helping others, answering questions

---

**Thank you for contributing to the Employee Attendance Manager Dashboard!**

Your contributions help make this project better for everyone. If you have any questions, don't hesitate to ask for help.
