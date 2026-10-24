# Testordrar – orderintag v1

Påhittade beställningar för att testa orderintaget. Alla företag, personer, nummer och adresser är fiktiva.
**Referensdatum:** anta att alla meddelanden kom in **tisdag 2026-10-27 kl 07:45** (så att "imorgon", "fredag" osv kan tolkas).

Varje order har en kommentar om vad den testar. Ta bort kommentarerna om du vill testa "blint".

---

## 1 – Enkel, komplett
<!-- testar: grundfallet, allt finns -->
**Från:** linda.ek@bergqvistsbygg.se
**Ämne:** Transport torsdag

Hej!
Vi behöver hjälp med en transport på torsdag.
Hämtning: Bergqvists Bygg AB, Industrivägen 14, 433 61 Sävedalen, mellan 07–09.
Leverans: Byggarbetsplats Kvarnbacken, Kvarnbacksgatan 3, 431 37 Mölndal, före 12:00.
4 EUR-pallar gipsskivor, ca 3 200 kg totalt.
Mottagaren har ingen truck så bakgavellyft behövs.
Vår ref: BB-2291

Mvh
Linda Ek
Bergqvists Bygg AB
070-123 45 67

---

## 2 – Kort och slarvig
<!-- testar: relativt datum, saknad adress, ingen vikt -->
**Från:** jocke@nordkustplat.se
**Ämne:** (inget ämne)

kan ni ta 3 pallar till sundsvall imorgon bitti? samma som förra veckan

/J

---

## 3 – SMS
<!-- testar: sms-format, telefonnummer som enda kontakt -->
**SMS från:** 073-998 21 40

Hej det är Ahmed på Tvättexperten. 2 burar tvätt ska hämtas hos oss i Kungälv idag efter 14 o till Hotell Strandkanten i Stenungsnunds hamn innan 17. Ok?

---

## 4 – Ändring av befintlig order
<!-- testar: klassning som ÄNDRING, referens till tidigare order -->
**Från:** linda.ek@bergqvistsbygg.se
**Ämne:** SV: Transport torsdag

Hej igen, ändring på BB-2291 – det blir 6 pallar istället för 4, och leveransen kan vara fram till 14 istället. Resten som innan.
/Linda

---

## 5 – Avbokning
<!-- testar: klassning som AVBOKNING -->
**Från:** order@grontfrukt.se
**Ämne:** Avboka 4471

Hej, vi behöver tyvärr avboka order 4471 på fredag, kunden har stängt. Tack!
Maria, Grönt & Frukt i Väst

---

## 6 – Inte en order
<!-- testar: klassning som EJ_ORDER (fakturafråga) -->
**Från:** ekonomi@lindhsmaskin.se
**Ämne:** Faktura 88123

Hej, vi har fått faktura 88123 men tycker att DMT:n ser hög ut jämfört med förra månaden. Kan ni förklara?
Mvh Peter Lindh

---

## 7 – Kyl
<!-- testar: temperaturkrav, flera kolli -->
**Från:** logistik@vastkustfisk.se
**Ämne:** Kyltransport onsdag

Hej,
Onsdag morgon: hämta 12 kolli fisk (frigolitlådor, ca 25 kg st) på Fiskhamnen kaj 4, 414 58 Göteborg från 05:30.
Leverans till Restaurang Havsbris, Storgatan 22, 451 30 Uddevalla, senast 09:00.
Måste vara kyld 0–4 grader hela vägen.
Mvh Sofia, Västkust Fisk AB

---

## 8 – Farligt gods
<!-- testar: ADR-flagga -->
**Från:** inkop@kemteknik-alingsas.se
**Ämne:** Leverans fat

Hej
Vi skickar 8 fat à 200 liter avfettningsmedel (UN 1993, klass 3) från oss på Sävelundsgatan 9, Alingsås till Borås Industriservice, Viaredsvägen 30, Borås. Helst fredag förmiddag. Vikt ca 1 700 kg.
ADR-papper bifogas separat.
/Kemteknik Alingsås, Thomas

---

## 9 – Flera stopp
<!-- testar: en upphämtning, flera leveranser -->
**Från:** butik@inredningshuset.se
**Ämne:** Utkörning fredag

Hej! Tre leveranser på fredag från vårt lager på Datavägen 6 i Askim:
1) Soffa (ca 90 kg) till Eriksson, Björkvägen 12, Kungsbacka – kund hemma 10–14
2) Matbord + 6 stolar till Nilsson, Vallgatan 5, Göteborg – efter 15
3) Byrå till Andersson, Stigbergsliden 8, Göteborg – när som helst
Bärhjälp in behövs på alla. Två man.
Hälsningar Inredningshuset

---

## 10 – Engelska
<!-- testar: annat språk -->
**Från:** shipping@nordicparts-intl.com
**Subject:** Pickup request

