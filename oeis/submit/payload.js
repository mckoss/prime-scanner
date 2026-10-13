window.OEIS_SUBMIT = {
 "meta": {
  "date": "2026-10-13",
  "run": "fresh",
  "frontier": 26306285568359759,
  "check": true,
  "check_note": "",
  "name": "Mike Koss"
 },
 "open_drafts": [
  "A058867",
  "A087770",
  "A096265"
 ],
 "draft_limit": 3,
 "credits": {
  "A058867": "terms 1..20 from Harvey Dubner, terms 21..30 from Dmitry Petukhov",
  "A087770": "terms 1..29 from Walter Carlini, Ray Chandler, Hugo Pfoertner and Giovanni Resta",
  "A096265": "terms 1..50 from Ken Takusagawa, terms 51..55 from Hugo Pfoertner",
  "A005669": "terms 1..77 from Charles R Greathouse IV, terms 78..82 from John W. Nicholson",
  "A107578": "terms 1..80 from John W. Nicholson; terms 1..75 from Jens Kruse Andersen; further terms coming from Thomas R. Nicely site",
  "A023187": "terms 1..56 from David W. Wilson, Jud McCranie, T. D. Noe and Dmitry Petukhov",
  "A031133": "terms 1..67 from Jeff Burch, Patrick De Geest, Jud McCranie, Jon E. Schoenfield, Dmitry Kamenetsky, Dmitry Petukhov, Vladimir Chirkov and Natalia Makarova",
  "A031134": "terms 1..67 from Jeff Burch, Patrick De Geest, Jud McCranie, Jon E. Schoenfield, Dmitry Kamenetsky, Dmitry Petukhov, Vladimir Chirkov and Natalia Makarova",
  "A031132": "terms 1..67 from Jeff Burch, Patrick De Geest, Jud McCranie, Jon E. Schoenfield, Dmitry Kamenetsky, Dmitry Petukhov, Vladimir Chirkov and Natalia Makarova",
  "A058868": "terms 0..19 from Harvey Dubner, terms 20..29 from Dmitry Petukhov"
 },
 "drafts": [
  {
   "aid": "A031132",
   "role": "the span between them",
   "what": "b-file +4 terms (67 to 71), Xref +A096265 (optional)",
   "items": [
    "b-file:A031132",
    "xref:A031132:A096265"
   ],
   "summary": "Extend the b-file to 71 terms; optionally add cross-references to A096265.",
   "blocked_on": null,
   "slot": "waits",
   "edits": [
    {
     "field": "Link",
     "code": "%H",
     "action": "credit_bfile_link",
     "text": "Mike Koss, <a href=\"/A031132/b031132_k.txt\">Table of n, a(n) for n = 1..71</a> (terms 1..67 from Jeff Burch, Patrick De Geest, Jud McCranie, Jon E. Schoenfield, Dmitry Kamenetsky, Dmitry Petukhov, Vladimir Chirkov and Natalia Makarova)"
    },
    {
     "field": "Xref",
     "code": "%Y",
     "action": "add",
     "add": [
      [
       "A096265",
       "the aloof prime"
      ]
     ],
     "optional": true
    }
   ],
   "uploads": [
    {
     "kind": "b-file",
     "name": "b031132.txt",
     "replaces": null,
     "slot": 0,
     "rows": 71,
     "published": false,
     "purpose": "The b-file: 71 terms, uploaded with the b-file box ticked. OEIS then rewrites the b-file %H line to credit only you; once saved, the Link card puts the earlier contributors back.",
     "desc": "",
     "content": "# A031132, 71 terms.\n#\n# Terms 1..67 from Jeff Burch, Patrick De Geest, Jud McCranie, Jon E. Schoenfield, Dmitry Kamenetsky, Dmitry Petukhov, Vladimir Chirkov and Natalia Makarova.\n# Terms 68..71 are new.\n# Every term independently rederived by an exhaustive scan from 0,\n# as column 3 of its aloof records.\n#\n# Mike Koss. Data as of 2026-10-13, when the scan last advanced.\n# Searched all below 26,306,285,568,359,759: every record up to that\n# bound is present, and there is no further one below it.\n# Independently confirmed by an exhaustive scan; check_oeis.py passes.\n# Source: https://github.com/mckoss/prime-scanner\n# OEIS data CC BY-SA 4.0\n1 3\n2 4\n3 6\n4 10\n5 12\n6 14\n7 18\n8 24\n9 28\n10 40\n11 42\n12 44\n13 48\n14 50\n15 56\n16 58\n17 72\n18 76\n19 80\n20 82\n21 100\n22 114\n23 116\n24 126\n25 138\n26 140\n27 160\n28 190\n29 200\n30 234\n31 236\n32 246\n33 248\n34 270\n35 306\n36 328\n37 330\n38 336\n39 340\n40 372\n41 376\n42 410\n43 436\n44 438\n45 450\n46 476\n47 502\n48 506\n49 524\n50 540\n51 546\n52 594\n53 600\n54 624\n55 678\n56 690\n57 700\n58 760\n59 780\n60 838\n61 900\n62 944\n63 972\n64 1014\n65 1016\n66 1032\n67 1152\n68 1168\n69 1170\n70 1182\n71 1220\n"
    }
   ]
  },
  {
   "aid": "A031133",
   "role": "the lower neighbour",
   "what": "b-file +4 terms (67 to 71)",
   "items": [
    "b-file:A031133"
   ],
   "summary": "Extend the b-file to 71 terms.",
   "blocked_on": null,
   "slot": "waits",
   "edits": [
    {
     "field": "Link",
     "code": "%H",
     "action": "credit_bfile_link",
     "text": "Mike Koss, <a href=\"/A031133/b031133_k.txt\">Table of n, a(n) for n = 1..71</a> (terms 1..67 from Jeff Burch, Patrick De Geest, Jud McCranie, Jon E. Schoenfield, Dmitry Kamenetsky, Dmitry Petukhov, Vladimir Chirkov and Natalia Makarova)"
    }
   ],
   "uploads": [
    {
     "kind": "b-file",
     "name": "b031133.txt",
     "replaces": null,
     "slot": 0,
     "rows": 71,
     "published": true,
     "purpose": "The b-file: 71 terms, uploaded with the b-file box ticked. OEIS then rewrites the b-file %H line to credit only you; once saved, the Link card puts the earlier contributors back.",
     "desc": "",
     "content": "# A031133, 71 terms.\n#\n# Terms 1..67 from Jeff Burch, Patrick De Geest, Jud McCranie, Jon E. Schoenfield, Dmitry Kamenetsky, Dmitry Petukhov, Vladimir Chirkov and Natalia Makarova.\n# Terms 68..71 are new.\n# Every term independently rederived by an exhaustive scan from 0,\n# as column 6 of its aloof records.\n#\n# Mike Koss. Data as of 2026-10-13, when the scan last advanced.\n# Searched all below 26,306,285,568,359,759: every record up to that\n# bound is present, and there is no further one below it.\n# Independently confirmed by an exhaustive scan; check_oeis.py passes.\n# Source: https://github.com/mckoss/prime-scanner\n# OEIS data CC BY-SA 4.0\n1 2\n2 3\n3 5\n4 19\n5 47\n6 83\n7 109\n8 199\n9 1123\n10 1321\n11 2161\n12 2477\n13 5591\n14 9551\n15 14087\n16 19603\n17 19609\n18 31393\n19 31397\n20 38461\n21 58789\n22 155893\n23 360653\n24 370247\n25 396733\n26 1357193\n27 1561891\n28 4652317\n29 8917463\n30 20831299\n31 38089217\n32 70396343\n33 72546143\n34 102765577\n35 142414553\n36 325737649\n37 436272961\n38 476956801\n39 1346350651\n40 1453168061\n41 2949346891\n42 3367207667\n43 9085929037\n44 10726904659\n45 20678048297\n46 25056082067\n47 31587561139\n48 42652618301\n49 50949283109\n50 122787888679\n51 215686840157\n52 220578149899\n53 724200190201\n54 929156727013\n55 1032148488143\n56 3605572653481\n57 4079970755221\n58 5061226833427\n59 12772332382321\n60 19535748742639\n61 21185697626083\n62 117102787055687\n63 471911699384771\n64 528459528876289\n65 543684371469023\n66 811782668945159\n67 1693182318746351\n68 12099132127786609\n69 12568891238649583\n70 14878430907698447\n71 16020873778856279\n"
    }
   ]
  },
  {
   "aid": "A031134",
   "role": "the upper neighbour",
   "what": "b-file +4 terms (67 to 71)",
   "items": [
    "b-file:A031134"
   ],
   "summary": "Extend the b-file to 71 terms.",
   "blocked_on": null,
   "slot": "waits",
   "edits": [
    {
     "field": "Link",
     "code": "%H",
     "action": "credit_bfile_link",
     "text": "Mike Koss, <a href=\"/A031134/b031134_k.txt\">Table of n, a(n) for n = 1..71</a> (terms 1..67 from Jeff Burch, Patrick De Geest, Jud McCranie, Jon E. Schoenfield, Dmitry Kamenetsky, Dmitry Petukhov, Vladimir Chirkov and Natalia Makarova)"
    }
   ],
   "uploads": [
    {
     "kind": "b-file",
     "name": "b031134.txt",
     "replaces": null,
     "slot": 0,
     "rows": 71,
     "published": true,
     "purpose": "The b-file: 71 terms, uploaded with the b-file box ticked. OEIS then rewrites the b-file %H line to credit only you; once saved, the Link card puts the earlier contributors back.",
     "desc": "",
     "content": "# A031134, 71 terms.\n#\n# Terms 1..67 from Jeff Burch, Patrick De Geest, Jud McCranie, Jon E. Schoenfield, Dmitry Kamenetsky, Dmitry Petukhov, Vladimir Chirkov and Natalia Makarova.\n# Terms 68..71 are new.\n# Every term independently rederived by an exhaustive scan from 0,\n# as column 7 of its aloof records.\n#\n# Mike Koss. Data as of 2026-10-13, when the scan last advanced.\n# Searched all below 26,306,285,568,359,759: every record up to that\n# bound is present, and there is no further one below it.\n# Independently confirmed by an exhaustive scan; check_oeis.py passes.\n# Source: https://github.com/mckoss/prime-scanner\n# OEIS data CC BY-SA 4.0\n1 5\n2 7\n3 11\n4 29\n5 59\n6 97\n7 127\n8 223\n9 1151\n10 1361\n11 2203\n12 2521\n13 5639\n14 9601\n15 14143\n16 19661\n17 19681\n18 31469\n19 31477\n20 38543\n21 58889\n22 156007\n23 360769\n24 370373\n25 396871\n26 1357333\n27 1562051\n28 4652507\n29 8917663\n30 20831533\n31 38089453\n32 70396589\n33 72546391\n34 102765847\n35 142414859\n36 325737977\n37 436273291\n38 476957137\n39 1346350991\n40 1453168433\n41 2949347267\n42 3367208077\n43 9085929473\n44 10726905097\n45 20678048747\n46 25056082543\n47 31587561641\n48 42652618807\n49 50949283633\n50 122787889219\n51 215686840703\n52 220578150493\n53 724200190801\n54 929156727637\n55 1032148488821\n56 3605572654171\n57 4079970755921\n58 5061226834187\n59 12772332383101\n60 19535748743477\n61 21185697626983\n62 117102787056631\n63 471911699385743\n64 528459528877303\n65 543684371470039\n66 811782668946191\n67 1693182318747503\n68 12099132127787777\n69 12568891238650753\n70 14878430907699629\n71 16020873778857499\n"
    }
   ]
  },
  {
   "aid": "A058868",
   "role": "the distance to each neighbour",
   "what": "b-file +4 terms (30 to 34)",
   "items": [
    "b-file:A058868"
   ],
   "summary": "Extend the b-file to 34 terms.",
   "blocked_on": null,
   "slot": "waits",
   "edits": [
    {
     "field": "Link",
     "code": "%H",
     "action": "credit_bfile_link",
     "text": "Mike Koss, <a href=\"/A058868/b058868_k.txt\">Table of n, a(n) for n = 1..34</a> (terms 0..19 from Harvey Dubner, terms 20..29 from Dmitry Petukhov)"
    }
   ],
   "uploads": [
    {
     "kind": "b-file",
     "name": "b058868.txt",
     "replaces": null,
     "slot": 0,
     "rows": 34,
     "published": false,
     "purpose": "The b-file: 34 terms, uploaded with the b-file box ticked. OEIS then rewrites the b-file %H line to credit only you; once saved, the Link card puts the earlier contributors back.",
     "desc": "",
     "content": "# A058868, 34 terms.\n#\n# Terms 0..19 from Harvey Dubner, terms 20..29 from Dmitry Petukhov.\n# Terms 30..33 are new.\n# Every term independently rederived by an exhaustive scan from 0,\n# as column 3 of its equidistant records.\n#\n# Mike Koss. Data as of 2026-10-13, when the scan last advanced.\n# Searched all below 26,306,285,568,359,759: every record up to that\n# bound is present, and there is no further one below it.\n# Independently confirmed by an exhaustive scan; check_oeis.py passes.\n# Source: https://github.com/mckoss/prime-scanner\n# OEIS data CC BY-SA 4.0\n0 2\n1 6\n2 12\n3 24\n4 30\n5 42\n6 48\n7 60\n8 66\n9 72\n10 84\n11 90\n12 96\n13 144\n14 150\n15 156\n16 168\n17 186\n18 198\n19 204\n20 210\n21 228\n22 240\n23 258\n24 276\n25 300\n26 306\n27 348\n28 390\n29 420\n30 426\n31 438\n32 468\n33 510\n"
    }
   ]
  },
  {
   "aid": "A005669",
   "role": "index of the lower prime",
   "what": "b-file +3 terms (82 to 85), Xref +A107578 (optional)",
   "items": [
    "b-file:A005669",
    "xref:A005669:A107578"
   ],
   "summary": "Extend the b-file to 85 terms; optionally add cross-references to A107578.",
   "blocked_on": null,
   "slot": "waits",
   "edits": [
    {
     "field": "Link",
     "code": "%H",
     "action": "credit_bfile_link",
     "text": "Mike Koss, <a href=\"/A005669/b005669_k.txt\">Table of n, a(n) for n = 1..85</a> (terms 1..77 from Charles R Greathouse IV, terms 78..82 from John W. Nicholson)"
    },
    {
     "field": "Xref",
     "code": "%Y",
     "action": "add",
     "add": [
      [
       "A107578",
       "index of the upper prime"
      ]
     ],
     "optional": true
    }
   ],
   "uploads": [
    {
     "kind": "b-file",
     "name": "b005669.txt",
     "replaces": null,
     "slot": 0,
     "rows": 85,
     "published": true,
     "purpose": "The b-file: 85 terms, uploaded with the b-file box ticked. OEIS then rewrites the b-file %H line to credit only you; once saved, the Link card puts the earlier contributors back.",
     "desc": "",
     "content": "# A005669, 85 terms.\n#\n# pi(p) for the prime at the lower end of the n-th maximal gap.\n# From the committed copy of Andersen and Luhn's table; see\n# oeis/andersen-luhn-index.txt, which records how it was checked\n# against the published b-files of A002386, A005250 and A005669.\n#\n# Mike Koss. From Andersen and Luhn's table, retrieved 2026-09-16.\n# Source: https://github.com/mckoss/prime-scanner\n# OEIS data CC BY-SA 4.0\n1 1\n2 2\n3 4\n4 9\n5 24\n6 30\n7 99\n8 154\n9 189\n10 217\n11 1183\n12 1831\n13 2225\n14 3385\n15 14357\n16 30802\n17 31545\n18 40933\n19 103520\n20 104071\n21 149689\n22 325852\n23 1094421\n24 1319945\n25 2850174\n26 6957876\n27 10539432\n28 10655462\n29 20684332\n30 23163298\n31 64955634\n32 72507380\n33 112228683\n34 182837804\n35 203615628\n36 486570087\n37 910774004\n38 981765347\n39 1094330259\n40 1820471368\n41 5217031687\n42 7322882472\n43 9583057667\n44 11723859927\n45 11945986786\n46 11992433550\n47 16202238656\n48 17883926781\n49 23541455083\n50 28106444830\n51 50070452577\n52 52302956123\n53 72178455400\n54 94906079600\n55 251265078335\n56 473258870471\n57 662221289043\n58 1411461642343\n59 2921439731020\n60 5394763455325\n61 6822667965940\n62 35315870460455\n63 49573167413483\n64 49749629143526\n65 1175661926421598\n66 1475067052906945\n67 2133658100875638\n68 5253374014230870\n69 5605544222945291\n70 7784313111002702\n71 8952449214971382\n72 10160960128667332\n73 10570355884548334\n74 20004097201301079\n75 34952141021660495\n76 135962332505694894\n77 160332893561542066\n78 360701908268316580\n79 408333670434942092\n80 423731791997205041\n81 426181820436140029\n82 428472240920394477\n83 477141032543986017\n84 1524717378371224128\n85 2251483061895611799\n"
    }
   ]
  },
  {
   "aid": "A023187",
   "role": "distance to the nearer neighbour",
   "what": "b-file +5 terms (56 to 61)",
   "items": [
    "b-file:A023187"
   ],
   "summary": "Extend the b-file to 61 terms.",
   "blocked_on": null,
   "slot": "waits",
   "edits": [
    {
     "field": "Link",
     "code": "%H",
     "action": "credit_bfile_link",
     "text": "Mike Koss, <a href=\"/A023187/b023187_k.txt\">Table of n, a(n) for n = 1..61</a> (terms 1..56 from David W. Wilson, Jud McCranie, T. D. Noe and Dmitry Petukhov)"
    }
   ],
   "uploads": [
    {
     "kind": "b-file",
     "name": "b023187.txt",
     "replaces": null,
     "slot": 0,
     "rows": 61,
     "published": false,
     "purpose": "The b-file: 61 terms, uploaded with the b-file box ticked. OEIS then rewrites the b-file %H line to credit only you; once saved, the Link card puts the earlier contributors back.",
     "desc": "",
     "content": "# A023187, 61 terms.\n#\n# Terms 1..56 from David W. Wilson, Jud McCranie, T. D. Noe and Dmitry Petukhov.\n# Terms 57..61 are new.\n# Every term independently rederived by an exhaustive scan from 0,\n# as column 3 of its lonely records.\n#\n# Mike Koss. Data as of 2026-10-13, when the scan last advanced.\n# Searched all below 26,306,285,568,359,759: every record up to that\n# bound is present, and there is no further one below it.\n# Independently confirmed by an exhaustive scan; check_oeis.py passes.\n# Source: https://github.com/mckoss/prime-scanner\n# OEIS data CC BY-SA 4.0\n1 1\n2 2\n3 4\n4 6\n5 12\n6 14\n7 18\n8 20\n9 24\n10 30\n11 40\n12 42\n13 44\n14 48\n15 54\n16 62\n17 72\n18 76\n19 96\n20 98\n21 108\n22 116\n23 124\n24 136\n25 156\n26 160\n27 162\n28 168\n29 174\n30 176\n31 178\n32 180\n33 186\n34 194\n35 210\n36 214\n37 222\n38 242\n39 244\n40 246\n41 250\n42 258\n43 268\n44 284\n45 300\n46 324\n47 328\n48 340\n49 348\n50 352\n51 390\n52 396\n53 420\n54 432\n55 452\n56 480\n57 508\n58 510\n59 520\n60 546\n61 550\n"
    }
   ]
  },
  {
   "aid": "A107578",
   "role": "index of the upper prime",
   "what": "b-file +5 terms (80 to 85)",
   "items": [
    "b-file:A107578"
   ],
   "summary": "Extend the b-file to 85 terms.",
   "blocked_on": null,
   "slot": "waits",
   "edits": [
    {
     "field": "Link",
     "code": "%H",
     "action": "credit_bfile_link",
     "text": "Mike Koss, <a href=\"/A107578/b107578_k.txt\">Table of n, a(n) for n = 1..85</a> (terms 1..80 from John W. Nicholson; terms 1..75 from Jens Kruse Andersen; further terms coming from Thomas R. Nicely site)"
    }
   ],
   "uploads": [
    {
     "kind": "b-file",
     "name": "b107578.txt",
     "replaces": null,
     "slot": 0,
     "rows": 85,
     "published": true,
     "purpose": "The b-file: 85 terms, uploaded with the b-file box ticked. OEIS then rewrites the b-file %H line to credit only you; once saved, the Link card puts the earlier contributors back.",
     "desc": "",
     "content": "# A107578, 85 terms.\n#\n# pi(q) for the prime at the upper end of the n-th maximal gap.\n# A107578(n) = A005669(n) + 1, which holds at all 80 terms both\n# sequences publish today.\n#\n# Mike Koss. From Andersen and Luhn's table, retrieved 2026-09-16.\n# Source: https://github.com/mckoss/prime-scanner\n# OEIS data CC BY-SA 4.0\n1 2\n2 3\n3 5\n4 10\n5 25\n6 31\n7 100\n8 155\n9 190\n10 218\n11 1184\n12 1832\n13 2226\n14 3386\n15 14358\n16 30803\n17 31546\n18 40934\n19 103521\n20 104072\n21 149690\n22 325853\n23 1094422\n24 1319946\n25 2850175\n26 6957877\n27 10539433\n28 10655463\n29 20684333\n30 23163299\n31 64955635\n32 72507381\n33 112228684\n34 182837805\n35 203615629\n36 486570088\n37 910774005\n38 981765348\n39 1094330260\n40 1820471369\n41 5217031688\n42 7322882473\n43 9583057668\n44 11723859928\n45 11945986787\n46 11992433551\n47 16202238657\n48 17883926782\n49 23541455084\n50 28106444831\n51 50070452578\n52 52302956124\n53 72178455401\n54 94906079601\n55 251265078336\n56 473258870472\n57 662221289044\n58 1411461642344\n59 2921439731021\n60 5394763455326\n61 6822667965941\n62 35315870460456\n63 49573167413484\n64 49749629143527\n65 1175661926421599\n66 1475067052906946\n67 2133658100875639\n68 5253374014230871\n69 5605544222945292\n70 7784313111002703\n71 8952449214971383\n72 10160960128667333\n73 10570355884548335\n74 20004097201301080\n75 34952141021660496\n76 135962332505694895\n77 160332893561542067\n78 360701908268316581\n79 408333670434942093\n80 423731791997205042\n81 426181820436140030\n82 428472240920394478\n83 477141032543986018\n84 1524717378371224129\n85 2251483061895611800\n"
    }
   ]
  },
  {
   "aid": "A000101",
   "role": "prime at the upper end",
   "what": "Xref +A053695 (optional)",
   "items": [
    "xref:A000101:A053695"
   ],
   "summary": "Optionally add the reverse cross-reference.",
   "blocked_on": null,
   "slot": "waits",
   "edits": [
    {
     "field": "Xref",
     "code": "%Y",
     "action": "add",
     "add": [
      [
       "A053695",
       "successive record-gap differences"
      ]
     ],
     "optional": true
    }
   ],
   "uploads": []
  },
  {
   "aid": "A002386",
   "role": "prime at the lower end",
   "what": "Xref +A053695 (optional), Xref +A087770 (optional), Xref +A107578 (optional)",
   "items": [
    "xref:A002386:A053695",
    "xref:A002386:A087770",
    "xref:A002386:A107578"
   ],
   "summary": "Optionally add cross-references to A053695, A087770, A107578.",
   "blocked_on": null,
   "slot": "waits",
   "edits": [
    {
     "field": "Xref",
     "code": "%Y",
     "action": "add",
     "add": [
      [
       "A053695",
       "successive record-gap differences"
      ],
      [
       "A087770",
       "the pairwise lonely prime"
      ],
      [
       "A107578",
       "index of the upper prime"
      ]
     ],
     "optional": true
    }
   ],
   "uploads": []
  },
  {
   "aid": "A023186",
   "role": "the lonely prime",
   "what": "Xref +A087770 (optional), Xref +A096265 (optional), a-file 61 rows (minor update of a023186_1.txt)",
   "items": [
    "xref:A023186:A087770",
    "xref:A023186:A096265",
    "a-file:update:lonely"
   ],
   "summary": "Optionally add cross-references to A087770, A096265; add an a-file with the bounding primes.",
   "blocked_on": null,
   "slot": "waits",
   "edits": [
    {
     "field": "Xref",
     "code": "%Y",
     "action": "add",
     "add": [
      [
       "A087770",
       "the pairwise lonely prime"
      ],
      [
       "A096265",
       "the aloof prime"
      ]
     ],
     "optional": true
    },
    {
     "field": "Link",
     "code": "%H",
     "action": "remove",
     "find": "href=\"/A023186/a023186_1.txt\""
    }
   ],
   "uploads": [
    {
     "kind": "a-file",
     "name": "a023186.txt",
     "replaces": "a023186_1.txt",
     "slot": 0,
     "rows": 61,
     "published": false,
     "purpose": "The a-file update: 61 rows, replacing a023186_1.txt. Its link text fills the upload box, so OEIS writes the new %H line itself; the Link card drops the old one.",
     "desc": "Mike Koss, <a>Table of the first 61 records with both bounding primes and both gaps</a>",
     "content": "# a023186.txt -- lonely prime records with bounding primes\n#\n# n    index\n# p    the lonely prime (A023186)\n# d    min(p-pp, np-p), the record (A023187)\n# pp   previous prime\n# np   next prime\n# -    none: p = 2 has no previous prime\n#\n# Mike Koss. Data as of 2026-10-13, when the scan last advanced.\n# Searched all below 26,306,285,568,359,759: every record up to that\n# bound is present, and there is no further one below it.\n# Independently confirmed by an exhaustive scan; check_oeis.py passes.\n# Source: https://github.com/mckoss/prime-scanner\n# OEIS data CC BY-SA 4.0\n#\n#  n                  p    d                 pp                 np\n   1                  2    1                  -                  3\n   2                  5    2                  3                  7\n   3                 23    4                 19                 29\n   4                 53    6                 47                 59\n   5                211   12                199                223\n   6               1847   14               1831               1861\n   7               2179   18               2161               2203\n   8               3967   20               3947               3989\n   9              16033   24              16007              16057\n  10              24281   30              24251              24317\n  11              38501   40              38461              38543\n  12              58831   42              58789              58889\n  13             203713   44             203669             203761\n  14             206699   48             206651             206749\n  15             413353   54             413299             413411\n  16            1272749   62            1272679            1272811\n  17            2198981   72            2198909            2199061\n  18            5102953   76            5102863            5103029\n  19           10938023   96           10937921           10938119\n  20           12623189   98           12623089           12623287\n  21           72546283  108           72546143           72546391\n  22          142414669  116          142414553          142414859\n  23          162821917  124          162821753          162822041\n  24          163710121  136          163709971          163710257\n  25          325737821  156          325737649          325737977\n  26         1131241763  160         1131241603         1131241933\n  27         1791752797  162         1791752629         1791752959\n  28         3173306951  168         3173306777         3173307119\n  29         4841337887  174         4841337713         4841338063\n  30         6021542119  176         6021541943         6021542299\n  31         6807940367  178         6807940189         6807940567\n  32         7174208683  180         7174208477         7174208863\n  33         8835528511  186         8835528307         8835528697\n  34        11179888193  194        11179887967        11179888387\n  35        15318488291  210        15318488071        15318488501\n  36        26329105043  214        26329104829        26329105267\n  37        31587561361  222        31587561139        31587561641\n  38        45241670743  242        45241670501        45241670987\n  39       113482615613  244       113482615369       113482615867\n  40       138465682247  246       138465682001       138465682513\n  41       307608752579  250       307608752329       307608752833\n  42       313455525683  258       313455525373       313455525941\n  43       343834606051  268       343834605773       343834606319\n  44       491856414677  284       491856414391       491856414961\n  45      1362810282439  300      1362810282139      1362810282781\n  46      1480975873513  324      1480975873189      1480975873847\n  47      5551890283531  328      5551890283183      5551890283859\n  48      9156364643509  340      9156364643137      9156364643849\n  49     16303344721399  348     16303344721051     16303344721777\n  50     25328423597831  352     25328423597479     25328423598209\n  51     26923643849953  390     26923643849563     26923643850343\n  52     92299530249323  396     92299530248927     92299530249733\n  53    187891466722913  420    187891466722493    187891466723333\n  54    342540487510231  432    342540487509799    342540487510673\n  55    475963705368391  452    475963705367939    475963705368871\n  56    941114429467073  480    941114429466593    941114429467567\n  57   2662972908869401  508   2662972908868891   2662972908869909\n  58   4685407635944059  510   4685407635943549   4685407635944569\n  59   4911417538051463  520   4911417538050943   4911417538052029\n  60  10991084454046573  546  10991084454046027  10991084454047143\n  61  23771684406473771  550  23771684406473221  23771684406474373\n"
    }
   ]
  }
 ]
};
