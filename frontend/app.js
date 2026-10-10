// Talks ONLY to the Main Backend (same origin). No SMTP details and no Email Microservice URL here.
const SEND_URL = "/send";
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const form = document.getElementById("email-form");
const button = document.getElementById("send-button");
const buttonLabel = button.querySelector(".label");
const result = document.getElementById("result");
const fields = {
  to: document.getElementById("to"),
  subject: document.getElementById("subject"),
  message: document.getElementById("message"),
};

function setFieldError(name, message) {
  const input = fields[name];
  const errorEl = document.getElementById(`${name}-error`);
  if (!input || !errorEl) return;
  errorEl.textContent = message || "";
  input.classList.toggle("invalid", Boolean(message));
}

function clearErrors() {
  Object.keys(fields).forEach((name) => setFieldError(name, ""));
}

function showResult(type, message) {
  result.hidden = false;
  result.className = `result ${type}`;
  result.textContent = message;
}

function setLoading(isLoading) {
  button.disabled = isLoading;
  button.classList.toggle("loading", isLoading);
  buttonLabel.textContent = isLoading ? "Sending..." : "Send Email";
}

function validate(data) {
  const errors = {};
  if (!data.to) errors.to = "Please enter a recipient email address.";
  else if (!EMAIL_PATTERN.test(data.to) || !fields.to.checkValidity()) errors.to = "Please enter a valid email address.";
  if (!data.subject) errors.subject = "Please enter a subject.";
  if (!data.message) errors.message = "Please enter a message.";
  return errors;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearErrors();
  result.hidden = true;

  const data = {
    to: fields.to.value.trim(),
    subject: fields.subject.value.trim(),
    message: fields.message.value.trim(),
  };

  const errors = validate(data);
  if (Object.keys(errors).length > 0) {
    Object.entries(errors).forEach(([name, message]) => setFieldError(name, message));
    showResult("error", "Please fix the highlighted fields.");
    return;
  }

  setLoading(true);
  let response;
  try {
    response = await fetch(SEND_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
  } catch (networkError) {
    showResult("error", "✗ Backend unavailable. Please check that the Main Backend is running.");
    setLoading(false);
    return;
  }

  let body = null;
  try {
    body = await response.json();
  } catch {
    // Non-JSON response; handled below.
  }
  setLoading(false);

  if (response.ok && body && body.success) {
    showResult("success", "✓ Email sent successfully");
    form.reset();
    return;
  }

  if (response.status === 422 && body && Array.isArray(body.errors)) {
    body.errors.forEach((err) => setFieldError(err.field, err.message));
    showResult("error", "Validation error: please fix the highlighted fields.");
    return;
  }

  const detail = body && body.message ? body.message : `Unexpected response (HTTP ${response.status}).`;
  showResult("error", `✗ Email sending failed: ${detail}`);
});
