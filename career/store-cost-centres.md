# Store cost centres

Match key for GL vs cost pivots. The last 5 digits of `Acct` are the store. Compare those digits to the code below (numeric codes shorter than 5 digits are padded with leading zeros, so `14` matches an account ending `00014`).

`PA Allocation` on the invoice pivot should equal `PA` on the cost pivot. A `0` or blank PA is unallocated: test it against the PA on the same supplier and store where the two sums do not already agree, and mark anything that is not an exact tie for manual check.

## Austria

| Store | Cost centre | Match key |
|---|---|---|
| Parndorf | 01000 - Parndorf | 01000 |
| Vienna | 01030 - Vienna Westfield | 01030 |

## Belgium

| Store | Cost centre | Match key |
|---|---|---|
| Maasmechelen | 01010 - Maasmechelen | 01010 |
| Messancy | 01000 - Messancy | 01000 |
| Antwerp | 01030 - Antwerp | 01030 |
| Brussels | 01040 - Brussels Louise | 01040 |

## Denmark

| Store | Cost centre | Match key |
|---|---|---|
| Copenhagen | 04000 - Copenhagen | 04000 |

## France

| Store | Cost centre | Match key |
|---|---|---|
| Lyon Village | 01070 - Lyon | 01070 |
| Troyes | 01030 - Troyes | 01030 |
| Carre Senart | 01060 - Carre Cenart | 01060 |
| Parly 2 | 01050 - Parly 2 | 01050 |
| La Defense | 01020 - La Defense | 01020 |
| Le Marais | 01130 - Le Marais | 01130 |
| Lyon Republique | 01150 - Lyon Republique | 01150 |
| Marseille | 01140 - Marseille | 01140 |
| One Nation | 01090 - One Nation Paris | 01090 |
| FDH | 01000 - Forum Des Halles | 01000 |
| Giverny | 01120 - Giverny | 01120 |
| Provence | 01040 - Provence | 01040 |
| Roubaix | 01010 - Roubaix | 01010 |
| CAP 3000 | 01190 - CAP 3000 | 01190 |
| Toulouse | 01170 - Toulouse | 01170 |

## Germany

| Store | Cost centre | Match key |
|---|---|---|
| Berlin East | 01000 - Berlin | 01000 |
| Wustermark | 01040 - Wustermark | 01040 |
| Centro Oberhausen | 01020 - Oberhausen | 01020 |
| Hamburg | 01060 - Hamburg | 01060 |
| Ingolstadt | 01030 - Ingolstadt | 01030 |
| Berlin West | 01070 - Berlin West | 01070 |
| Neumunster | 01010 - Neumunster | 01010 |
| Stuttgart | 01100 - Stuttgart | 01100 |
| Zweibrucken | 01050 - Zweibruecken | 01050 |
| Munich | 01090 - Munich | 01090 |
| Metzingen | 01080 - Metzingen | 01080 |
| Cologne | 01110 - Cologne | 01110 |
| Wertheim | 01111 - Weirtheim | 01111 |
| Ochtum Park | 01113 - Ochtum Park | 01113 |

## Italy

| Store | Cost centre | Match key |
|---|---|---|
| Barberino | 01010 - BARBERINO | 01010 |
| Fidenza | 01030 - FIDENZA | 01030 |
| Serravalle | 01020 - SERRAVALLE | 01020 |
| Rome | 01040 - ROMA | 01040 |
| Verona | 01070 - Verona | 01070 |

## Netherlands

| Store | Cost centre | Match key |
|---|---|---|
| Amsterdam | 01000 - Amsterdam | 01000 |
| Styles Outlet | 01030 - Style Outlets | 01030 |
| Batavia | 01020 - Batavia Stad | 01020 |
| Mall of Netherlands | 01040 - Mall of the Netherlands | 01040 |
| Roermond | 01010 - Roermond | 01010 |
| Roosendaal | 01050 - Roosendaal | 01050 |
| Rotterdam | 01070 - Rotterdam | 01070 |

## Portugal

| Store | Cost centre | Match key |
|---|---|---|
| Vila do Conde | 14 - Outlet store Vila do Conde | 00014 |
| Freeport | 13 - Outlet store Freeport | 00013 |
| Faro | 15 - Outlet store Faro | 00015 |
| Colombo | 11 - Lisbon Colombo | 00011 |
| Rua Garrett | 10016 - Lisbon Garrett | 10016 |

## Spain

| Store | Cost centre | Match key |
|---|---|---|
| Fuencarral | (blank) | — |
| Getafe | 55 - Getafe | 00055 |
| La Rambla | 8 - Rambla | 00008 |
| La Roca | 98 - Outlet store La Roca | 00098 |
| Las Rozas | 97 - Outlet Las Rozas | 00097 |
| Malaga | 92 - Outlet Málaga | 00092 |
| Mallorca | 07 - Outlet Mallorca | 00007 |
| San Sebastian | 99 - Outlet San Sebastián de los Reyes | 00099 |
| Sevilla | (blank) | — |
| Valencia | 46 - Valencia | 00046 |
| Portal Del Angel | 89 - FP store Portal Angel | 00089 |

## Sweden

| Store | Cost centre | Match key |
|---|---|---|
| Stockholm | 04101 - Stockholm | 04101 |
| Mall of Scandinavia | 04100 - Mall of Scandinavia | 04100 |

## UK

| Store | Cost centre | Match key |
|---|---|---|
| White City | 07371 - White City | 07371 |
| West Midlands | (blank) | — |
| Wembley | 07010 - Retail Wembley | 07010 |
| Trafford | 07373 - Retail Trafford | 07373 |
| Swindon | 07394 - Retail Swindon | 07394 |
| Stratford | 07372 - Retail Stratford | 07372 |
| Oxford Street | 07393 - Retail Oxford Street | 07393 |
| O2 | 07390 - Retail London O2 | 07390 |
| Livingston | 07380 - Retail Livingston | 07380 |
| Leeds | 07377 - Retail Leeds | 07377 |
| Kildare | 07397 - Retail Kildare | 07397 |
| Gunwharf Quays | 07376 - Retail Gunwharf Quays | 07376 |
| Glasgow | 07378 - Retail Glasgow | 07378 |
| Flimby | 07000 - Retail Flimby | 07000 |
| Edinburgh | 07375 - Retail Edinburgh | 07375 |
| Dublin | 07374 - Retail Dublin | 07374 |
| Dalton Park | 07070 - Retail Dalton | 07070 |
| Cheshire Oaks | 07392 - Retail C Oaks SG&A | 07392 |
| Castleford | 8005 - NBFS UK Castleford | 08005 |
| Bridgend | 07395 - Retail Bridgend | 07395 |
| Birmingham | 07381 - Retail Birmingham | 07381 |
| Bicester | 07399 - Retail Bicester | 07399 |

## Central

| Store | Cost centre | Match key |
|---|---|---|
| NBEU | NBEU - Central costs | — |

Blank match keys (Fuencarral, Sevilla, West Midlands, NBEU) cannot be tied from the account suffix. Manual check.

Same 5-digit code is reused across countries (Austria Parndorf and Belgium Messancy are both `01000`). Always match entity + code, not the code alone.

**See also:** [[README]]

**Section:** [[career]]
