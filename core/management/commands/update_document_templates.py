from django.core.management.base import BaseCommand
from core.models import DocumentTemplate, CustomUser


class Command(BaseCommand):
    help = 'Update existing document templates with logo integration'

    def handle(self, *args, **options):
        self.stdout.write('Updating document templates with logo integration...')
        
        # Get or create admin user for template creation
        admin_user = CustomUser.objects.filter(role='admin').first()
        if not admin_user:
            self.stdout.write(self.style.WARNING('No admin user found. Updating templates without created_by.'))
            admin_user = None
        
        # Professional Offer Letter Template with Logo
        offer_letter_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                    margin: 0; 
                    padding: 0; 
                    line-height: 1.6; 
                    color: #333;
                    background-color: #ffffff;
                }
                .page { 
                    max-width: 800px; 
                    margin: 0 auto; 
                    padding: 40px; 
                    background: white;
                    box-shadow: 0 0 20px rgba(0,0,0,0.1);
                }
                .header-strip { 
                    background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%); 
                    height: 3px; 
                    margin-bottom: 20px; 
                }
                .header { 
                    display: flex; 
                    align-items: center; 
                    margin-bottom: 30px; 
                    padding-bottom: 20px; 
                    border-bottom: 2px solid #e5e7eb; 
                }
                .logo-container { 
                    margin-right: 20px; 
                }
                .company-logo { 
                    max-height: 80px; 
                    max-width: 120px; 
                    object-fit: contain; 
                }
                .company-info { 
                    flex: 1; 
                }
                .company-name { 
                    font-size: 28px; 
                    font-weight: 700; 
                    color: #1e40af; 
                    margin: 0 0 8px 0; 
                    letter-spacing: 1px;
                }
                .company-address { 
                    font-size: 13px; 
                    color: #6b7280; 
                    line-height: 1.4; 
                    margin: 0;
                }
                .document-date { 
                    font-size: 14px; 
                    color: #374151; 
                    margin-bottom: 30px; 
                    text-align: right;
                }
                .title { 
                    text-align: center; 
                    font-size: 24px; 
                    font-weight: 700; 
                    margin: 40px 0; 
                    color: #1e40af;
                    text-transform: uppercase;
                    letter-spacing: 2px;
                }
                .letter-info {
                    background: #f8fafc;
                    padding: 20px;
                    border-left: 4px solid #1e40af;
                    margin-bottom: 30px;
                }
                .letter-info p {
                    margin: 5px 0;
                    font-size: 14px;
                }
                .content { 
                    margin: 30px 0; 
                    font-size: 15px;
                    line-height: 1.7;
                }
                .content p {
                    margin-bottom: 15px;
                }
                .highlight {
                    background: #dbeafe;
                    padding: 15px;
                    border-radius: 8px;
                    margin: 20px 0;
                    border-left: 4px solid #3b82f6;
                }
                .signature { 
                    margin-top: 50px; 
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-end;
                }
                .signature-left {
                    flex: 1;
                }
                .signature-right {
                    text-align: right;
                }
                .footer { 
                    margin-top: 50px; 
                    text-align: center; 
                    font-size: 12px; 
                    color: #6b7280; 
                    border-top: 1px solid #e5e7eb; 
                    padding-top: 20px; 
                }
                .footer-strip {
                    background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
                    height: 2px;
                    margin-top: 20px;
                }
                .employee-name {
                    font-weight: 700;
                    color: #1e40af;
                    font-size: 16px;
                }
            </style>
        </head>
        <body>
            <div class="page">
                <div class="header-strip"></div>
                
                <div class="header">
                    <div class="logo-container">
                        <img src="{{ logo_url }}" alt="Company Logo" class="company-logo">
                    </div>
                    <div class="company-info">
                        <h1 class="company-name">DISHA ONLINE SOLUTION</h1>
                        <p class="company-address">
                            Bhumiraj Costarica, 9th Floor Office No- 907, Plot No- 1 & 2,<br>
                            Sector 18, Sanpada, Navi Mumbai, Maharashtra 400705
                        </p>
                    </div>
                </div>
                
                <div class="document-date">{{ current_date }}</div>
                
                <div class="title">Offer Letter</div>
                
                <div class="letter-info">
                    <p><strong>Date:</strong> {{ current_date }}</p>
                    <p><strong>To:</strong> {{ employee_name }}</p>
                    <p><strong>Subject:</strong> Job Offer - {{ position }}</p>
                </div>
                
                <div class="content">
                    <p>Dear <strong>{{ employee_name }}</strong>,</p>
                    
                    <p>We are pleased to offer you the position of <strong>{{ position }}</strong> at <strong>Disha Online SOLUTION</strong>. We are confident that your skills and experience will contribute significantly to the growth and success of our organization.</p>
                    
                    <div class="highlight">
                        <p><strong>Position Details:</strong></p>
                        <p><strong>Starting Date:</strong> {{ start_date }}</p>
                        <p><strong>Starting Salary:</strong> {{ starting_salary }}</p>
                    </div>
                    
                    <p>This offer is contingent upon your acceptance and completion of all pre-employment requirements. Please find the employee handbook enclosed, which contains detailed information about our medical and retirement benefits, company policies, and procedures.</p>
                    
                    <p>We believe you will be a valuable addition to our team and look forward to your contributions to our continued success.</p>
                    
                    <p>Please confirm your acceptance of this offer by signing and returning a copy of this offer letter within 7 days.</p>
                    
                    <p>We are excited to welcome you on board and look forward to a successful working relationship.</p>
                </div>
                
                <div class="signature">
                    <div class="signature-left">
                        <p>Sincerely,</p>
                        <br><br>
                        <p>Manager<br>Disha Online SOLUTION</p>
                    </div>
                    <div class="signature-right">
                        <p class="employee-name">{{ employee_name }}</p>
                    </div>
                </div>
                
                <div class="footer">
                    <p>This is a computer-generated document and does not require a signature.</p>
                </div>
                
                <div class="footer-strip"></div>
            </div>
        </body>
        </html>
        """
        
        # Updated Salary Increment Template with Logo
        salary_increment_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
                .header { text-align: center; margin-bottom: 30px; border-bottom: 2px solid #1e40af; padding-bottom: 20px; }
                .logo-container { margin-bottom: 15px; }
                .company-logo { max-height: 80px; max-width: 200px; }
                .company-name { font-size: 24px; font-weight: bold; color: #1e40af; margin-top: 10px; }
                .company-address { font-size: 12px; color: #666; margin-top: 10px; }
                .date { font-weight: bold; margin-bottom: 20px; }
                .title { text-align: center; font-size: 20px; font-weight: bold; margin: 30px 0; color: #1e40af; }
                .content { margin: 20px 0; }
                .signature { margin-top: 40px; }
                .footer { margin-top: 40px; text-align: center; font-size: 12px; color: #666; border-top: 1px solid #e5e7eb; padding-top: 20px; }
            </style>
        </head>
        <body>
            <div class="header">
                <div class="logo-container">
                    <img src="{{ logo_url }}" alt="Company Logo" class="company-logo">
                </div>
                <div class="company-name">DISHA ONLINE SOLUTION</div>
                <div class="company-address">
                    Bhumiraj Costarica, 9th Floor Office No- 907, Plot No- 1 & 2,<br>
                    Sector 18, Sanpada, Navi Mumbai, Maharashtra 400705
                </div>
            </div>
            
            <div class="date">Date: {{ effective_date }}</div>
            
            <div class="title">SALARY INCREMENT LETTER</div>
            
            <div class="content">
                <p>Dear <strong>{{ employee_name }}</strong>,</p>
                
                <p>We are pleased to inform you that your salary has been increased effective from <strong>{{ effective_date }}</strong>.</p>
                
                <p>Your current salary details are as follows:</p>
                <ul>
                    <li><strong>Previous Salary:</strong> {{ previous_salary }}</li>
                    <li><strong>New Salary:</strong> {{ new_salary }}</li>
                    <li><strong>Increment Percentage:</strong> {{ increment_percentage }}</li>
                </ul>
                
                <p>This increment reflects your valuable contribution to our organization and your continued dedication to excellence.</p>
                
                <p>We appreciate your hard work and look forward to your continued success with Disha Online SOLUTION.</p>
                
                <div class="signature">
                    <p>Sincerely,</p>
                    <p>Manager<br>Disha Online SOLUTION</p>
                </div>
            </div>
            
            <div class="footer">
                <p><strong>{{ employee_name }}</strong></p>
            </div>
        </body>
        </html>
        """
        
        # Update existing templates
        updated_count = 0
        
        # Update Offer Letter template
        offer_template = DocumentTemplate.objects.filter(
            document_type='offer_letter',
            name='Default Offer Letter'
        ).first()
        
        if offer_template:
            offer_template.template_content = offer_letter_template
            offer_template.save()
            updated_count += 1
            self.stdout.write(f'Updated: {offer_template.name}')
        else:
            # Create new template if doesn't exist
            DocumentTemplate.objects.create(
                name='Default Offer Letter',
                document_type='offer_letter',
                template_content=offer_letter_template,
                is_active=True,
                created_by=admin_user
            )
            updated_count += 1
            self.stdout.write('Created: Default Offer Letter')
        
        # Update Salary Increment template
        increment_template = DocumentTemplate.objects.filter(
            document_type='salary_increment',
            name='Default Salary Increment Letter'
        ).first()
        
        if increment_template:
            increment_template.template_content = salary_increment_template
            increment_template.save()
            updated_count += 1
            self.stdout.write(f'Updated: {increment_template.name}')
        else:
            # Create new template if doesn't exist
            DocumentTemplate.objects.create(
                name='Default Salary Increment Letter',
                document_type='salary_increment',
                template_content=salary_increment_template,
                is_active=True,
                created_by=admin_user
            )
            updated_count += 1
            self.stdout.write('Created: Default Salary Increment Letter')
        
        # Add Salary Slip template
        salary_slip_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                    margin: 0; 
                    padding: 0; 
                    line-height: 1.6; 
                    color: #333;
                    background-color: #ffffff;
                }
                .page { 
                    max-width: 800px; 
                    margin: 0 auto; 
                    padding: 40px; 
                    background: white;
                    box-shadow: 0 0 20px rgba(0,0,0,0.1);
                }
                .header-strip { 
                    background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%); 
                    height: 3px; 
                    margin-bottom: 20px; 
                }
                .header { 
                    display: flex; 
                    align-items: center; 
                    margin-bottom: 30px; 
                    padding-bottom: 20px; 
                    border-bottom: 2px solid #e5e7eb; 
                }
                .logo-container { 
                    margin-right: 20px; 
                }
                .company-logo { 
                    max-height: 80px; 
                    max-width: 120px; 
                    object-fit: contain; 
                }
                .company-info { 
                    flex: 1; 
                }
                .company-name { 
                    font-size: 28px; 
                    font-weight: 700; 
                    color: #1e40af; 
                    margin: 0 0 8px 0; 
                    letter-spacing: 1px;
                }
                .company-address { 
                    font-size: 13px; 
                    color: #6b7280; 
                    line-height: 1.4; 
                    margin: 0;
                }
                .document-title { 
                    text-align: center; 
                    font-size: 24px; 
                    font-weight: 700; 
                    margin: 30px 0; 
                    color: #1e40af;
                    text-transform: uppercase;
                    letter-spacing: 2px;
                }
                .salary-month {
                    text-align: center;
                    font-size: 18px;
                    font-weight: 600;
                    color: #374151;
                    margin-bottom: 30px;
                    background: #f8fafc;
                    padding: 10px;
                    border-radius: 8px;
                }
                .employee-section {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 30px;
                    margin-bottom: 30px;
                }
                .employee-info, .bank-info {
                    background: #f8fafc;
                    padding: 20px;
                    border-radius: 8px;
                    border-left: 4px solid #1e40af;
                }
                .section-title {
                    font-size: 16px;
                    font-weight: 700;
                    color: #1e40af;
                    margin-bottom: 15px;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }
                .info-row {
                    display: flex;
                    justify-content: space-between;
                    margin: 8px 0;
                    padding: 5px 0;
                    border-bottom: 1px solid #e5e7eb;
                }
                .info-row:last-child {
                    border-bottom: none;
                }
                .info-label {
                    font-weight: 600;
                    color: #374151;
                }
                .info-value {
                    font-weight: 500;
                    color: #1e40af;
                }
                .salary-table {
                    width: 100%;
                    border-collapse: collapse;
                    margin: 30px 0;
                    background: white;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }
                .salary-table th {
                    background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
                    color: white;
                    padding: 15px;
                    text-align: left;
                    font-weight: 700;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }
                .salary-table td {
                    padding: 12px 15px;
                    border-bottom: 1px solid #e5e7eb;
                }
                .salary-table tr:nth-child(even) {
                    background: #f8fafc;
                }
                .salary-table tr:last-child td {
                    border-bottom: none;
                    font-weight: 700;
                    background: #dbeafe;
                    color: #1e40af;
                }
                .amount {
                    text-align: right;
                    font-weight: 600;
                }
                .net-salary {
                    background: #dbeafe !important;
                    font-weight: 700;
                    font-size: 16px;
                    color: #1e40af;
                }
                .footer { 
                    margin-top: 40px; 
                    text-align: center; 
                    font-size: 12px; 
                    color: #6b7280; 
                    border-top: 1px solid #e5e7eb; 
                    padding-top: 20px; 
                }
                .footer-strip {
                    background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
                    height: 2px;
                    margin-top: 20px;
                }
                .generated-info {
                    text-align: right;
                    font-size: 11px;
                    color: #9ca3af;
                    margin-top: 20px;
                }
            </style>
        </head>
        <body>
            <div class="page">
                <div class="header-strip"></div>
                
                <div class="header">
                    <div class="logo-container">
                        <img src="{{ logo_url }}" alt="Company Logo" class="company-logo">
                    </div>
                    <div class="company-info">
                        <h1 class="company-name">DISHA ONLINE SOLUTION</h1>
                        <p class="company-address">
                            Bhumiraj Costarica, 9th Floor Office No- 907, Plot No- 1 & 2,<br>
                            Sector 18, Sanpada, Navi Mumbai, Maharashtra 400705
                        </p>
                    </div>
                </div>
                
                <div class="document-title">Salary Slip</div>
                <div class="salary-month">{{ salary_month }} {{ salary_year }}</div>
                
                <div class="employee-section">
                    <div class="employee-info">
                        <div class="section-title">Employee Information</div>
                        <div class="info-row">
                            <span class="info-label">Employee Name:</span>
                            <span class="info-value">{{ employee_name }}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Employee ID:</span>
                            <span class="info-value">{{ employee_id }}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Designation:</span>
                            <span class="info-value">{{ employee_designation }}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Department:</span>
                            <span class="info-value">{{ employee_department }}</span>
                        </div>
                    </div>
                    
                    <div class="bank-info">
                        <div class="section-title">Bank & Other Details</div>
                        <div class="info-row">
                            <span class="info-label">Bank Name:</span>
                            <span class="info-value">{{ bank_name }}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Account No:</span>
                            <span class="info-value">{{ account_number }}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Date of Joining:</span>
                            <span class="info-value">{{ date_of_joining }}</span>
                        </div>
                    </div>
                </div>
                
                <table class="salary-table">
                    <thead>
                        <tr>
                            <th>Component</th>
                            <th class="amount">Amount</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>Basic Salary</td>
                            <td class="amount">{{ basic_salary }}</td>
                        </tr>
                        <tr>
                            <td>Extra Days Pay</td>
                            <td class="amount">{{ extra_days_pay }}</td>
                        </tr>
                        <tr>
                            <td>Total Salary</td>
                            <td class="amount">{{ total_salary }}</td>
                        </tr>
                        <tr>
                            <td class="net-salary">NET SALARY</td>
                            <td class="amount net-salary">{{ net_salary }}</td>
                        </tr>
                    </tbody>
                </table>
                
                <div class="footer">
                    <p>This is a computer generated salary slip and does not require signature</p>
                </div>
                
                <div class="generated-info">
                    Generated on: {{ current_date }}
                </div>
                
                <div class="footer-strip"></div>
            </div>
        </body>
        </html>
        """
        
        # Update Salary Slip template
        slip_template = DocumentTemplate.objects.filter(
            document_type='salary_slip',
            name='Default Salary Slip'
        ).first()
        
        if slip_template:
            slip_template.template_content = salary_slip_template
            slip_template.save()
            updated_count += 1
            self.stdout.write(f'Updated: {slip_template.name}')
        else:
            # Create new template if doesn't exist
            DocumentTemplate.objects.create(
                name='Default Salary Slip',
                document_type='salary_slip',
                template_content=salary_slip_template,
                is_active=True,
                created_by=admin_user
            )
            updated_count += 1
            self.stdout.write('Created: Default Salary Slip')
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully updated {updated_count} document templates with logo integration!')
        )
