from fpdf import FPDF
import os

# Output directory
output_dir = "./"

# 1. Portfolio PDF
portfolio_pdf = FPDF()
portfolio_pdf.add_page()
portfolio_pdf.set_font("Arial", size=12)
portfolio_pdf.cell(200, 10, txt="John Doe - Carpenter Portfolio", ln=True, align="C")
portfolio_pdf.ln(10)
portfolio_pdf.multi_cell(0, 10, txt="""
Projects:

1. Custom Kitchen Cabinetry - Designed and built cabinets for a modern kitchen using oak and walnut.
2. Residential Roofing Repair - Led a team to replace damaged trusses and install new shingles.
3. Pergola Construction - Designed and built a backyard pergola for a client in Nairobi.
4. Office Partitioning - Installed wood and glass partitions for a corporate office.

Tools Used:
- Circular Saw
- Jigsaw
- Power Drill
- Chisel Set
- Measuring Tape
- Level

Specializations:
- Joinery
- Roofing
- Framing
- Wood Finishing
""")
portfolio_path = os.path.join(output_dir, "Carpenter_Portfolio_John_Doe.pdf")
portfolio_pdf.output(portfolio_path)

# 2. Certificate/License PDF
cert_pdf = FPDF()
cert_pdf.add_page()
cert_pdf.set_font("Arial", "B", 16)
cert_pdf.cell(200, 10, txt="Certificate of Trade Proficiency", ln=True, align="C")
cert_pdf.ln(20)
cert_pdf.set_font("Arial", size=12)
cert_pdf.multi_cell(0, 10, txt="""
This is to certify that

John Doe

has successfully completed the Trade Proficiency Examination in

Carpentry and Joinery

Awarded on: March 15, 2023
Certificate No: 2023/CP/01234

Authorized by:
National Construction Authority of Kenya
""")
cert_path = os.path.join(output_dir, "Carpenter_Certificate_John_Doe.pdf")
cert_pdf.output(cert_path)

# 3. ID PDF
id_pdf = FPDF()
id_pdf.add_page()
id_pdf.set_font("Arial", "B", 14)
id_pdf.cell(200, 10, txt="Trade Identification Card", ln=True, align="C")
id_pdf.ln(15)
id_pdf.set_font("Arial", size=12)
id_pdf.cell(50, 10, txt="Name:", ln=0)
id_pdf.cell(100, 10, txt="John Doe", ln=1)
id_pdf.cell(50, 10, txt="Trade:", ln=0)
id_pdf.cell(100, 10, txt="Carpentry", ln=1)
id_pdf.cell(50, 10, txt="ID Number:", ln=0)
id_pdf.cell(100, 10, txt="12345678", ln=1)
id_pdf.cell(50, 10, txt="Issued Date:", ln=0)
id_pdf.cell(100, 10, txt="April 10, 2024", ln=1)
id_pdf.cell(50, 10, txt="Valid Until:", ln=0)
id_pdf.cell(100, 10, txt="April 10, 2029", ln=1)
id_pdf.ln(20)
id_pdf.cell(200, 10, txt="Authorized by: National Trade Licensing Bureau", ln=True)
id_path = os.path.join(output_dir, "Carpenter_ID_John_Doe.pdf")
id_pdf.output(id_path)

portfolio_path, cert_path, id_path
