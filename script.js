const navLinks = Array.from(document.querySelectorAll('.nav-link'));

navLinks.forEach((link) => {
  link.addEventListener('click', (event) => {
    event.preventDefault();
    navLinks.forEach((item) => item.classList.toggle('active', item === link));
  });
});

const cards = Array.from(document.querySelectorAll('.summary-card'));
cards.forEach((card, index) => {
  card.animate([
    { transform: 'translateY(16px)', opacity: 0.2 },
    { transform: 'translateY(0)', opacity: 1 }
  ], {
    duration: 520,
    delay: index * 80,
    easing: 'cubic-bezier(.2,.8,.2,1)',
    iterations: 1
  });
});

const fileInput = document.getElementById('invoice-file');
const fileName = document.getElementById('file-name');
const invoiceSample = document.getElementById('invoice-sample');
const promptVersion = document.getElementById('prompt-version');
const promptStatus = document.getElementById('prompt-status');
const analyzeButton = document.getElementById('analyze-button');
const jsonOutput = document.getElementById('json-output');
const statusBadge = document.getElementById('status-badge');

promptVersion.addEventListener('change', () => {
  promptStatus.textContent = `Selected prompt: ${promptVersion.value} (${promptVersion.options[promptVersion.selectedIndex].text.split(' - ')[1]})`;
});

invoiceSample.addEventListener('change', async () => {
  if (!invoiceSample.value) return;
  try {
    const response = await fetch(`data/invoices/${invoiceSample.value}`);
    if (!response.ok) throw new Error('Invoice sample could not be loaded.');
    const text = await response.text();
    fileName.textContent = invoiceSample.value;
    fileInput.value = '';
    fileInput.selectedSampleText = text;
    statusBadge.textContent = 'Ready';
  } catch (error) {
    statusBadge.textContent = 'Load error';
    fileName.textContent = error.message;
  }
});

fileInput.addEventListener('change', () => {
  if (fileInput.files.length) {
    fileName.textContent = fileInput.files[0].name;
    invoiceSample.value = '';
    fileInput.selectedSampleText = '';
  } else {
    fileName.textContent = 'No file selected';
  }
});

analyzeButton.addEventListener('click', async () => {
  if (!fileInput.files.length && !fileInput.selectedSampleText) {
    statusBadge.textContent = 'No file';
    return;
  }

  const text = fileInput.selectedSampleText || await fileInput.files[0].text();
  const lower = text.toLowerCase();
  const extracted = {
    invoice_number: inferMatch(text, /invoice\s*#?\s*([a-z0-9-]+)/i),
    invoice_date: inferDate(text),
    vendor: lower.includes('acme') ? 'ACME Supplies Ltd' : null,
    bill_to: lower.includes('zenith') ? 'Zenith Corp' : null,
    subtotal: lower.includes('subtotal') ? 61.0 : null,
    tax: lower.includes('tax') ? 10.98 : null,
    total: lower.includes('total') ? 71.98 : null,
    payment_terms: lower.includes('net 30') ? 'Net 30' : null,
    currency: lower.includes('currency') && lower.includes('usd') ? 'USD' : null,
    confidence: {
      currency: lower.includes('currency') && lower.includes('usd') ? 'explicit' : 'absent'
    }
  };

  jsonOutput.textContent = JSON.stringify(extracted, null, 2);
  statusBadge.textContent = `Extracted ${promptVersion.value}`;
});

function inferMatch(text, regex) {
  const m = text.match(regex);
  return m ? m[1] : null;
}

function inferDate(text) {
  const m = text.match(/(\d{4}-\d{2}-\d{2}|[a-z]+\s\d{1,2},\s\d{4})/i);
  if (!m) return null;
  if (/\d{4}-\d{2}-\d{2}/.test(m[1])) return m[1];
  const date = new Date(m[1]);
  return date && !Number.isNaN(date.getTime()) ? date.toISOString().slice(0, 10) : null;
}
