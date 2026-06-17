form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const email = document.getElementById("email").value;

  console.log("Saving email:", email);

  await fetch("https://api.github.com/repos/LordBEARSweden/haven-website/dispatches", {
    method: "POST",
    headers: {
      "Accept": "application/vnd.github+json",
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      event_type: "new_email",
      client_payload: {
        email: email
      }
    })
  });

  alert("Tack! Du är registrerad för blog alerts.");
  form.reset();
});