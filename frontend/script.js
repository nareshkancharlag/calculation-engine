const API_URL = "http://localhost:8000";

async function addRule() {
    const input = document.getElementById('newRuleInput');
    const statusEl = document.getElementById('addRuleStatus');
    const btn = event.target;

    if (!input.value.trim()) {
        alert("Please enter rule text.");
        return;
    }

    btn.disabled = true;
    statusEl.textContent = "Adding rule...";

    try {
        const response = await fetch(`${API_URL}/add_rule`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: input.value })
        });
        const data = await response.json();

        if (response.ok) {
            statusEl.textContent = data.message;
            statusEl.style.color = "green";
            input.value = ""; // clear input
        } else {
            statusEl.textContent = `Error: ${data.detail}`;
            statusEl.style.color = "red";
        }
    } catch (error) {
        statusEl.textContent = `Error: ${error.message}`;
        statusEl.style.color = "red";
    } finally {
        btn.disabled = false;
    }
}

async function ingestRules() {
    const statusEl = document.getElementById('ingestStatus');
    const btn = document.getElementById('ingestBtn');

    statusEl.textContent = "Ingesting rules...";
    btn.disabled = true;

    try {
        const response = await fetch(`${API_URL}/ingest`, {
            method: 'POST'
        });
        const data = await response.json();

        if (response.ok) {
            statusEl.textContent = `Success: ${data.message}`;
            statusEl.style.color = "green";
        } else {
            statusEl.textContent = `Error: ${data.detail}`;
            statusEl.style.color = "red";
        }
    } catch (error) {
        statusEl.textContent = `Error connecting to server: ${error.message}`;
        statusEl.style.color = "red";
    } finally {
        btn.disabled = false;
    }
}

async function calculateTax() {
    const input = document.getElementById('queryInput').value;
    const resultSection = document.getElementById('resultSection');
    const taxAmountEl = document.getElementById('taxAmount');
    const explanationEl = document.getElementById('explanationText');
    const rawOutputEl = document.getElementById('rawOutputText');
    const btn = document.getElementById('calcBtn');

    if (!input.trim()) {
        alert("Please enter a query.");
        return;
    }

    btn.disabled = true;
    btn.textContent = "Calculating...";

    try {
        const response = await fetch(`${API_URL}/calculate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ text: input })
        });

        const data = await response.json();

        if (response.ok) {
            resultSection.classList.remove('hidden');


            // Handle generic response
            console.log("Response Data:", data);
            let val = data.calculated_value !== undefined ? data.calculated_value : data.tax_amount;
            console.log("Calculated Value:", val);

            let displayVal = "N/A";
            if (typeof val === 'number') {
                displayVal = '$' + val.toFixed(2);
            } else if (val) {
                displayVal = val;
            }

            // If displayVal is not usable but we have a result text, use that partially?
            // User asked: "Answer is not displayed... Display response on the UI for all types of queries."
            // If value is 0 or N/A, and result string exists, maybe we should rely on result string?
            // Actually, let's trust calculated_value if present.

            // IMPORTANT: Note that we renamed the HTML ID from taxAmount to resultValue in index.html
            // So we must fix the selector here too.
            const resultValueEl = document.getElementById('resultValue');
            // Note: index.html change: id="taxAmount" -> id="resultValue"
            // But we must assume index.html change was applied or will be.
            // Let's check if the element exists, or fallback to taxAmount locally? 
            // The index.html edit was step 229, so it should be resultValue.

            if (resultValueEl) {
                resultValueEl.textContent = displayVal;
            } else {
                // Fallback if ID wasn't updated in DOM yet (should be though)
                document.getElementById('taxAmount').textContent = displayVal;
            }

            explanationEl.textContent = data.explanation || data.result;
            rawOutputEl.textContent = JSON.stringify(data, null, 2);

        } else {
            alert(`Error: ${data.detail}`);
        }
    } catch (error) {
        alert(`Error connecting to server: ${error.message}`);
    } finally {
        btn.disabled = false;
        btn.textContent = "Calculate Tax";
    }
}
