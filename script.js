console.log("script loaded");
form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const email = document.getElementById("email").value;

  // simulering just nu
  console.log("Saving email:", email);

  alert("Tack! Du är registrerad för blog alerts.");

  form.reset();
});
document.addEventListener("DOMContentLoaded", () => {
  // din kod här
});