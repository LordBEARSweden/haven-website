const fs = require("fs");
const path = require("path");

const EMAIL_FILE = path.join(__dirname, "../emails.json");

function loadEmails() {
  if (!fs.existsSync(EMAIL_FILE)) return [];
  return JSON.parse(fs.readFileSync(EMAIL_FILE, "utf8"));
}

function saveEmail(email) {
  const emails = loadEmails();

  if (emails.includes(email)) {
    return { status: "exists" };
  }

  emails.push(email);
  fs.writeFileSync(EMAIL_FILE, JSON.stringify(emails, null, 2));

  return { status: "added" };
}

// enkel test (kommer från CLI eller API senare)
const email = process.argv[2];

if (!email) {
  console.log("No email provided");
  process.exit(1);
}

const result = saveEmail(email);
console.log(result);