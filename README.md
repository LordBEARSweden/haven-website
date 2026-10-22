# Haven Nordic Health 2.0 — Gemensam grundstruktur

Den här leveransen **förändrar inte det visuella konceptet** från godkända Prototyp 2.
Den gör strukturen lättare att förvalta och återanvända. Ingen Bootstrap, npm,
Blazor, server-side rendering eller annan extern byggplattform krävs.

## Innan du kopierar filer

1. Kontrollera att du står i `feature/website-v2` och att du har sparat nuvarande arbete.
2. Kopiera filer och mappar från paketet till **roten** av ditt befintliga
   `haven-website`-projekt. Bevara befintliga `images/`, `fonts/`, `blog/`,
   `style.css` och alla undersidor. 
3. Projektets `index.html` får ersättas i *denna utvecklingsbranch*.
   Inga andra befintliga HTML-sidor ska ersättas i det här steget.
4. Öppna startsidan med Live Server i VS Code.
5. Skapa inte någon merge till `main` innan webbplatsens övriga sidor har flyttats
   till den gemensamma designen och hela sidan är testad.

## Var ändrar jag vad?

| Fil | Funktion |
|---|---|
| `src/pages/index.html` | Startsidan: all text och Aktuellt-korten |
| `src/partials/header.html` | Gemensam navigation och logotyp |
| `src/partials/footer.html` | Gemensam sidfot |
| `src/partials/analytics.html` | Befintlig Google Analytics-integration |
| `src/partials/booking-widget.html` | Befintlig Koalendar-widget |
| `css/tokens.css` | Färger, typsnitt, hero-bild, grundvariabler |
| `css/base.css` | Globala stilar för nya sidan |
| `css/components.css` | Gemensamma knappar, navigation och footer |
| `css/pages/home.css` | Startsidans sektioner |
| `css/responsive.css` | Mobil, surfplatta och andra brytpunkter |
| `js/site.js` | Mobilnavigation och automatiskt copyright-år |
| `index.html` | **Genererad** startsida; redigera normalt mallen i `src/pages` |
| `build.py` | Sammanfogar HTML-mallar till vanlig statisk HTML |

## Uppdatera HTML

Ändra `src/pages/index.html` och kör därefter i VS Code-terminalen
(PowerShell, i projektets rot):

```powershell
py -3 build.py
```

Om du använder `python` i stället för `py` fungerar också
`python build.py`. Python 3 behöver finnas installerat för **byggsteget**,
men behövs inte för själva hemsidan: den färdigbyggda `index.html`
ligger redan i paketet och kan öppnas direkt.

Ändrar du enbart CSS eller `js/site.js` behövs ingen ny HTML-generering.

## Viktigt om sökvägar

`{{root}}` i mallarna blir automatiskt rätt relativ sökväg.
Det är därför navigationen kan återanvändas på t.ex. en framtida
`blog/index.html` utan att länkarna till startsidan blir fel.

En framtida sida läggs under `src/pages/<namn>.html` (eller i en underkatalog).
Om mallen innehåller `{{header}}`, `{{footer}}`, `{{analytics}}` och
`{{booking_widget}}` får sidan samma gemensamma delar vid byggning.

`{{active:home}}` är en platsmarkör i headern som styr vilken länk som
får `aria-current="page"`. Den väljs automatiskt av byggskriptet. När vi
skapar nya sidor kan den regeln utökas till fler menylänkar.

## Bilder och logotyp

Paketet innehåller **inte** originalbilderna eller fontfilerna. Det
använder logotypen och typsnittsfilerna från det befintliga projektet:
`images/Haven Transparent No buffer no text.png` och `fonts/Averia_Serif_Libre/`.

Hero-bilden är tills vidare samma *externa testbild* som i prototyp 2,
konfigurerad i `css/tokens.css` via `--v2-hero-image`.
Innan lansering ska den ersättas med ett valt, lokalt optimerat foto och
användningsrätten kontrolleras. När filen ligger i `images/`, skriv t.ex.:

```css
--v2-hero-image: url('../images/hero-haven.webp');
```

## Lanseringsprincip

- `main`: gamla, publika hemsidan under fortsatt normal drift.
- `feature/website-v2`: nytt utseende, gemensamma komponenter och sidmallar.
- Publicera nya bloggar i `main` som vanligt och för in dem regelbundet i
  utvecklingsbranchen.
- När **alla** relevanta sidor konverterats, testa mobiler, tangentbord,
  formulär, externa integrationer, SEO och befintliga URL:er.
- Slå först därefter samman till `main` och publicera hela V2 som en helhet.

OBS: `style.css` ligger kvar för de sidor som fortfarande använder
version 1. Den nya startsidan länkar **inte längre** in `style.css`.

## Teknisk begränsning och nästa steg

Denna leverans skapar en gemensam grund och återanvändbara header/footer,
men migrerar **inte** resterande undersidor. Den är därför inte redo att
slås ihop till den publika sajten ännu.

Google Analytics och Koalendar är bevarade från tidigare version;
samtyckeshantering och externa tjänsters beteende behöver granskas innan
publicering. Spara ändringar i Git för att kunna återgå vid behov.
