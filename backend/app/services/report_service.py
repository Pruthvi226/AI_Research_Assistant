from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from typing import Dict, Any
import os

class ReportService:
    @staticmethod
    def generate_pdf_report(data: Dict[str, Any], output_path: str):
        c = canvas.Canvas(output_path, pagesize=letter)
        width, height = letter
        
        # Header
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, height - 100, f"Research Report: {data.get('title', 'Unknown')}")
        
        # content
        c.setFont("Helvetica", 12)
        y = height - 150
        
        c.drawString(100, y, "Abstract:")
        y -= 20
        c.setFont("Helvetica", 10)
        c.drawString(100, y, data.get("abstract", "No abstract available.")[:100] + "...")
        y -= 40
        
        c.setFont("Helvetica", 12)
        c.drawString(100, y, "Methodology:")
        y -= 20
        c.setFont("Helvetica", 10)
        c.drawString(100, y, data.get("methodology", "N/A"))
        y -= 40
        
        c.setFont("Helvetica", 12)
        c.drawString(100, y, "Conclusion:")
        y -= 20
        c.setFont("Helvetica", 10)
        c.drawString(100, y, data.get("conclusion", "N/A"))
        
        c.save()
        return output_path

report_service = ReportService()
