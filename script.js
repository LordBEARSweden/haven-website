document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("email-form");

  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const email = document.getElementById("email").value;

    try {
      const res = await fetch("https://withered-mode-96d3.lord-bear.workers.dev/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ email })
      });

      const data = await res.json();

      console.log("Saved:", data);

      if (!res.ok) {
        throw new Error("Request failed");
      }

      if (data.message === "already exists") {
        alert("Du är redan registrerad");
        return;
      }

      alert("Tack! Du är registrerad");
      form.reset();

    } catch (err) {
      console.error(err);
      alert("Något gick fel.");
    }
  });
});