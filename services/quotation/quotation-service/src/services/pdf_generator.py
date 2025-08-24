"""
PDF generator service for freight quotes.
"""
import logging
import io
from datetime import datetime
from typing import Optional
from decimal import Decimal

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
except ImportError:
    # Fallback if reportlab is not available
    SimpleDocTemplate = None

from shared.storage import storage, generate_object_path

logger = logging.getLogger(__name__)


class PDFGenerator:
    """PDF generator for freight quotes."""
    
    def __init__(self):
        self.company_name = "FreightPlatform"
        self.company_address = "123 Shipping Lane\nFreight City, FC 12345\nPhone: +1-555-FREIGHT"
        self.company_email = "quotes@freightplatform.com"
    
    def generate_quote_pdf(self, quote) -> Optional[str]:
        """
        Generate PDF for a quote and upload to object storage.
        
        Args:
            quote: Quote model instance
            
        Returns:
            Object path in storage or None if generation fails
        """
        if SimpleDocTemplate is None:
            logger.error("ReportLab not available for PDF generation")
            return None
        
        try:
            # Create PDF in memory
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18
            )
            
            # Build PDF content
            story = self._build_quote_content(quote)
            
            # Generate PDF
            doc.build(story)
            
            # Upload to storage
            buffer.seek(0)
            object_path = generate_object_path(
                'quotes',
                quote.quote_id,
                f'{quote.quote_id}.pdf'
            )
            
            storage_path = storage.upload_file(
                buffer,
                object_path,
                content_type='application/pdf',
                metadata={
                    'quote_id': quote.quote_id,
                    'customer_id': quote.customer_id or 'unknown',
                    'generated_at': datetime.utcnow().isoformat()
                }
            )
            
            if storage_path:
                logger.info(f"Generated PDF for quote {quote.quote_id}: {storage_path}")
                return object_path
            else:
                logger.error(f"Failed to upload PDF for quote {quote.quote_id}")
                return None
        
        except Exception as e:
            logger.error(f"Error generating PDF for quote {quote.quote_id}: {e}")
            return None
    
    def _build_quote_content(self, quote):
        """Build PDF content for quote."""
        story = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#1f4e79'),
            alignment=TA_CENTER
        )
        
        header_style = ParagraphStyle(
            'CustomHeader',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            textColor=colors.HexColor('#1f4e79')
        )
        
        # Company header
        story.append(Paragraph(self.company_name, title_style))
        story.append(Paragraph(self.company_address.replace('\n', '<br/>'), styles['Normal']))
        story.append(Paragraph(f"Email: {self.company_email}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Quote title
        story.append(Paragraph(f"FREIGHT QUOTE - {quote.quote_id}", title_style))
        story.append(Spacer(1, 20))
        
        # Quote details
        story.append(Paragraph("Quote Details", header_style))
        
        quote_details = [
            ['Quote ID:', quote.quote_id],
            ['Date:', quote.created_at.strftime('%B %d, %Y')],
            ['Valid Until:', quote.valid_until.strftime('%B %d, %Y')],
            ['Status:', quote.status],
            ['Customer ID:', quote.customer_id or 'N/A']
        ]
        
        quote_table = Table(quote_details, colWidths=[2*inch, 3*inch])
        quote_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(quote_table)
        story.append(Spacer(1, 20))
        
        # Shipment details
        story.append(Paragraph("Shipment Details", header_style))
        
        shipment_details = [
            ['Mode:', quote.mode],
            ['Service:', quote.service],
            ['Origin:', quote.origin],
            ['Destination:', quote.destination],
            ['Route:', quote.route_key]
        ]
        
        # Add cargo details
        cargo = quote.get_cargo_details()
        if cargo:
            if 'weightKg' in cargo:
                shipment_details.append(['Weight:', f"{cargo['weightKg']} kg"])
            if 'volumeM3' in cargo:
                shipment_details.append(['Volume:', f"{cargo['volumeM3']} m³"])
        
        # Add container details
        containers = quote.get_containers()
        if containers:
            container_desc = ', '.join([f"{c.get('count', 1)}x {c.get('type', 'Container')}" for c in containers])
            shipment_details.append(['Containers:', container_desc])
        
        shipment_table = Table(shipment_details, colWidths=[2*inch, 3*inch])
        shipment_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(shipment_table)
        story.append(Spacer(1, 20))
        
        # Pricing breakdown
        story.append(Paragraph("Pricing Breakdown", header_style))
        
        # Create pricing table
        pricing_data = [['Description', 'Quantity', 'Unit Price', 'Total']]
        
        # Add quote items
        for item in quote.items:
            pricing_data.append([
                item.description,
                str(item.quantity),
                f"{quote.currency} {item.unit_price:.2f}",
                f"{quote.currency} {item.total_price:.2f}"
            ])
        
        # Add totals
        pricing_data.append(['', '', 'Subtotal:', f"{quote.currency} {quote.base_amount:.2f}"])
        
        # Add surcharges
        surcharges = quote.get_surcharges()
        for surcharge in surcharges:
            pricing_data.append([
                '', '', 
                surcharge.get('description', surcharge.get('code', 'Surcharge')),
                f"{quote.currency} {surcharge['amount']:.2f}"
            ])
        
        pricing_data.append(['', '', 'TOTAL:', f"{quote.currency} {quote.total_amount:.2f}"])
        
        pricing_table = Table(pricing_data, colWidths=[3*inch, 1*inch, 1.5*inch, 1.5*inch])
        pricing_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4e79')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Data rows
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            
            # Total row
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f0f0f0')),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        story.append(pricing_table)
        story.append(Spacer(1, 30))
        
        # Terms and conditions
        story.append(Paragraph("Terms and Conditions", header_style))
        
        terms = [
            "1. This quote is valid until the date specified above.",
            "2. Prices are subject to change based on fuel surcharges and currency fluctuations.",
            "3. Additional charges may apply for special handling or documentation requirements.",
            "4. Payment terms: Net 30 days from invoice date.",
            "5. All shipments are subject to our standard terms and conditions of carriage."
        ]
        
        for term in terms:
            story.append(Paragraph(term, styles['Normal']))
            story.append(Spacer(1, 6))
        
        story.append(Spacer(1, 20))
        
        # Footer
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER
        )
        
        story.append(Paragraph(
            f"Generated on {datetime.utcnow().strftime('%B %d, %Y at %I:%M %p UTC')}",
            footer_style
        ))
        
        return story
    
    def generate_invoice_pdf(self, booking) -> Optional[str]:
        """
        Generate PDF invoice for a booking (placeholder for future implementation).
        
        Args:
            booking: Booking model instance
            
        Returns:
            Object path in storage or None if generation fails
        """
        # TODO: Implement invoice PDF generation
        logger.info(f"Invoice PDF generation not yet implemented for booking {booking.id}")
        return None

