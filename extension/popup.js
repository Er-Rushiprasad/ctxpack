const resultEl = document.getElementById("result");

document.getElementById("ping").addEventListener("click", async () => {
  resultEl.textContent = "fetching...";
  try {
    const res = await fetch("http://127.0.0.1:8000/status");
    const data = await res.json();
    resultEl.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    resultEl.textContent = `fetch failed: ${err.message}\n(is the server running on 127.0.0.1:8000?)`;
  }
});
