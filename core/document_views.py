from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status, viewsets, permissions
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.template import Template, Context
from django.http import HttpResponse, JsonResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.core.mail import send_mail
from django.conf import settings
import logging
from datetime import datetime, date
from django.utils.dateparse import parse_date
# WeasyPrint availability will be checked when needed by check_weasyprint_availability()
# Do not import at module level to avoid startup crashes if missing
WEASYPRINT_AVAILABLE = None
PDF_CONSTRUCTOR_ARGS = None

from io import BytesIO

def check_weasyprint_availability():
    """Check if WeasyPrint is available and return status"""
    global WEASYPRINT_AVAILABLE, PDF_CONSTRUCTOR_ARGS
    
    if WEASYPRINT_AVAILABLE is not None:
        return WEASYPRINT_AVAILABLE
    
    try:
        import weasyprint
        import pydyf
        WEASYPRINT_AVAILABLE = True
        logger = logging.getLogger(__name__)
        logger.info(f"WeasyPrint is available for PDF generation - Version: {weasyprint.__version__}")
        logger.info(f"pydyf version: {pydyf.__version__}")
        
        # Test if pydyf.PDF constructor is compatible
        try:
            # Test the PDF constructor with different argument counts
            test_pdf = pydyf.PDF()
            logger.info("pydyf.PDF() constructor test: SUCCESS (0 args)")
            PDF_CONSTRUCTOR_ARGS = 0
        except TypeError as e:
            try:
                test_pdf = pydyf.PDF('1.7')
                logger.info("pydyf.PDF() constructor test: SUCCESS (1 arg)")
                PDF_CONSTRUCTOR_ARGS = 1
            except TypeError as e2:
                try:
                    test_pdf = pydyf.PDF('1.7', 'test')
                    logger.info("pydyf.PDF() constructor test: SUCCESS (2 args)")
                    PDF_CONSTRUCTOR_ARGS = 2
                except TypeError as e3:
                    logger.error(f"pydyf.PDF() constructor test: FAILED - {e3}")
                    PDF_CONSTRUCTOR_ARGS = -1
                    WEASYPRINT_AVAILABLE = False
                    
    except (ImportError, OSError) as e:
        WEASYPRINT_AVAILABLE = False
        PDF_CONSTRUCTOR_ARGS = -1
        logger = logging.getLogger(__name__)
        logger.error(f"WeasyPrint not available: {e}. PDF generation will be disabled.")
    
    return WEASYPRINT_AVAILABLE

from .models import (
    CustomUser, DocumentTemplate, GeneratedDocument, Office
)
from .serializers import (
    DocumentTemplateSerializer, GeneratedDocumentSerializer, DocumentGenerationSerializer
)

logger = logging.getLogger(__name__)


class DocumentTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet for managing document templates"""
    queryset = DocumentTemplate.objects.all()
    serializer_class = DocumentTemplateSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['document_type', 'is_active', 'created_by']
    search_fields = ['name', 'document_type']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['name']
    
    def get_queryset(self):
        # Only admins and managers can access templates
        if self.request.user.role in ['admin', 'manager']:
            return DocumentTemplate.objects.all()
        return DocumentTemplate.objects.none()
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class GeneratedDocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for managing generated documents"""
    queryset = GeneratedDocument.objects.all()
    serializer_class = GeneratedDocumentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['document_type', 'is_sent', 'generated_at']
    search_fields = ['title', 'employee__first_name', 'employee__last_name', 'employee__username', 'employee__employee_id']
    ordering_fields = ['generated_at', 'is_sent', 'title']
    ordering = ['-generated_at']
    
    def get_queryset(self):
        user = self.request.user
        queryset = GeneratedDocument.objects.none()
        
        if user.role == 'admin':
            queryset = GeneratedDocument.objects.all()
        elif user.role == 'manager':
            # Managers can see documents for their office employees
            queryset = GeneratedDocument.objects.filter(
                employee__office=user.office
            )
        else:
            # Employees and accountants can only see their own documents
            queryset = GeneratedDocument.objects.filter(employee=user)
            
        # Apply Office filter if provided (mainly for admins)
        office_id = self.request.query_params.get('office')
        if office_id and office_id != 'all':
            queryset = queryset.filter(employee__office__id=office_id)
            
        return queryset
    
    @action(detail=True, methods=['get'])
    def download_pdf(self, request, pk=None):
        """Download PDF version of the document"""
        document = self.get_object()
        logger.info(f"Download PDF request for document {document.id}: {document.title}")
        
        # Debug: Check document state
        logger.info(f"Document PDF file field: {document.pdf_file}")
        if document.pdf_file:
            logger.info(f"PDF file name: {document.pdf_file.name}")
            logger.info(f"PDF file size: {document.pdf_file.size}")
            logger.info(f"PDF file URL: {document.pdf_file.url}")
        
        # Debug: Check MEDIA_ROOT setting
        from django.conf import settings
        logger.info(f"MEDIA_ROOT: {settings.MEDIA_ROOT}")
        logger.info(f"MEDIA_URL: {settings.MEDIA_URL}")
        
        # Check if PDF file exists and is valid
        if document.pdf_file and document.pdf_file.size > 0:
            try:
                import os
                logger.info(f"PDF file exists in database: {document.pdf_file.name}, size: {document.pdf_file.size}")
                logger.info(f"PDF file path: {document.pdf_file.path}")
                # Check if the file actually exists on disk
                if os.path.exists(document.pdf_file.path):
                    filename = self.generate_document_filename(document)
                    logger.info(f"Reading PDF file content...")
                    
                    # Check file permissions
                    import stat
                    file_stat = os.stat(document.pdf_file.path)
                    logger.info(f"File permissions: {stat.filemode(file_stat.st_mode)}")
                    logger.info(f"File size on disk: {file_stat.st_size} bytes")
                    
                    pdf_content = document.pdf_file.read()
                    logger.info(f"PDF content size: {len(pdf_content)} bytes")
                    logger.info(f"PDF content starts with: {pdf_content[:10]}")
                    
                    # Verify it's actually a PDF by checking the header
                    if pdf_content.startswith(b'%PDF'):
                        response = HttpResponse(pdf_content, content_type='application/pdf')
                        response['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
                        response['Content-Length'] = len(pdf_content)
                        return response
                    else:
                        logger.warning(f"PDF file for document {document.id} is corrupted, regenerating...")
                else:
                    logger.warning(f"PDF file for document {document.id} does not exist on disk: {document.pdf_file.path}")
                    logger.warning(f"Cleaning up orphaned files and regenerating...")
                    self.cleanup_orphaned_files(document)
            except Exception as e:
                logger.error(f"Error reading existing PDF file for document {document.id}: {e}")
                import traceback
                logger.error(f"PDF file read error traceback: {traceback.format_exc()}")
                # Try to clean up orphaned files
                self.cleanup_orphaned_files(document)
                # Return error response instead of continuing
                return JsonResponse({
                    'error': 'PDF file read error',
                    'detail': str(e),
                    'traceback': traceback.format_exc()
                }, status=500)
        
        # If no valid PDF file, generate one on-demand (works on VPS hosting)
        if WEASYPRINT_AVAILABLE:
            try:
                if WEASYPRINT_AVAILABLE is None:
                    check_weasyprint_availability()
                
                if not WEASYPRINT_AVAILABLE:
                     logger.error("WeasyPrint became unavailable during PDF generation request")
                     raise Exception("WeasyPrint library is not available")

                import weasyprint  # Import here to avoid NameError
                
                logger.info(f"Generating PDF for document {document.id}")
                logger.info(f"Using WeasyPrint version: {weasyprint.__version__}")
                
                # Generate proper filename
                filename = self.generate_document_filename(document)
                
                # Get company logo path and information
                logo_path = ""
                company_name = "Your Company Name"
                company_address = "Company Address, City, State, ZIP"
                
                try:
                    import os
                    from django.conf import settings
                    
                    # Try different logo locations
                    logo_locations = [
                        os.path.join(settings.MEDIA_ROOT, 'documents', 'companylogo.png'),
                        os.path.join(settings.MEDIA_ROOT, 'companylogo.png'),
                        os.path.join(settings.MEDIA_ROOT, 'logo.png'),
                        os.path.join(settings.STATIC_ROOT, 'images', 'logo.png') if hasattr(settings, 'STATIC_ROOT') else None
                    ]
                    
                    for logo_file in logo_locations:
                        if logo_file and os.path.exists(logo_file):
                            logo_path = f"file://{logo_file}"
                            logger.info(f"Company logo found: {logo_path}")
                            break
                    
                    if not logo_path:
                        logger.warning("Company logo not found, using text header")
                    
                    # Get company information from settings or use defaults
                    company_name = getattr(settings, 'COMPANY_NAME', 'Your Company Name')
                    company_address = getattr(settings, 'COMPANY_ADDRESS', 'Company Address, City, State, ZIP')
                    company_phone = getattr(settings, 'COMPANY_PHONE', '+1 (555) 123-4567')
                    company_email = getattr(settings, 'COMPANY_EMAIL', 'conatact.dishaonliesolution@gmail.com')
                    company_website = getattr(settings, 'COMPANY_WEBSITE', 'https://dishaonliesolution.in')
                    
                except Exception as e:
                    logger.warning(f"Could not load company information: {e}")
                
                # Get employee ID from user
                employee_id = document.user.employee_id if document.user.employee_id else str(document.user.id)[:8].upper()
                
                # Enhance the document content with professional, compact CSS for A4 printing
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <title>{document.title}</title>
                    <style>
                        @page {{
                            margin: 0.4in;
                            size: A4;
                        }}
                        
                        * {{
                            box-sizing: border-box;
                        }}
                        
                        body {{
                            font-family: 'Arial', 'Helvetica', sans-serif;
                            font-size: 10pt;
                            line-height: 1.2;
                            color: #000000;
                            margin: 0;
                            padding: 0;
                            background: white;
                        }}
                        
                        .document-container {{
                            max-width: 100%;
                            margin: 0 auto;
                        }}
                        
                        .header {{
                            text-align: center;
                            margin-bottom: 15px;
                            border-bottom: 1px solid #000;
                            padding-bottom: 10px;
                        }}
                        
                        .company-logo {{
                            max-height: 50px;
                            max-width: 150px;
                            margin-bottom: 8px;
                        }}
                        
                        .company-name {{
                            font-size: 14pt;
                            font-weight: bold;
                            color: #000000;
                            margin: 3px 0;
                            text-transform: uppercase;
                            letter-spacing: 1px;
                        }}
                        
                        .company-address {{
                            font-size: 8pt;
                            color: #000000;
                            margin: 2px 0;
                            line-height: 1.1;
                        }}
                        
                        .company-contact {{
                            font-size: 7pt;
                            color: #000000;
                            margin: 2px 0;
                        }}
                        
                        .document-title {{
                            font-size: 12pt;
                            font-weight: bold;
                            color: #000000;
                            text-align: center;
                            margin: 8px 0 5px 0;
                            text-transform: uppercase;
                            letter-spacing: 1px;
                        }}
                        
                        .employee-header {{
                            display: flex;
                            justify-content: space-between;
                            margin: 5px 0;
                            font-size: 9pt;
                            border-bottom: 1px solid #000;
                            padding-bottom: 8px;
                        }}
                        
                        .employee-id {{
                            font-weight: bold;
                            color: #000000;
                        }}
                        
                        .document-date {{
                            color: #000000;
                        }}
                        
                        h1, h2, h3, h4, h5, h6 {{
                            color: #000000;
                            margin-top: 10px;
                            margin-bottom: 5px;
                            page-break-after: avoid;
                        }}
                        
                        h1 {{
                            font-size: 12pt;
                            font-weight: bold;
                        }}
                        
                        h2 {{
                            font-size: 11pt;
                            font-weight: bold;
                        }}
                        
                        h3 {{
                            font-size: 10pt;
                            font-weight: bold;
                        }}
                        
                        p {{
                            margin: 4px 0;
                            text-align: justify;
                            font-size: 9pt;
                            line-height: 1.2;
                        }}
                        
                        .content {{
                            margin: 10px 0;
                        }}
                        
                        .footer {{
                            margin-top: 20px;
                            padding-top: 8px;
                            border-top: 1px solid #000;
                            font-size: 7pt;
                            color: #000000;
                            text-align: center;
                        }}
                        
                        table {{
                            width: 100%;
                            border-collapse: collapse;
                            margin: 8px 0;
                            font-size: 9pt;
                            border: 1px solid #000;
                        }}
                        
                        th, td {{
                            border: 1px solid #000;
                            padding: 4px 6px;
                            text-align: left;
                            vertical-align: top;
                        }}
                        
                        th {{
                            background-color: #f0f0f0;
                            font-weight: bold;
                            font-size: 9pt;
                            color: #000000;
                        }}
                        
                        .salary-table {{
                            margin: 5px 0;
                        }}
                        
                        .salary-table th {{
                            background-color: #e0e0e0;
                            text-align: center;
                            font-weight: bold;
                        }}
                        
                        .salary-table td {{
                            text-align: right;
                        }}
                        
                        .salary-table .label {{
                            text-align: left;
                            font-weight: bold;
                        }}
                        
                        .signature-section {{
                            margin-top: 20px;
                            page-break-inside: avoid;
                        }}
                        
                        .signature-line {{
                            border-bottom: 1px solid #000;
                            width: 150px;
                            margin: 10px 0 3px 0;
                        }}
                        
                        .employee-info {{
                            display: flex;
                            justify-content: space-between;
                            margin: 8px 0;
                            font-size: 9pt;
                        }}
                        
                        .employee-info div {{
                            flex: 1;
                            margin: 0 5px;
                        }}
                        
                        .date-info {{
                            text-align: right;
                            font-size: 8pt;
                            color: #000000;
                            margin: 5px 0;
                        }}
                        
                        /* Compact spacing for A4 */
                        .compact {{
                            margin: 3px 0;
                        }}
                        
                        .compact p {{
                            margin: 2px 0;
                        }}
                        
                        .text-center {{
                            text-align: center;
                        }}
                        
                        .text-right {{
                            text-align: right;
                        }}
                        
                        .text-bold {{
                            font-weight: bold;
                        }}
                        
                        .mt-10 {{
                            margin-top: 10px;
                        }}
                        
                        .mb-5 {{
                            margin-bottom: 5px;
                        }}
                        
                        @media print {{
                            body {{ margin: 0; }}
                            .no-print {{ display: none; }}
                            @page {{ margin: 0.4in; }}
                        }}
                    </style>
                </head>
                <body>
                    <div class="document-container">
                        <div class="header">
                            {f'<img src="{logo_path}" alt="Company Logo" class="company-logo">' if logo_path else ''}
                            <div class="company-name">{company_name}</div>
                            <div class="company-address">{company_address}</div>
                            <div class="company-contact">
                                Phone: {company_phone} | Email: {company_email} | Website: {company_website}
                            </div>
                        </div>
                        
                        <div class="document-title">{document.title}</div>
                        
                        <div class="employee-header">
                            <div class="employee-id">Employee ID: {employee_id}</div>
                            <div class="document-date">Date: {document.generated_at.strftime('%B %d, %Y') if hasattr(document, 'generated_at') and document.generated_at else 'N/A'}</div>
                        </div>
                        
                        <div class="content compact">
                            {document.content}
                        </div>
                        
                        <div class="footer">
                            <p>This document was generated on {document.generated_at.strftime('%B %d, %Y at %I:%M %p') if hasattr(document, 'generated_at') and document.generated_at else 'N/A'}</p>
                            <p>Employee Management System</p>
                        </div>
                    </div>
                </body>
                </html>
                """
                
                # Use WeasyPrint to generate PDF with high quality settings
                pdf_buffer = BytesIO()
                
                # Create WeasyPrint HTML object with better configuration
                # Import HTML class locally
                from weasyprint import HTML
                html_doc = HTML(string=html_content)
                
                # Generate PDF with version-compatible settings
                try:
                    # Try with newer WeasyPrint parameters first
                    html_doc.write_pdf(
                        pdf_buffer,
                        stylesheets=None,  # We're using inline styles
                        optimize_images=True
                    )
                except TypeError as e:
                    if "PDF.__init__()" in str(e):
                        logger.warning(f"WeasyPrint version compatibility issue: {e}")
                        # Fallback to basic PDF generation without advanced options
                        pdf_buffer = BytesIO()  # Reset buffer
                        html_doc.write_pdf(pdf_buffer)
                    else:
                        raise e
                except Exception as e:
                    logger.error(f"Unexpected error in PDF generation: {e}")
                    # Try basic PDF generation as last resort
                    pdf_buffer = BytesIO()  # Reset buffer
                    html_doc.write_pdf(pdf_buffer)
                pdf_buffer.seek(0)
                pdf_content = pdf_buffer.getvalue()
                
                # Verify the generated PDF
                if pdf_content.startswith(b'%PDF') and len(pdf_content) > 100:
                    # Save PDF file for future use
                    try:
                        import os
                        from django.conf import settings
                        
                        # Ensure the directory exists
                        pdf_dir = os.path.join(settings.MEDIA_ROOT, 'generated_documents')
                        os.makedirs(pdf_dir, exist_ok=True)
                        
                        document.pdf_file.save(f"{filename}.pdf", BytesIO(pdf_content), save=True)
                        logger.info(f"PDF file saved successfully: {document.pdf_file.path}")
                    except Exception as save_error:
                        logger.warning(f"Could not save PDF file: {save_error}")
                        import traceback
                        logger.warning(f"PDF save error traceback: {traceback.format_exc()}")
                        # Continue with download even if saving fails
                    
                    # Return the PDF response
                    response = HttpResponse(pdf_content, content_type='application/pdf')
                    response['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
                    response['Content-Length'] = len(pdf_content)
                    return response
                else:
                    logger.error(f"Generated PDF is invalid for document {document.id}")
                    raise Exception("Generated PDF is invalid")
                
            except Exception as e:
                logger.error(f"PDF generation failed for document {document.id}: {e}")
                import traceback
                logger.error(f"PDF generation traceback: {traceback.format_exc()}")
                return JsonResponse({
                    'error': 'PDF generation failed',
                    'detail': str(e),
                    'traceback': traceback.format_exc()
                }, status=500)
        else:
            logger.error("WeasyPrint not available - PDF generation failed")
            return JsonResponse({
                'error': 'PDF generation not available',
                'detail': 'WeasyPrint is not working. Please check server configuration.',
                'fallback_available': False
            }, status=503)
    

    def generate_html_content_for_document(self, document):
        """Generate HTML content for document download when PDF is not available"""
        try:
            # Get company logo path and information
            logo_path = ""
            company_name = "Your Company Name"
            company_address = "Company Address"
            company_phone = "+1 (555) 123-4567"
            company_email = "info@company.com"
            company_website = "www.company.com"
            
            try:
                from django.conf import settings
                logo_path = self.get_logo_url()
                
                # Get company information from settings or use defaults
                company_name = getattr(settings, 'COMPANY_NAME', 'DISHA ONLINE SOLUTIONS')
                company_address = getattr(settings, 'COMPANY_ADDRESS', 'Bhumiraj Costarica, 9th Floor Office No- 907, Plot No- 1 & 2, Sector 18, Sanpada, Navi Mumbai, Maharashtra 400705')
                company_phone = getattr(settings, 'COMPANY_PHONE', '+91 1234567890')
                company_email = getattr(settings, 'COMPANY_EMAIL', 'info@dosapi.attendance.dishaonliesolution.workspa.in')
                company_website = getattr(settings, 'COMPANY_WEBSITE', 'https://dosapi.attendance.dishaonliesolution.workspa.in')
                
            except Exception as e:
                logger.warning(f"Could not load company information: {e}")
            
            # Get employee ID from user
            employee_id = document.employee.employee_id if document.employee.employee_id else str(document.employee.id)[:8].upper()
            
            # Generate filename based on document type
            filename = self.generate_document_filename(document)
            
            # Enhance the document content with proper CSS for single-page layout
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>{document.title}</title>
                <style>
                    @page {{
                        margin: 0.4in;
                        size: A4;
                    }}
                    
                    * {{
                        box-sizing: border-box;
                    }}
                    
                    body {{
                        font-family: 'Arial', 'Helvetica', sans-serif;
                        font-size: 10pt;
                        line-height: 1.2;
                        color: #000000;
                        margin: 0;
                        padding: 0;
                        background: white;
                    }}
                    
                    .document-container {{
                        max-width: 100%;
                        margin: 0 auto;
                    }}
                    
                    .header {{
                        text-align: center;
                        margin-bottom: 15px;
                        border-bottom: 1px solid #000;
                        padding-bottom: 10px;
                    }}
                    
                    .company-logo {{
                        max-height: 50px;
                        max-width: 150px;
                        margin-bottom: 8px;
                    }}
                    
                    .company-name {{
                        font-size: 14pt;
                        font-weight: bold;
                        color: #000000;
                        margin: 3px 0;
                        text-transform: uppercase;
                        letter-spacing: 1px;
                    }}
                    
                    .company-address {{
                        font-size: 8pt;
                        color: #000000;
                        margin: 2px 0;
                        line-height: 1.1;
                    }}
                    
                    .company-contact {{
                        font-size: 7pt;
                        color: #000000;
                        margin: 2px 0;
                    }}
                    
                    .document-title {{
                        font-size: 12pt;
                        font-weight: bold;
                        color: #000000;
                        text-align: center;
                        margin: 15px 0 10px 0;
                        text-transform: uppercase;
                        letter-spacing: 1px;
                    }}
                    
                    .employee-header {{
                        display: flex;
                        justify-content: space-between;
                        margin: 10px 0;
                        font-size: 9pt;
                        border-bottom: 1px solid #000;
                        padding-bottom: 8px;
                    }}
                    
                    .employee-id {{
                        font-weight: bold;
                        color: #000000;
                    }}
                    
                    .document-date {{
                        color: #000000;
                    }}
                    
                    h1, h2, h3, h4, h5, h6 {{
                        color: #000000;
                        margin-top: 10px;
                        margin-bottom: 5px;
                        page-break-after: avoid;
                    }}
                    
                    h1 {{
                        font-size: 12pt;
                        font-weight: bold;
                    }}
                    
                    h2 {{
                        font-size: 11pt;
                        font-weight: bold;
                    }}
                    
                    h3 {{
                        font-size: 10pt;
                        font-weight: bold;
                    }}
                    
                    p {{
                        margin: 4px 0;
                        text-align: justify;
                        font-size: 9pt;
                        line-height: 1.2;
                    }}
                    
                    .content {{
                        margin: 10px 0;
                    }}
                    
                    .footer {{
                        margin-top: 20px;
                        padding-top: 8px;
                        border-top: 1px solid #000;
                        font-size: 7pt;
                        color: #000000;
                        text-align: center;
                    }}
                    
                    table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin: 8px 0;
                        font-size: 9pt;
                        border: 1px solid #000;
                    }}
                    
                    th, td {{
                        border: 1px solid #000;
                        padding: 4px 6px;
                        text-align: left;
                        vertical-align: top;
                    }}
                    
                    th {{
                        background-color: #f0f0f0;
                        font-weight: bold;
                        font-size: 9pt;
                        color: #000000;
                    }}
                    
                    .salary-table {{
                        margin: 10px 0;
                    }}
                    
                    .salary-table th {{
                        background-color: #e0e0e0;
                        text-align: center;
                        font-weight: bold;
                    }}
                    
                    .salary-table td {{
                        text-align: right;
                    }}
                    
                    .salary-table .label {{
                        text-align: left;
                        font-weight: bold;
                    }}
                    
                    .signature-section {{
                        margin-top: 20px;
                        page-break-inside: avoid;
                    }}
                    
                    .signature-line {{
                        border-bottom: 1px solid #000;
                        width: 150px;
                        margin: 10px 0 3px 0;
                    }}
                    
                    .employee-info {{
                        display: flex;
                        justify-content: space-between;
                        margin: 8px 0;
                        font-size: 9pt;
                    }}
                    
                    .employee-info div {{
                        flex: 1;
                        margin: 0 5px;
                    }}
                    
                    .date-info {{
                        text-align: right;
                        font-size: 8pt;
                        color: #000000;
                        margin: 5px 0;
                    }}
                    
                    /* Compact spacing for A4 */
                    .compact {{
                        margin: 3px 0;
                    }}
                    
                    .compact p {{
                        margin: 2px 0;
                    }}
                    
                    .text-center {{
                        text-align: center;
                    }}
                    
                    .text-right {{
                        text-align: right;
                    }}
                    
                    .text-bold {{
                        font-weight: bold;
                    }}
                    
                    .mt-10 {{
                        margin-top: 10px;
                    }}
                    
                    .mb-5 {{
                        margin-bottom: 5px;
                    }}
                    
                    @media print {{
                        body {{ margin: 0; }}
                        .no-print {{ display: none; }}
                        @page {{ margin: 0.75in; }}
                    }}
                </style>
            </head>
            <body>
                <div class="document-container">
                    <div class="header">
                        {f'<img src="{logo_path}" alt="Company Logo" class="company-logo">' if logo_path else ''}
                        <div class="company-name">{company_name}</div>
                        <div class="company-address">{company_address}</div>
                        <div class="company-contact">
                            Phone: {company_phone} | Email: {company_email} | Website: {company_website}
                        </div>
                    </div>
                    
                    <div class="document-title">{document.title}</div>
                    
                    <div class="employee-header">
                        <div class="employee-id">Employee ID: {employee_id}</div>
                        <div class="document-date">Date: {document.generated_at.strftime('%B %d, %Y') if hasattr(document, 'generated_at') and document.generated_at else 'N/A'}</div>
                    </div>
                    
                    <div class="content compact">
                        {document.content}
                    </div>
                    
                    <div class="footer">
                        <p>This document was generated on {document.generated_at.strftime('%B %d, %Y at %I:%M %p') if hasattr(document, 'generated_at') and document.generated_at else 'N/A'}</p>
                        <p>Employee Management System</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return html_content
            
        except Exception as e:
            logger.error(f"Error generating HTML content: {e}")
            # Return basic HTML as fallback
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>{document.title}</title>
            </head>
            <body>
                <h1>{document.title}</h1>
                <div>{document.content}</div>
            </body>
            </html>
            """

    def cleanup_orphaned_files(self, document):
        """Clean up orphaned file references"""
        try:
            if document.pdf_file and document.pdf_file.name:
                import os
                from django.conf import settings
                
                file_path = os.path.join(settings.MEDIA_ROOT, document.pdf_file.name)
                if not os.path.exists(file_path):
                    logger.warning(f"Cleaning up orphaned file reference for document {document.id}")
                    document.pdf_file = None
                    document.save(update_fields=['pdf_file'])
                    return True
        except Exception as e:
            logger.error(f"Error cleaning up orphaned files for document {document.id}: {e}")
        return False
    
    def generate_document_filename(self, document):
        """Generate a proper filename for the document"""
        from datetime import datetime
        import re
        
        # Get employee first name
        employee_name = document.employee.first_name.lower() if document.employee.first_name else "employee"
        
        # Try to get month and year from document data
        month_name = None
        year = None
        
        if document.document_type == 'salary_slip' and document.salary_data:
            try:
                salary_data = document.salary_data
                if isinstance(salary_data, str):
                    import json
                    salary_data = json.loads(salary_data)
                
                month_name = salary_data.get('salary_month', '').lower()
                year = salary_data.get('salary_year', '')
            except:
                pass
        
        # Fallback to current date if no specific data available
        if not month_name or not year:
            current_date = datetime.now()
            month_name = current_date.strftime("%B").lower()  # e.g., "august"
            year = current_date.year
        
        # Generate filename based on document type
        if document.document_type == 'salary_slip':
            filename = f"{employee_name}_{month_name}_salaryslip_{year}"
        elif document.document_type == 'offer_letter':
            filename = f"{employee_name}_{month_name}_offerletter_{year}"
        elif document.document_type == 'salary_increment':
            filename = f"{employee_name}_{month_name}_salaryincrement_{year}"
        else:
            filename = f"{employee_name}_{month_name}_{document.document_type}_{year}"
        
        # Clean filename to be filesystem-safe
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = re.sub(r'\s+', '_', filename)  # Replace spaces with underscores
        filename = filename.strip('_')  # Remove leading/trailing underscores
        
        return filename
    
    @action(detail=True, methods=['post'])
    def send_email(self, request, pk=None):
        """Send document via email to employee"""
        document = self.get_object()
        
        try:
            # Send email to employee
            subject = f"{document.title} - {document.employee.get_full_name()}"
            message = f"""
Dear {document.employee.get_full_name()},

Please find attached your {document.get_document_type_display()}.

Best regards,
{request.user.get_full_name()}
{request.user.office.name if request.user.office else 'Disha Online Solutions'}
            """
            
            # For now, we'll just mark as sent (email configuration needed)
            document.is_sent = True
            document.sent_at = timezone.now()
            document.save()
            
            return Response({
                'message': 'Document sent successfully',
                'sent_at': document.sent_at
            })
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return Response(
                {'error': 'Failed to send email'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DocumentGenerationViewSet(viewsets.ViewSet):
    """ViewSet for generating documents"""
    permission_classes = [IsAuthenticated]

    def get_offer_letter_template(self):
        """Professional offer letter template from external file"""
        import os
        from django.conf import settings
        
        template_path = os.path.join(settings.BASE_DIR, 'core', 'Templates', 'offerlettter.html')
        try:
            with open(template_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            logger.error(f"Error reading offer letter template: {e}")
            return "<html><body><h1>Error loading template</h1></body></html>"
    

    def get_salary_increment_template(self):
        """Professional salary increment template from external file"""
        import os
        from django.conf import settings
        
        template_path = os.path.join(settings.BASE_DIR, 'core', 'Templates', 'salary_increment.html')
        try:
            with open(template_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            logger.error(f"Error reading salary increment template: {e}")
            return "<html><body><h1>Error loading template</h1></body></html>"

      



    def format_currency(self, amount):
        """Format currency in Indian format with proper word representation"""
        if amount is None:
            return "Not specified"
        
        # Convert to integer for formatting
        try:
            amount_int = int(float(amount))
        except (ValueError, TypeError):
            # If conversion fails, return as is or 0
            return str(amount) if amount is not None else "0"
        
        # Format with commas
        formatted = f"{amount_int:,}"
        
        # Convert to proper words
        words = self.number_to_words(amount_int)
        return f"Rs. {formatted} ({words})"

    def get_salary_slip_template(self):
        """Professional salary slip template from external file"""
        import os
        from django.conf import settings
        
        template_path = os.path.join(settings.BASE_DIR, 'core', 'Templates', 'salary_slip.html')
        try:
            with open(template_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            logger.error(f"Error reading salary slip template: {e}")
            # Fallback to a basic template or raise error
            return "<html><body><h1>Error loading template</h1></body></html>"



    def number_to_words(self, num):
        """Convert number to words in Indian format"""
        if num == 0:
            return "Zero"
        
        if num < 0:
            return "Minus " + self.number_to_words(abs(num))
        
        # Indian number system: Crore, Lakh, Thousand, Hundred
        crore = num // 10000000
        lakh = (num % 10000000) // 100000
        thousand = (num % 100000) // 1000
        hundred = (num % 1000) // 100
        tens = num % 100
        
        result = []
        
        # Crore
        if crore > 0:
            result.append(self.convert_three_digits(crore) + " Crore")
        
        # Lakh
        if lakh > 0:
            result.append(self.convert_three_digits(lakh) + " Lakh")
        
        # Thousand
        if thousand > 0:
            result.append(self.convert_three_digits(thousand) + " Thousand")
        
        # Hundred
        if hundred > 0:
            result.append(self.convert_three_digits(hundred) + " Hundred")
        
        # Tens and Ones
        if tens > 0:
            result.append(self.convert_tens_ones(tens))
        
        return " ".join(result)
    
    def convert_three_digits(self, num):
        """Convert 3-digit number to words"""
        if num == 0:
            return ""
        
        hundred = num // 100
        tens_ones = num % 100
        
        result = []
        
        if hundred > 0:
            result.append(self.ones[hundred] + " Hundred")
        
        if tens_ones > 0:
            result.append(self.convert_tens_ones(tens_ones))
        
        return " ".join(result)
    
    def convert_tens_ones(self, num):
        """Convert 2-digit number to words"""
        if num < 20:
            return self.ones[num]
        else:
            tens = num // 10
            ones = num % 10
            if ones == 0:
                return self.tens[tens]
            else:
                return self.tens[tens] + " " + self.ones[ones]
    
    @property
    def ones(self):
        return [
            "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
            "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
            "Seventeen", "Eighteen", "Nineteen"
        ]
    
    @property
    def tens(self):
        return [
            "", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"
        ]
    
    def get_logo_url(self):
        """Get the company logo URL"""
        from django.conf import settings
        import os
        
        # Check if logo file exists
        logo_path = os.path.join(settings.MEDIA_ROOT, 'documents', 'companylogo.png')
        if os.path.exists(logo_path):
            # Use production domain
            domain = "https://dosapi.attendance.dishaonliesolution.workspa.in"
            # Return absolute URL for the logo
            return f"{domain}{settings.MEDIA_URL}documents/companylogo.png"
        else:
            # Return a placeholder or default logo
            domain = "https://dosapi.attendance.dishaonliesolution.workspa.in"
            return f"{domain}{settings.MEDIA_URL}documents/companylogo.png"
    
    def generate_document_content(self, employee, document_type, data):
        """Generate document content using template"""
        
        if document_type == 'offer_letter':
            template_content = self.get_offer_letter_template()
            
            # Format start date
            start_date_str = data.get('start_date', '')
            if start_date_str:
                try:
                    start_date_obj = parse_date(start_date_str)
                    if start_date_obj:
                        start_date_formatted = start_date_obj.strftime('%d-%m-%Y')
                    else:
                        start_date_formatted = start_date_str
                except:
                    start_date_formatted = start_date_str
            else:
                start_date_formatted = ''
            
            context = {
                'employee_name': employee.get_full_name(),
                'employee_id': employee.employee_id if employee.employee_id else str(employee.id)[:8].upper(),
                'position': data.get('position', ''),
                'start_date': start_date_formatted,
                'starting_salary': self.format_currency(data.get('starting_salary')),
                'current_date': datetime.now().strftime('%A, %d %B %Y'),
                'logo_url': self.get_logo_url(),
            }
            
        elif document_type == 'salary_increment':
            template_content = self.get_salary_increment_template()
            
            # Try to get increment record for auto-fetching data
            increment_record = None
            
            # Option 1: Use provided increment_id
            if 'increment_id' in data and data['increment_id']:
                from coreapp.models import SalaryIncrement
                try:
                    increment_record = SalaryIncrement.objects.get(
                        id=data['increment_id'],
                        employee=employee
                    )
                    logger.info(f"Found increment record by ID: {increment_record.id}")
                except SalaryIncrement.DoesNotExist:
                    logger.warning(f"Increment record not found for ID: {data['increment_id']}")
            
            # Option 2: Get latest approved increment if no increment_id provided
            if not increment_record:
                from coreapp.models import SalaryIncrement
                increment_record = SalaryIncrement.objects.filter(
                    employee=employee,
                    status='approved'
                ).order_by('-effective_from').first()
                if increment_record:
                    logger.info(f"Using latest approved increment record: {increment_record.id}")
            
            # Use increment record data if available, otherwise fall back to manual data
            # Use increment record data if available, otherwise fall back to manual data
            if increment_record:
                previous_salary = float(increment_record.old_salary or 0)
                new_salary = float(increment_record.new_salary or 0)
                increment_amount = float(increment_record.increment_amount or 0)
                increment_percentage = float(increment_record.increment_percentage or 0)
                effective_date = increment_record.effective_from
                logger.info(f"Auto-fetched increment data: old={previous_salary}, new={new_salary}, amount={increment_amount}")
            else:
                # Fall back to manual data from request
                previous_salary = float(data.get('previous_salary', 0))
                new_salary = float(data.get('new_salary', 0))
                increment_amount = new_salary - previous_salary
                increment_percentage = ((new_salary - previous_salary) / previous_salary * 100) if previous_salary > 0 else 0
                effective_date = data.get('effective_date', '')
                logger.info(f"Using manual increment data: old={previous_salary}, new={new_salary}, amount={increment_amount}")
            
            # Format effective date
            if effective_date:
                try:
                    if isinstance(effective_date, str):
                        effective_date_obj = parse_date(effective_date)
                    else:
                        effective_date_obj = effective_date
                    
                    if effective_date_obj:
                        effective_date_formatted = effective_date_obj.strftime('%d-%m-%Y')
                    else:
                        effective_date_formatted = str(effective_date)
                except:
                    effective_date_formatted = str(effective_date)
            else:
                effective_date_formatted = ''
            
            context = {
                'employee_name': employee.get_full_name(),
                'employee_id': employee.employee_id if employee.employee_id else str(employee.id)[:8].upper(),
                'employee_designation': employee.designation or 'Employee',
                'previous_salary': self.format_currency(previous_salary),
                'new_salary': self.format_currency(new_salary),
                'increment_amount': self.format_currency(increment_amount),
                'increment_percentage': f"{increment_percentage:.0f}%",
                'effective_date': effective_date_formatted,
                'logo_url': self.get_logo_url(),
            }
        
        elif document_type == 'salary_slip':
            template_content = self.get_salary_slip_template()
            
            # Check if salary_id is provided for auto-fetching from DB
            salary_id = data.get('salary_id')
            salary_record = None
            
            if salary_id:
                from .models import Salary
                try:
                    salary_record = Salary.objects.select_related(
                        'employee', 'employee__office', 'employee__department', 'employee__designation'
                    ).get(id=salary_id)
                    logger.info(f"Auto-fetched salary record by ID: {salary_record.id}")
                except Salary.DoesNotExist:
                    logger.warning(f"Salary record not found for ID: {salary_id}, falling back to manual data")
            
            if salary_record:
                # === AUTO-FETCH from database (fast path) ===
                emp = salary_record.employee
                basic_salary = float(salary_record.basic_pay or 0)
                per_day_pay = float(salary_record.per_day_pay or 0)
                worked_days = float(salary_record.worked_days or 0)
                total_days = salary_record.total_days or 30
                gross_salary = float(salary_record.gross_salary or 0)
                net_salary = float(salary_record.net_salary or 0)
                total_gross_salary = gross_salary
                total_salary = net_salary
                extra_days_pay = max(0, (worked_days - total_days)) * per_day_pay
                absent_days = total_days - int(worked_days)
                total_deductions = float(salary_record.deduction or 0) + float(salary_record.balance_loan or 0)
                final_salary = float(salary_record.final_salary or 0)
                basic_pay = basic_salary
                
                # Format month/year from salary_month date
                months = ['January', 'February', 'March', 'April', 'May', 'June',
                          'July', 'August', 'September', 'October', 'November', 'December']
                salary_month = months[salary_record.salary_month.month - 1]
                salary_year = str(salary_record.salary_month.year)
                
                # Employee details from DB
                employee_name = emp.get_full_name()
                employee_id_display = emp.employee_id if emp.employee_id else str(emp.id)[:8].upper()
                employee_designation = getattr(emp.designation, 'name', 'Not specified') if emp.designation else 'Not specified'
                employee_department = getattr(emp.department, 'name', 'Not specified') if emp.department else 'Not specified'
                office_name = getattr(emp.office, 'name', 'Not specified') if emp.office else 'Not specified'
                
                # Bank details from employee
                bank_name = getattr(emp, 'bank_name', 'Not specified') or 'Not specified'
                account_number = getattr(emp, 'account_number', 'Not specified') or 'Not specified'
                ifsc_code = getattr(emp, 'ifsc_code', 'Not specified') or 'Not specified'
                
                # Other employee details
                address = getattr(emp, 'address', 'Not specified') or 'Not specified'
                pan_number = getattr(emp, 'pan_number', 'Not specified') or 'Not specified'
                aadhar_number = getattr(emp, 'aadhar_number', 'Not specified') or 'Not specified'
                uan_number = getattr(emp, 'uan_number', 'Not specified') or 'Not specified'
                esi_number = getattr(emp, 'esi_number', 'Not specified') or 'Not specified'
                pf_number = getattr(emp, 'pf_number', 'Not specified') or 'Not specified'
                
            else:
                # === FALLBACK: Get salary slip data from frontend (legacy path) ===
                basic_salary = float(data.get('basic_salary', 0))
                extra_days_pay = float(data.get('extra_days_pay', 0))
                total_gross_salary = float(data.get('total_gross_salary', 0))
                net_salary = float(data.get('net_salary', 0))
                total_salary = float(data.get('total_salary', 0))
                
                total_days = data.get('total_days', 0)
                worked_days = data.get('worked_days', 0)
                per_day_pay = float(data.get('per_day_pay', 0))
                gross_salary = float(data.get('gross_salary', 0))
                absent_days = data.get('absent_days', 0)
                total_deductions = float(data.get('total_deductions', 0))
                final_salary = float(data.get('final_salary', 0))
                basic_pay = float(data.get('basic_pay', 0))
                
                salary_month = data.get('salary_month', '')
                salary_year = data.get('salary_year', '')
                
                employee_name = (data.get('employee_name') or 
                               data.get('full_name') or 
                               employee.get_full_name())
                employee_id_display = (data.get('employee_id_number') or 
                                      data.get('employee_employee_id') or 
                                      data.get('employee_id') or 
                                      employee.employee_id if employee.employee_id else str(employee.id)[:8].upper())
                employee_designation = (data.get('employee_designation') or 
                                      data.get('designation') or 
                                      employee.designation or 'Not specified')
                employee_department = (data.get('employee_department') or 
                                     data.get('department') or 
                                     str(getattr(employee, 'department', 'Not specified')))
                office_name = (data.get('employee_office') or 
                             data.get('office_name') or 
                             getattr(employee.office, 'name', 'Not specified') if hasattr(employee, 'office') and employee.office else 'Not specified')
                
                bank_name = data.get('bank_name', getattr(employee, 'bank_name', 'Not specified'))
                account_number = data.get('account_number', getattr(employee, 'account_number', 'Not specified'))
                ifsc_code = data.get('ifsc_code', getattr(employee, 'ifsc_code', 'Not specified'))
                
                address = data.get('address', getattr(employee, 'address', 'Not specified'))
                pan_number = data.get('pan_number', getattr(employee, 'pan_number', 'Not specified'))
                aadhar_number = data.get('aadhar_number', getattr(employee, 'aadhar_number', 'Not specified'))
                uan_number = data.get('uan_number', getattr(employee, 'uan_number', 'Not specified'))
                esi_number = data.get('esi_number', getattr(employee, 'esi_number', 'Not specified'))
                pf_number = data.get('pf_number', getattr(employee, 'pf_number', 'Not specified'))
            
            
            context = {
                'employee_name': employee_name,
                'employee_id': employee_id_display,
                'employee_designation': employee_designation,
                'employee_department': employee_department,
                'office_name': office_name,
                'bank_name': bank_name,
                'account_number': ('X' * (len(str(account_number)) - 4) + str(account_number)[-4:]) if account_number and str(account_number) not in ['Not specified', ''] and len(str(account_number)) > 4 else account_number,
                'ifsc_code': ifsc_code,
                'address': address,
                'pan_number': pan_number,
                'aadhar_number': aadhar_number,
                'uan_number': uan_number,
                'esi_number': esi_number,
                'pf_number': pf_number,
                'salary_month': salary_month,
                'salary_year': salary_year,
                'basic_salary': self.format_currency(basic_salary),
                'extra_days_pay': self.format_currency(extra_days_pay),
                'total_salary': self.format_currency(total_salary),
                'net_salary': self.format_currency(net_salary),
                'total_gross_salary': self.format_currency(total_gross_salary),
                'gross_salary': self.format_currency(gross_salary),
                'per_day_pay': self.format_currency(per_day_pay),
                'basic_pay': self.format_currency(basic_pay),
                'final_salary': self.format_currency(final_salary),
                'total_deductions': self.format_currency(total_deductions),
                'total_days': total_days,
                'worked_days': worked_days,
                'absent_days': absent_days,
                'logo_url': self.get_logo_url(),
                'current_date': datetime.now().strftime('%d/%m/%Y'),
                'joining_date': (emp if salary_record else employee).joining_date.strftime('%d-%m-%Y') if (emp if salary_record else employee).joining_date else None,
            }
        
        else:
            raise ValueError(f"Unsupported document type: {document_type}")
        
        # Render template
        template = Template(template_content)
        rendered_content = template.render(Context(context))
        
        return rendered_content
    
    @action(detail=False, methods=['post'])
    def preview_document(self, request):
        """Preview a document before generation"""
        try:
            # Parse request data
            if hasattr(request, 'data'):
                data = request.data
            else:
                import json
                data = json.loads(request.body.decode('utf-8'))
            
            serializer = DocumentGenerationSerializer(data=data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            data = serializer.validated_data
            employee_id = data['employee_id']
            document_type = data['document_type']
            
            # Get employee
            employee = get_object_or_404(CustomUser, id=employee_id)
            
            # Check permissions
            user = request.user
            if user.role == 'manager' and employee.office != user.office:
                return Response(
                    {'error': 'You can only preview documents for employees in your office'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            elif user.role == 'employee':
                return Response(
                    {'error': 'Employees cannot preview documents'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Generate document content
            content = self.generate_document_content(employee, document_type, data)
            
            # Create title
            if document_type == 'offer_letter':
                title = f"Offer Letter - {employee.get_full_name()}"
            elif document_type == 'salary_increment':
                title = f"Salary Increment Letter - {employee.get_full_name()}"
            else:
                title = f"{document_type.replace('_', ' ').title()} - {employee.get_full_name()}"
            
            return Response({
                'title': title,
                'content': content,
                'employee_name': employee.get_full_name(),
                'employee_email': employee.email,
                'document_type': document_type,
                'preview_data': data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Document preview failed: {e}")
            return Response({'error': 'Failed to preview document'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def generate_document(self, request):
        """Generate a document for an employee"""
        # Parse request data
        if hasattr(request, 'data'):
            data = request.data
        else:
            import json
            data = json.loads(request.body.decode('utf-8'))
        
        serializer = DocumentGenerationSerializer(data=data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        employee_id = data['employee_id']
        document_type = data['document_type']
        
        # Get employee
        from .models import CustomUser
        employee = get_object_or_404(CustomUser, id=employee_id)
        
        # Check permissions
        user = request.user
        if user.role == 'manager' and employee.office != user.office:
            return Response(
                {'error': 'You can only generate documents for employees in your office'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        elif user.role == 'employee':
            return Response(
                {'error': 'Employees cannot generate documents'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # Generate document content
            content = self.generate_document_content(employee, document_type, data)
            
            # Create document title
            if document_type == 'offer_letter':
                title = f"Offer Letter - {employee.get_full_name()}"
            elif document_type == 'salary_increment':
                title = f"Salary Increment Letter - {employee.get_full_name()}"
            else:
                title = f"{document_type.replace('_', ' ').title()} - {employee.get_full_name()}"
            
            # Convert data to JSON-serializable format
            json_data = {}
            for key, value in data.items():
                if hasattr(value, 'isoformat'):  # datetime/date objects
                    json_data[key] = value.isoformat()
                elif hasattr(value, '__str__') and not isinstance(value, (str, int, float, bool, list, dict)):
                    json_data[key] = str(value)  # UUID and other objects
                else:
                    json_data[key] = value
            
            # Get or create default template
            template = DocumentTemplate.objects.filter(
                document_type=document_type,
                is_active=True
            ).first()
            
            if not template:
                # Create a default template if none exists
                if document_type == 'offer_letter':
                    template_content = self.get_offer_letter_template()
                elif document_type == 'salary_increment':
                    template_content = self.get_salary_increment_template()
                else:
                    template_content = "<html><body><h1>Document</h1></body></html>"
                
                template = DocumentTemplate.objects.create(
                    name=f"Default {document_type.replace('_', ' ').title()}",
                    document_type=document_type,
                    template_content=template_content,
                    is_active=True,
                    created_by=user
                )
            
            # Create generated document record
            generated_doc = GeneratedDocument.objects.create(
                employee=employee,
                template=template,
                document_type=document_type,
                title=title,
                content=content,
                generated_by=user,
                offer_data=json_data if document_type == 'offer_letter' else None,
                increment_data=json_data if document_type == 'salary_increment' else None,
                salary_data=json_data if document_type == 'salary_slip' else None,
            )
            
            # Generate file based on document type
            if check_weasyprint_availability():
                # Generate PDF for other document types
                try:
                    import weasyprint
                    from weasyprint import HTML
                    logger.info(f"Generating PDF for document {generated_doc.id}")
                    pdf_buffer = BytesIO()
                    HTML(string=content).write_pdf(pdf_buffer)
                    pdf_buffer.seek(0)
                    
                    # Save PDF file
                    filename = f"{title.replace(' ', '_')}_{generated_doc.id}.pdf"
                    generated_doc.pdf_file.save(filename, pdf_buffer, save=True)
                    logger.info(f"PDF file saved successfully: {filename}")
                    
                except Exception as e:
                    logger.warning(f"PDF generation failed (likely Windows dev environment): {e}")
                    # Continue without PDF - will work on VPS hosting
            else:
                logger.info("WeasyPrint not available on local development environment - will work on VPS hosting")
            
            # Send email if requested
            if data.get('send_email', True):
                try:
                    # Mark as sent (actual email sending would require email configuration)
                    generated_doc.is_sent = True
                    generated_doc.sent_at = timezone.now()
                    generated_doc.save()
                except Exception as e:
                    logger.warning(f"Email sending failed: {e}")
            
            # Notify Admins about document generation
            try:
                from .notification_service import NotificationService
                from .models import CustomUser
                
                admin_message = f"Document Generated:\nType: {document_type}\nTitle: {title}\nEmployee: {employee.get_full_name()}\nGenerated By: {user.get_full_name()}"
                
                admins = CustomUser.objects.filter(role='admin', is_active=True)
                for admin in admins:
                    NotificationService.create_notification(
                        user=admin,
                        title=f"Document Generated: {title}",
                        message=admin_message,
                        notification_type='document',
                        category='info',
                        priority='low',
                        created_by=user,
                        send_email=True  # Ensure admin gets an email
                    )
            except Exception as e:
                logger.error(f"Failed to notify admins about document generation: {e}")
            
            # Return generated document
            response_serializer = GeneratedDocumentSerializer(generated_doc)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Document generation failed: {e}")
            return Response(
                {'error': 'Failed to generate document'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    
    @action(detail=False, methods=['get'], url_path='employees')
    def get_employees(self, request):
        """Get list of employees for document generation"""
        
        user = request.user
        queryset = CustomUser.objects.select_related('office')
        
        if user.is_admin:
            queryset = queryset.all()
        elif user.is_manager:
            queryset = queryset.filter(office=user.office)
        else:
            queryset = queryset.filter(id=user.id)
        
        # Use the same serializer as CustomUserViewSet
        from .serializers import CustomUserSerializer
        serializer = CustomUserSerializer(queryset, many=True)
        
        return Response(serializer.data)



    @action(detail=False, methods=['get'])
    def get_employee_details(self, request):
        """Get detailed information for a specific employee"""
        user = request.user
        employee_id = request.query_params.get('employee_id')
        
        if not employee_id:
            return Response(
                {'error': 'employee_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            employee = get_object_or_404(CustomUser, id=employee_id)
            
            # Check permissions
            if user.role == 'employee' and employee != user:
                return Response(
                    {'error': 'Access denied'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            employee_data = {
                'id': employee.id,
                'employee_id': employee.employee_id if employee.employee_id else str(employee.id)[:8].upper(),
                'name': employee.get_full_name(),
                'first_name': employee.first_name,
                'last_name': employee.last_name,
                'email': employee.email,
                'designation': employee.designation,
                'department': employee.department,
                'office': employee.office.name if employee.office else None,
                'office_id': employee.office.id if employee.office else None,
                'current_salary': employee.salary,
                'joining_date': employee.joining_date.strftime('%Y-%m-%d') if employee.joining_date else None,
                'phone': employee.phone_number,
                'address': employee.address,
                'date_of_birth': employee.date_of_birth.strftime('%Y-%m-%d') if employee.date_of_birth else None,
                'bank_name': getattr(employee, 'bank_name', ''),
                'account_number': getattr(employee, 'account_number', ''),
                'pan_number': getattr(employee, 'pan_number', ''),
                'aadhar_number': getattr(employee, 'aadhar_number', ''),
                'emergency_contact': getattr(employee, 'emergency_contact', ''),
                'emergency_phone': getattr(employee, 'emergency_phone', ''),
                'is_active': employee.is_active,
                'created_at': employee.date_joined.strftime('%Y-%m-%d %H:%M:%S') if employee.date_joined else None
            }
            
            return Response(employee_data)
            
        except Exception as e:
            logger.error(f"Error fetching employee details: {e}")
            return Response(
                {'error': 'Failed to fetch employee details'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def my_documents(self, request):
        """Get current user's documents (for employees and accountants to view their own documents)"""
        user = request.user
        
        if user.role in ['employee', 'accountant']:
            # Employee and accountant can only see their own documents
            documents = GeneratedDocument.objects.filter(employee=user).order_by('-generated_at')
        elif user.role == 'manager':
            # Manager can see documents for employees in their office
            documents = GeneratedDocument.objects.filter(
                employee__office=user.office
            ).order_by('-generated_at')
        elif user.role == 'admin':
            # Admin can see all documents
            documents = GeneratedDocument.objects.all().order_by('-generated_at')
        else:
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = GeneratedDocumentSerializer(documents, many=True)
        return Response(serializer.data)
