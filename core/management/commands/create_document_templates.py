from django.core.management.base import BaseCommand
from core.models import DocumentTemplate, CustomUser


class Command(BaseCommand):
    help = 'Create default document templates for offer letters and salary increment letters'

    def handle(self, *args, **options):
        self.stdout.write('Creating default document templates...')
        
        # Get or create admin user for template creation
        admin_user = CustomUser.objects.filter(role='admin').first()
        if not admin_user:
            self.stdout.write(self.style.WARNING('No admin user found. Creating templates without created_by.'))
            admin_user = None
        
        # Offer Letter Template
        offer_letter_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
                .header { text-align: center; margin-bottom: 30px; border-bottom: 1px solid #1e40af; padding-bottom: 20px; }
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
            
            <div class="date">{{ current_date }}</div>
            
            <div class="title">OFFER LETTER</div>
            
            <div class="content">
                <p>Dear <strong>{{ employee_name }}</strong>,</p>
                
                <p>We are pleased to offer you the position of <strong>{{ position }}</strong> at <strong>Disha Online SOLUTION</strong>. We feel confident that you will contribute your skills and experience to the growth of our organization.</p>
                
                <p>As we discussed, your <strong>Starting date</strong> will be on <strong>{{ start_date }}</strong>. Your <strong>Starting Salary</strong> will be <strong>Rs. {{ starting_salary }}</strong>. Please find the employee handbook enclosed here which contains the medical and retirement benefits offered by our organization.</p>
                
                <p>Please confirm your acceptance of this offer by signing and returning a copy of this offer letter.</p>
                
                <p>We are excited to welcome you on board.</p>
                
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
        
        # Salary Increment Template
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
                <p>To: <strong>{{ employee_name }}</strong> <strong>{{ employee_designation }}</strong></p>
                <p>Subject: Salary Increment Notification</p>
                
                <p>Dear <strong>{{ employee_name }}</strong>,</p>
                
                <p>We are pleased to inform you that in recognition of your exceptional performance and dedication, your salary has been increased.</p>
                
                <p>Your previous salary was <strong>{{ previous_salary }}</strong> and your salary has been increased by <strong>{{ increment_percentage }}%</strong>. Your new annual salary will be <strong>{{ new_salary }}</strong>, effective from <strong>{{ effective_date }}</strong>.</p>
                
                <p>We appreciate your hard work and look forward to your continued contributions to our organization.</p>
                
                <div class="signature">
                    <p>Best regards,</p>
                    <p>Manager<br>Disha Online SOLUTION</p>
                </div>
            </div>
            
            <div class="footer">
                <p><strong>{{ employee_name }}</strong> <strong>{{ employee_designation }}</strong> <strong>Disha Online SOLUTION</strong></p>
            </div>
        </body>
        </html>
        """
        
        # Professional Salary Slip Template
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
                    height: 6px;
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
        
        # Create templates
        templates_data = [
            {
                'name': 'Default Offer Letter',
                'document_type': 'offer_letter',
                'template_content': offer_letter_template
            },
            {
                'name': 'Default Salary Increment Letter',
                'document_type': 'salary_increment',
                'template_content': salary_increment_template
            },
            {
                'name': 'Default Salary Slip',
                'document_type': 'salary_slip',
                'template_content': salary_slip_template
            }
        ]
        
        created_count = 0
        for template_data in templates_data:
            template, created = DocumentTemplate.objects.get_or_create(
                name=template_data['name'],
                document_type=template_data['document_type'],
                defaults={
                    'template_content': template_data['template_content'],
                    'is_active': True,
                    'created_by': admin_user
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created template: {template.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Template already exists: {template.name}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} document templates')
        )
