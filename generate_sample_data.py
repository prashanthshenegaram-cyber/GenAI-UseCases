from pathlib import Path


def main() -> None:
    root = Path(__file__).parent
    documents = root / "data/documents"
    documents.mkdir(parents=True, exist_ok=True)
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
        from reportlab.lib.styles import getSampleStyleSheet
        from PIL import Image as PILImage, ImageDraw
        chart = documents / "sales_chart.png"
        image = PILImage.new("RGB", (700, 420), "white")
        draw = ImageDraw.Draw(image)
        values = {"North": 3100, "South": 3700, "East": 3500, "West": 4200}
        draw.text((25, 20), "Q3 Sales", fill="black")
        for index, (region, value) in enumerate(values.items()):
            x = 90 + index * 140
            height = value // 12
            draw.rectangle((x, 370 - height, x + 70, 370), fill=(45, 105, 170))
            draw.text((x, 380), f"{region} {value}", fill="black")
        image.save(chart)
        pdf = documents / "spec.pdf"
        doc = SimpleDocTemplate(str(pdf), pagesize=letter)
        styles = getSampleStyleSheet()
        story = [Paragraph("Device Specification", styles["Title"]), Paragraph("The Acme Sensor is designed for indoor industrial monitoring. It supports continuous operation and a two-year warranty.", styles["BodyText"]), Spacer(1, 20), Paragraph("Technical Specifications", styles["Heading2"]), Table([["Property", "Value"], ["Operating Temperature", "-10 C to 55 C"], ["Voltage", "220V"], ["Weight", "4.5 kg"]], style=TableStyle([("GRID", (0, 0), (-1, -1), 1, colors.black)])), Spacer(1, 20), Image(str(chart), width=500, height=300)]
        doc.build(story)
    except ImportError as exc:
        raise SystemExit("Install reportlab and pillow to generate sample PDF: " + str(exc))
    try:
        import pandas as pd
        with pd.ExcelWriter(documents / "sales.xlsx", engine="openpyxl") as writer:
            pd.DataFrame([["North", 2500, 2800, 3100], ["South", 3000, 3400, 3700], ["East", 2900, 3200, 3500], ["West", 3500, 3900, 4200]], columns=["Region", "Q1", "Q2", "Q3"]).to_excel(writer, sheet_name="Sales", index=False)
            pd.DataFrame([["Sensor", "Monitoring", 120], ["Gateway", "Networking", 55], ["Mount", "Accessory", 240]], columns=["Product", "Category", "Stock"]).to_excel(writer, sheet_name="Products", index=False)
    except ImportError as exc:
        raise SystemExit("Install pandas and openpyxl to generate sample Excel: " + str(exc))
    print(f"Generated sample documents in {documents}")


if __name__ == "__main__":
    main()
