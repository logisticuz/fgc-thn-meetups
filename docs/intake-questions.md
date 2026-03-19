# Intake questions

## Mål & scope
- Vad är must-have i MVP vs nice-to-have?
- Vem är primär användare: arrangör/kiosk eller medlem?
- Hur snabbt måste incheckningen gå per person?
- Hur ska ni mäta närvaro: per session, per vecka, per medlem?

## Användarroller
- Vilka roller finns: admin, arrangör, medlem, gäst?
- Behöver admin kunna redigera historik eller bara exportera?
- Ska medlemmar kunna se sin egen historik?

## Medlems-ID / Sverok
- Har ni medlemsnummer i digital form (QR/NFC) redan?
- Finns format/validering för Sverok-kortet?
- Hur hanterar vi medlemmar utan kort/telefon?

## Check-in flow
- Ska medlemmar skanna en QR på plats (kiosk) eller visar de sin QR som scannas?
- En check-in per session eller flera (in/ut)?
- Vill ni stoppa dubletter, eller tillåta flera incheckningar?

## Utrustning & miljö
- Vilken hårdvara tänker ni: laptop, surfplatta, mobil, Raspberry Pi?
- Ska det funka utan internet helt?
- Finns krav på snabbhet (t.ex. 30 personer pa 5 min)?

## Offline & sync
- Ar offline-lage ett krav for MVP?
- Hur ska synk ske: manuell export/import, eller automatisk nar nat finns?
- Ska data lagras lokalt pa en enhet eller delas mellan flera?

## Data & lagring
- Var vill ni lagra data: lokalt filformat, SQLite, moln (senare)?
- Hur lange behover ni spara historik?
- Behöver ni backup eller export-rutiner?

## Rapporter till SFR
- Vilket format accepterar Studieframjandet (CSV, Excel, PDF)?
- Krävs specifika falt: personnummer, medlemsnummer, tid, plats?
- Ska rapport vara per tva manader automatiskt?

## Integritet & juridik
- Ska ni lagra personuppgifter (namn, e-post) eller bara medlems-ID?
- Behöver samtycke eller policytext visas i appen?
- Ska vi ha anonym gast-loggning?

## Statistik & insikter
- Vilka insikter vill ni se: per session, per medlem, snitt, retention?
- Ska ni kunna filtrera pa spel, aktivitet, arrangor?
- Vill ni ha dashboard direkt i appen eller export forst?

## Design & sprak
- Ska UI vara svenska, engelska, eller bada?
- Ska det vara kiosk-lage med stora knappar?
- Har ni logotyp/farger som ska användas?

## Tekniska preferenser
- Ar ni okej med webapp (PWA) som kan installeras offline?
- Vill ni undvika konton/ID-inloggning helt?
- Finns tekniska begransningar (ingen server, ingen molntjanst)?
