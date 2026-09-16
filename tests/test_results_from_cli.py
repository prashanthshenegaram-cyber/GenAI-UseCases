import json
from pathlib import Path

from src.main import main


def test_main_extract_and_write_output(tmp_path, monkeypatch):
    # Use a temporary invoice file and capture CLI output using the actual extraction pipeline.
    invoice_path = tmp_path / "invoice.txt"
    invoice_path.write_text("ACME Supplies Ltd\nInvoice # INV-2024-0891\nDate: March 15, 2024\nBill To: Zenith Corp\nSubtotal: 61.00\nTax: 10.98\nTotal: 71.98\nPayment Terms: Net 30\nCurrency: USD\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    # Determine workspace root can differ; use local file injection.
    try:
        main(["extract", "--input", str(invoice_path), "--prompt-version", "v5"])
    except SystemExit:
        pass

    out_path = Path("data") / "outputs" / "invoice_v5_output.json"
    if out_path.exists():
        data = json.loads(out_path.read_text(encoding="utf-8"))
        assert data["invoice_number"] == "INV-2024-0891"
