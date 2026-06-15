document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("email-form");

  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const email = document.getElementById("email").value;

    console.log("Saving email:", email);

    alert("Tack! Du är registrerad för blog alerts.");

    form.reset();
  });
});