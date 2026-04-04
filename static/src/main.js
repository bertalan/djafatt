// static/src/main.js — ONLY JS FILE IN THE PROJECT
import "./main.css";
import "htmx.org";

// CSRF token injection for HTMX requests
document.body.addEventListener("htmx:configRequest", (e) => {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    if (match && e.detail.verb !== "get") {
        e.detail.headers["X-CSRFToken"] = decodeURIComponent(match[1]);
    }
});

// Fill payment fields when contact is changed (HTMX contactPaymentFill event)
document.body.addEventListener("contactPaymentFill", (e) => {
    const data = e.detail;
    const fields = {
        id_payment_method: data.payment_method,
        id_payment_terms: data.payment_terms,
        id_bank_name: data.bank_name,
        id_bank_iban: data.bank_iban,
    };
    for (const [id, value] of Object.entries(fields)) {
        const el = document.getElementById(id);
        if (el && value) el.value = value;
    }
});

// Contact select → fetch payment defaults via HTMX
document.addEventListener("DOMContentLoaded", () => {
    const contactSelect = document.querySelector("[data-contact-defaults-url]");
    if (!contactSelect) return;
    contactSelect.addEventListener("change", () => {
        const contactId = contactSelect.value;
        if (!contactId) return;
        const urlTemplate = contactSelect.dataset.contactDefaultsUrl;
        const url = urlTemplate.replace("{id}", contactId);
        htmx.ajax("GET", url, { target: "body", swap: "none" });
    });
});

// Product select → autofill line fields
document.body.addEventListener("change", (e) => {
    if (!e.target.classList.contains("product-select")) return;
    const productId = e.target.value;
    if (!productId) return;
    const urlTemplate = e.target.dataset.productFillUrl;
    if (!urlTemplate) return;
    const url = urlTemplate.replace("{id}", productId);
    const row = e.target.closest(".line-row");
    if (!row) return;
    fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } })
        .then(r => r.json())
        .then(data => {
            const set = (sel, val) => { const el = row.querySelector(sel); if (el && val !== undefined) el.value = val; };
            set("input[name$='-description']", data.description);
            set("input[name$='-unit_price_display']", data.unit_price_display);
            set("input[name$='-unit_of_measure']", data.unit_of_measure);
            if (data.vat_rate_id) set("select[name$='-vat_rate']", String(data.vat_rate_id));
            // Trigger totals recalc
            const priceField = row.querySelector("input[name$='-unit_price_display']");
            if (priceField) htmx.trigger(priceField, "change");
        });
});
