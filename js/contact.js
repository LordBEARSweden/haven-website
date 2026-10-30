/* Kontakt 2.0: kopierar alltid det värde som faktiskt visas på sidan. */
document.addEventListener('DOMContentLoaded', () => {
  const status = document.getElementById('v2-contact-copy-status');
  const buttons = document.querySelectorAll('.v2-contact-page [data-copy-target]');

  for (const button of buttons) {
    button.addEventListener('click', async () => {
      const targetId = button.getAttribute('data-copy-target');
      const source = document.getElementById(targetId);
      if (!source || !status) return;
      const value = source.textContent.trim();
      if (!value) return;
      try {
        if (!navigator.clipboard || !navigator.clipboard.writeText) {
          throw new Error('Clipboard API unavailable');
        }
        await navigator.clipboard.writeText(value);
        status.textContent = `${button.getAttribute('data-copy-label') || 'Uppgift'} kopierat!`;
      } catch (_) {
        status.textContent = 'Automatisk kopiering fungerar inte här. Markera texten och kopiera manuellt.';
      }
    });
  }
});