Hi,
Please arrange pickup of 2 pallets (1.2 x 0.8 x 1.4 m, 450 kg each) from our supplier Mekano AB, Hisingsgatan 40, Göteborg, on Thursday. Deliver to our warehouse at Logistikvägen 2, Jönköping, by Friday 10:00.
PO number: NP-55120
Best regards, Jake

---

## 11 – Motstridig information
<!-- testar: osäkerhetsflagga när ämne och text säger olika -->
**Från:** anders@ahlsellmontage.se
**Ämne:** Körning onsdag

Hej, kan ni hämta 2 pallar hos oss på Exportgatan 19, Hisings Backa torsdag efter lunch och leverera till Partille samma dag?
Anders

---

## 12 – Vidarebefordrad tråd med brus
<!-- testar: hitta ordern i en lång tråd med signaturer -->
**Från:** reception@hallbergsfastigheter.se
**Ämne:** VB: VB: flytt av arkiv

Se nedan, kan ni ordna det?
Karin

-----Ursprungligt meddelande-----
Från: Erik Hallberg
Skickat: den 26 oktober 2026 16:02
Ämne: VB: flytt av arkiv

Karin, kan du be åkeriet?

-----Ursprungligt meddelande-----
Från: Stina Ro
Hej, arkivet (ca 40 flyttkartonger, kanske 600 kg) ska från Kontoret Avenyn 10 (3 tr, hiss finns) till förrådet på Ringögatan 18 nästa måndag, gärna förmiddag.
Stina
--
Stina Ro | Kontorsansvarig | Hallbergs Fastigheter AB
Detta mejl kan innehålla konfidentiell information...

---

## 13 – Återkommande
<!-- testar: återkommande uppdrag -->
**Från:** lager@bagerietsolsidan.se
**Ämne:** Fast körning

Hej! Från och med nästa vecka vill vi ha en fast körning varje måndag och torsdag: 10–15 backar bröd från bageriet på Solsidevägen 3, Lerum, kl 04:30 till tre ICA-butiker i Partille (vi skickar exakta adresser). Kan ni ge pris?

---

## 14 – Prisförfrågan, inte bokning
<!-- testar: offert vs bokning -->
**Från:** info@grusochsten.se
**Ämne:** Prisfråga

Hej, vad skulle det kosta att köra en container (20 fot, ca 18 ton) från Arendal i Göteborg till Trollhättan? Ingen brådska, vill bara ha en uppskattning.
/Grus & Sten Väst

---

## 15 – Brådskande
<!-- testar: akut-flagga, "nu" -->
**Från:** 070-555 88 12 (SMS)

AKUT!! Maskinen har gått sönder, reservdel (1 kartong ca 30 kg) måste från Bromma Hydraulik Ringvägen 4 Kungälv till oss på Lindholmen Varv, Göteborg SÅ FORT SOM MÖJLIGT. Ring mig. /Robert

---

## 16 – Saknar nästan allt
<!-- testar: flagga för mycket som saknas, ska inte gissa -->
**Från:** sara.m@gmail.com
**Ämne:** Hjälp

Hej, jag behöver flytta lite saker nästa vecka. Gör ni sånt?

---

## 17 – Volym i annan enhet
<!-- testar: flakmeter / lastmeter -->
**Från:** trafik@skogslundssag.se
**Ämne:** Virke till Varberg

Hej, ca 6 lastmeter virke från sågen i Skogslund (Sågverksvägen 1, 512 91 Svenljunga) till Varbergs Bygghandel, Hamnvägen 7, Varberg. Fredag, de tar emot 07–16. Vikt runt 9 ton. Behöver kran.

---

## 18 – Retur
<!-- testar: retur / omvänd riktning -->
**Från:** linda.ek@bergqvistsbygg.se
**Ämne:** Retur av tompallar

Hej, kan ni på torsdag när ni ändå är i Mölndal ta med 10 tomma EUR-pallar tillbaka från Kvarnbacken till oss i Sävedalen?
/Linda

---

## 19 – Två ordrar i ett mejl
<!-- testar: dela upp i flera ordrar -->
**Från:** order@grontfrukt.se
**Ämne:** Två körningar

Hej!
1. Torsdag: 5 pallar frukt från oss (Partihallarna, Göteborg) till Coop Tuve, före 07:00. Kylt.
2. Fredag: 3 pallar till ICA Kvantum Mölndal, före 06:30. Kylt.
Ca 400 kg per pall.
Maria

---

## 20 – Datumförvirring
<!-- testar: datum som redan passerat / tvetydigt -->
**Från:** kontor@mollerselektro.se
**Ämne:** Leverans 3/11

Hej, leverans av 2 kabeltrummor (ca 800 kg st) från Elgrossen, Transportgatan 21, Hisings Kärra till vårt projekt på Masthuggskajen den 3/11 kl 7. Behöver kranbil.
/Möllers El
