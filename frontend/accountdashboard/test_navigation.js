// Test script to verify navigation items for accountant role
import { getNavigationForRole, ROUTES } from './src/config/routes.js';

console.log('Testing navigation for accountant role...\n');

const accountantNavigation = getNavigationForRole('accountant');

console.log('Available navigation items for accountant:');
accountantNavigation.forEach((item, index) => {
  console.log(`${index + 1}. ${item.name}`);
  console.log(`   Route: ${item.href}`);
  console.log(`   Icon: ${item.icon}`);
  console.log(`   Description: ${item.description}`);
  console.log(`   Read Only: ${item.readOnly}`);
  console.log('');
});

console.log('Expected routes:');
console.log('- Dashboard');
console.log('- Users (View Only)');
console.log('- Attendance (View Only)');
console.log('- Reports (View Only)');
console.log('- Offices (View Only)');
console.log('- Leaves');
console.log('- Documents');
console.log('- Resignations');
console.log('- Profile');

console.log('\nAll routes should be visible in the sidebar now!');
