import fitz
from PIL import Image, ImageDraw, ImageFont
import os

def make_pdf(filename, text):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(fitz.Point(50, 50), text, fontsize=12)
    doc.save(filename)
    doc.close()

def make_img(filename, text):
    img = Image.new('RGB', (800, 600), color = (255, 255, 255))
    d = ImageDraw.Draw(img)
    # Using default font, so we need to manually handle newlines or use multiline_text
    d.multiline_text((50,50), text, fill=(0,0,0))
    img.save(filename)

coi_compliant_text = """
CERTIFICATE OF LIABILITY INSURANCE
Insured: Acme Corp
Insurer: Global Insurance Co.
Policy Number: POL-12345
General Liability: $2,000,000
Workers Compensation: $1,000,000
Effective Date: 01-01-2026
Expiration Date: 01-01-2027
"""

coi_non_compliant_text = """
CERTIFICATE OF LIABILITY INSURANCE
Insured: Shady LLC
Insurer: Fast Insurance Inc.
Policy Number: POL-99999
General Liability: $500,000
Workers Compensation: $0
Effective Date: 01-01-2020
Expiration Date: 01-01-2021
"""

diversity_text = """
MINORITY BUSINESS ENTERPRISE CERTIFICATION
Company: Acme Corp
Certification Type: MBE
Certification Date: 01-01-2026
Expiration Date: 01-01-2028
Status: Active
"""

os.makedirs('test_documents', exist_ok=True)
make_pdf('test_documents/sample_coi_compliant.pdf', coi_compliant_text)
make_pdf('test_documents/sample_coi_expired.pdf', coi_non_compliant_text)
make_img('test_documents/sample_diversity_cert.png', diversity_text)

print("Test files generated in test_documents/ directory successfully!")
