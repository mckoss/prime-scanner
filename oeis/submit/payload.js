window.OEIS_SUBMIT = {
 "meta": {
  "date": "2026-10-06",
  "run": "fresh",
  "frontier": 26099160246699733,
  "check": true,
  "check_note": ""
 },
 "drafts": [
  {
   "aid": "A000101",
   "role": "prime at the upper end",
   "what": "Xref +A053695",
   "summary": "Add the reverse cross-reference.",
   "blocked_on": null,
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
     ]
    }
   ],
   "uploads": []
  },
  {
   "aid": "A002386",
   "role": "prime at the lower end",
   "what": "Xref +A053695, Xref +A087770, Xref +A107578",
   "summary": "Add cross-references to A053695, A087770, A107578.",
   "blocked_on": null,
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
     ]
    }
   ],
   "uploads": []
  },
  {
   "aid": "A005250",
   "role": "the gap size",
   "what": "a-file 85 rows (update)",
   "summary": "Update the existing a-file to 85 rows; its link text is unchanged.",
   "blocked_on": [
    "open OEIS draft (rev 277, proposed; supplementary-table extension. A107578 was not edited.)"
   ],
   "edits": [],
   "uploads": [
    {
     "kind": "a-file",
     "name": "a005250.txt",
     "slot": 0,
     "rows": 85,
     "published": true,
     "purpose": "The a-file: 85 rows, each record with its bounding primes and gaps. Replaces the file the existing %H line already links.",
     "desc": "",
     "content": "Table from Alex Beveridge, Apr 18 2007.\n\nUpdated by Jens Kruse Andersen, Oct 19 2010.\n\nCorrected OEIS list title by John W. Nicholson, Sep 11, 2011.\n\nUpdated by Mike Koss, 2026-09-16, to 85 rows, from Andersen and\nLuhn's table at https://www.pzktupel.de/RecordGaps/risinggap.php\n\nMaximal prime gaps table with gap number, upper prime, gap, prime count of upper prime.\n\n\n  # = A000027\n  p = upper prime A000101\ngap = difference between p and previous prime A005250\n  G = index of upper prime A107578\n\nA000027 A000101 A005250 A107578\n# p gap G\n1 3 1 2\n2 5 2 3\n3 11 4 5\n4 29 6 10\n5 97 8 25\n6 127 14 31\n7 541 18 100\n8 907 20 155\n9 1151 22 190\n10 1361 34 218\n11 9587 36 1184\n12 15727 44 1832\n13 19661 52 2226\n14 31469 72 3386\n15 156007 86 14358\n16 360749 96 30803\n17 370373 112 31546\n18 492227 114 40934\n19 1349651 118 103521\n20 1357333 132 104072\n21 2010881 148 149690\n22 4652507 154 325853\n23 17051887 180 1094422\n24 20831533 210 1319946\n25 47326913 220 2850175\n26 122164969 222 6957877\n27 189695893 234 10539433\n28 191913031 248 10655463\n29 387096383 250 20684333\n30 436273291 282 23163299\n31 1294268779 288 64955635\n32 1453168433 292 72507381\n33 2300942869 320 112228684\n34 3842611109 336 182837805\n35 4302407713 354 203615629\n36 10726905041 382 486570088\n37 20678048681 384 910774005\n38 22367085353 394 981765348\n39 25056082543 456 1094330260\n40 42652618807 464 1820471369\n41 127976335139 468 5217031688\n42 182226896713 474 7322882473\n43 241160624629 486 9583057668\n44 297501076289 490 11723859928\n45 303371455741 500 11945986787\n46 304599509051 514 11992433551\n47 416608696337 516 16202238657\n48 461690510543 532 17883926782\n49 614487454057 534 23541455084\n50 738832928467 540 28106444831\n51 1346294311331 582 50070452578\n52 1408695494197 588 52302956124\n53 1968188557063 602 72178455401\n54 2614941711251 652 94906079601\n55 7177162612387 674 251265078336\n56 13829048560417 716 473258870472\n57 19581334193189 766 662221289044\n58 42842283926129 778 1411461642344\n59 90874329412297 804 2921439731021\n60 171231342421327 806 5394763455326\n61 218209405437449 906 6822667965941\n62 1189459969826399 916 35315870460456\n63 1686994940956727 924 49573167413484\n64 1693182318747503 1132 49749629143527\n65 43841547845542243 1184 1175661926421599\n66 55350776431904441 1198 1475067052906946\n67 80873624627236069 1220 2133658100875639\n68 203986478517457213 1224 5253374014230871\n69 218034721194215521 1248 5605544222945292\n70 305405826521089141 1272 7784313111002703\n71 352521223451365651 1328 8952449214971383\n72 401429925999155063 1356 10160960128667333\n73 418032645936713497 1370 10570355884548335\n74 804212830686679111 1442 20004097201301080\n75 1425172824437700887 1476 34952141021660496\n76 5733241593241198219 1488 135962332505694895\n77 6787988999657779307 1510 160332893561542067\n78 15570628755536097769 1526 360701908268316581\n79 17678654157568190587 1530 408333670434942093\n80 18361375334787048247 1550 423731791997205042\n81 18470057946260699783 1552 426181820436140030\n82 18571673432051831671 1572 428472240920394478\n83 20733746510561444539 1676 477141032543986018\n84 68068810283234184631 1724 1524717378371224129\n85 101412319996363310923 1854 2251483061895611800\n\nNotes:\n\nTo get lower prime subtract gap from p.\nTo get prime count of lower prime subtract 1 from the last column.\n"
    }
   ]
  },
  {
   "aid": "A005669",
   "role": "index of the lower prime",
   "what": "b-file 85 terms, Xref +A107578",
   "summary": "Extend the b-file to 85 terms; add cross-references to A107578.",
   "blocked_on": null,
   "edits": [
    {
     "field": "Xref",
     "code": "%Y",
     "action": "add",
     "add": [
      [
       "A107578",
       "index of the upper prime"
      ]
     ]
    }
   ],
   "uploads": [
    {
     "kind": "b-file",
     "name": "b005669.txt",
     "slot": 0,
     "rows": 85,
     "published": true,
     "purpose": "The b-file: 85 terms, uploaded with the b-file box ticked. OEIS then rewrites the b-file %H line itself; after saving, check it reads n = 1..85.",
     "desc": "",
     "content": "# A005669, 85 terms.\n#\n# pi(p) for the prime at the lower end of the n-th maximal gap.\n# From the committed copy of Andersen and Luhn's table; see\n# oeis/andersen-luhn-index.txt, which records how it was checked\n# against the published b-files of A002386, A005250 and A005669.\n#\n# Mike Koss. From Andersen and Luhn's table, retrieved 2026-09-16.\n# Source: https://github.com/mckoss/prime-scanner\n# OEIS data CC BY-SA 4.0\n1 1\n2 2\n3 4\n4 9\n5 24\n6 30\n7 99\n8 154\n9 189\n10 217\n11 1183\n12 1831\n13 2225\n14 3385\n15 14357\n16 30802\n17 31545\n18 40933\n19 103520\n20 104071\n21 149689\n22 325852\n23 1094421\n24 1319945\n25 2850174\n26 6957876\n27 10539432\n28 10655462\n29 20684332\n30 23163298\n31 64955634\n32 72507380\n33 112228683\n34 182837804\n35 203615628\n36 486570087\n37 910774004\n38 981765347\n39 1094330259\n40 1820471368\n41 5217031687\n42 7322882472\n43 9583057667\n44 11723859927\n45 11945986786\n46 11992433550\n47 16202238656\n48 17883926781\n49 23541455083\n50 28106444830\n51 50070452577\n52 52302956123\n53 72178455400\n54 94906079600\n55 251265078335\n56 473258870471\n57 662221289043\n58 1411461642343\n59 2921439731020\n60 5394763455325\n61 6822667965940\n62 35315870460455\n63 49573167413483\n64 49749629143526\n65 1175661926421598\n66 1475067052906945\n67 2133658100875638\n68 5253374014230870\n69 5605544222945291\n70 7784313111002702\n71 8952449214971382\n72 10160960128667332\n73 10570355884548334\n74 20004097201301079\n75 34952141021660495\n76 135962332505694894\n77 160332893561542066\n78 360701908268316580\n79 408333670434942092\n80 423731791997205041\n81 426181820436140029\n82 428472240920394477\n83 477141032543986017\n84 1524717378371224128\n85 2251483061895611799\n"
    }
   ]
  },
  {
   "aid": "A023186",
   "role": "the lonely prime",
   "what": "b-file 61 terms, bound comment, a-file 60 rows, Xref +A087770, Xref +A096265",
   "summary": "Extend the b-file to 61 terms; add a search-bound comment; add an a-file with the bounding primes; add cross-references to A087770, A096265.",
   "blocked_on": null,
   "edits": [
    {
     "field": "Ext",
     "code": "%E",
     "action": "add",
     "text": "a(57)-a(61) from ~~~~"
    },
    {
     "field": "Comment",
     "code": "%C",
     "action": "add",
     "text": "There is no further term below 2.6*10^16: an exhaustive scan from 0 to 26099160246699733 finds none. - ~~~~"
    },
    {
     "field": "Link",
     "code": "%H",
     "action": "add",
     "text": "Mike Koss, <a href=\"/A023186/a023186.txt\">Table of the first 60 records with both bounding primes and both gaps</a>"
    },
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
     ]
    }
   ],
   "uploads": [
    {
     "kind": "b-file",
     "name": "b023186.txt",
     "slot": 0,
     "rows": 61,
     "published": true,
     "purpose": "The b-file: 61 terms, uploaded with the b-file box ticked. OEIS then rewrites the b-file %H line itself; after saving, check it reads n = 1..61.",
     "desc": "",
     "content": "# A023186, 61 terms.\n#\n# Terms 1..56 from Dmitry Petukhov (first 40 terms from Ken Takusagawa, terms 41..52 from Giovanni Resta).\n# Terms 57..61 are new.\n# Every term independently rederived by an exhaustive scan from 0.\n#\n# Mike Koss. Data as of 2026-10-06, when the scan last advanced.\n# Searched all below 26,099,160,246,699,733: every record up to that\n# bound is present, and there is no further one below it.\n# Independently confirmed by an exhaustive scan; check_oeis.py passes.\n# Source: https://github.com/mckoss/prime-scanner\n# OEIS data CC BY-SA 4.0\n1 2\n2 5\n3 23\n4 53\n5 211\n6 1847\n7 2179\n8 3967\n9 16033\n10 24281\n11 38501\n12 58831\n13 203713\n14 206699\n15 413353\n16 1272749\n17 2198981\n18 5102953\n19 10938023\n20 12623189\n21 72546283\n22 142414669\n23 162821917\n24 163710121\n25 325737821\n26 1131241763\n27 1791752797\n28 3173306951\n29 4841337887\n30 6021542119\n31 6807940367\n32 7174208683\n33 8835528511\n34 11179888193\n35 15318488291\n36 26329105043\n37 31587561361\n38 45241670743\n39 113482615613\n40 138465682247\n41 307608752579\n42 313455525683\n43 343834606051\n44 491856414677\n45 1362810282439\n46 1480975873513\n47 5551890283531\n48 9156364643509\n49 16303344721399\n50 25328423597831\n51 26923643849953\n52 92299530249323\n53 187891466722913\n54 342540487510231\n55 475963705368391\n56 941114429467073\n57 2662972908869401\n58 4685407635944059\n59 4911417538051463\n60 10991084454046573\n61 23771684406473771\n"
    },
    {
     "kind": "a-file",
     "name": "a023186.txt",
     "slot": 1,
     "rows": 60,
     "published": false,
     "purpose": "The a-file: 60 rows, each record with its bounding primes and gaps. A new %H line links it as a023186.txt; if OEIS stores it under another name, such as a023186_1.txt, make the link match.",
     "desc": "",
     "content": "# a023186.txt -- lonely prime records with bounding primes\n#\n# n    index\n# p    the lonely prime (A023186)\n# d    min(p-pp, np-p), the record (A023187)\n# pp   previous prime\n# np   next prime\n#\n# Mike Koss. Data as of 2026-10-06, when the scan last advanced.\n# Searched all below 26,099,160,246,699,733: every record up to that\n# bound is present, and there is no further one below it.\n# Independently confirmed by an exhaustive scan; check_oeis.py passes.\n# Source: https://github.com/mckoss/prime-scanner\n# OEIS data CC BY-SA 4.0\n#\n#  n                  p    d                 pp                 np\n   2                  5    2                  3                  7\n   3                 23    4                 19                 29\n   4                 53    6                 47                 59\n   5                211   12                199                223\n   6               1847   14               1831               1861\n   7               2179   18               2161               2203\n   8               3967   20               3947               3989\n   9              16033   24              16007              16057\n  10              24281   30              24251              24317\n  11              38501   40              38461              38543\n  12              58831   42              58789              58889\n  13             203713   44             203669             203761\n  14             206699   48             206651             206749\n  15             413353   54             413299             413411\n  16            1272749   62            1272679            1272811\n  17            2198981   72            2198909            2199061\n  18            5102953   76            5102863            5103029\n  19           10938023   96           10937921           10938119\n  20           12623189   98           12623089           12623287\n  21           72546283  108           72546143           72546391\n  22          142414669  116          142414553          142414859\n  23          162821917  124          162821753          162822041\n  24          163710121  136          163709971          163710257\n  25          325737821  156          325737649          325737977\n  26         1131241763  160         1131241603         1131241933\n  27         1791752797  162         1791752629         1791752959\n  28         3173306951  168         3173306777         3173307119\n  29         4841337887  174         4841337713         4841338063\n  30         6021542119  176         6021541943         6021542299\n  31         6807940367  178         6807940189         6807940567\n  32         7174208683  180         7174208477         7174208863\n  33         8835528511  186         8835528307         8835528697\n  34        11179888193  194        11179887967        11179888387\n  35        15318488291  210        15318488071        15318488501\n  36        26329105043  214        26329104829        26329105267\n  37        31587561361  222        31587561139        31587561641\n  38        45241670743  242        45241670501        45241670987\n  39       113482615613  244       113482615369       113482615867\n  40       138465682247  246       138465682001       138465682513\n  41       307608752579  250       307608752329       307608752833\n  42       313455525683  258       313455525373       313455525941\n  43       343834606051  268       343834605773       343834606319\n  44       491856414677  284       491856414391       491856414961\n  45      1362810282439  300      1362810282139      1362810282781\n  46      1480975873513  324      1480975873189      1480975873847\n  47      5551890283531  328      5551890283183      5551890283859\n  48      9156364643509  340      9156364643137      9156364643849\n  49     16303344721399  348     16303344721051     16303344721777\n  50     25328423597831  352     25328423597479     25328423598209\n  51     26923643849953  390     26923643849563     26923643850343\n  52     92299530249323  396     92299530248927     92299530249733\n  53    187891466722913  420    187891466722493    187891466723333\n  54    342540487510231  432    342540487509799    342540487510673\n  55    475963705368391  452    475963705367939    475963705368871\n  56    941114429467073  480    941114429466593    941114429467567\n  57   2662972908869401  508   2662972908868891   2662972908869909\n  58   4685407635944059  510   4685407635943549   4685407635944569\n  59   4911417538051463  520   4911417538050943   4911417538052029\n  60  10991084454046573  546  10991084454046027  10991084454047143\n  61  23771684406473771  550  23771684406473221  23771684406474373\n"
    }
   ]
  },
  {
   "aid": "A031132",
   "role": "the span between them",
   "what": "Xref +A096265",
   "summary": "Add the reverse cross-reference.",
   "blocked_on": null,
   "edits": [
    {
     "field": "Xref",
     "code": "%Y",
     "action": "add",
     "add": [
      [
       "A096265",
       "the aloof prime"
      ]
     ]
    }
   ],
   "uploads": []
  },
  {
   "aid": "A031133",
   "role": "the lower neighbour",
   "what": "bound comment",
   "summary": "Add a search-bound comment: no further term below 2.6*10^16.",
   "blocked_on": null,
   "edits": [
    {
     "field": "Comment",
     "code": "%C",
     "action": "add",
     "text": "There is no further term below 2.6*10^16: an exhaustive scan from 0 to 26099160246699733 finds none. - ~~~~"
    }
   ],
   "uploads": []
  },
  {
   "aid": "A031134",
   "role": "the upper neighbour",
   "what": "bound comment",
   "summary": "Add a search-bound comment: no further term below 2.6*10^16.",
   "blocked_on": null,
   "edits": [
    {
     "field": "Comment",
     "code": "%C",
     "action": "add",
     "text": "There is no further term below 2.6*10^16: an exhaustive scan from 0 to 26099160246699733 finds none. - ~~~~"
    }
   ],
   "uploads": []
  },
  {
   "aid": "A058867",
   "role": "the balanced prime",
   "what": "b-file 34 terms, bound comment, a-file 34 rows",
   "summary": "Extend the b-file to 34 terms; credit the prior A052187 table; add a search-bound comment; add an a-file with the bounding primes.",
   "blocked_on": null,
   "edits": [
    {
     "field": "Ext",
     "code": "%E",
     "action": "add",
     "text": "a(31) = A052187(72) + 426; the prime triple was already tabulated in A052187 (table credited to Jerry M. Lagrou and earlier contributors), and is independently confirmed by this scan. ~~~~"
    },
    {
     "field": "Ext",
     "code": "%E",
     "action": "add",
     "text": "a(32) from ~~~~"
    },
    {
     "field": "Ext",
     "code": "%E",
     "action": "add",
     "text": "a(33) from ~~~~"
    },
    {
     "field": "Ext",
     "code": "%E",
     "action": "add",
     "text": "a(34) from ~~~~"
    },
    {
     "field": "Link",
     "code": "%H",
     "action": "add",
     "text": "Jerry M. Lagrou and earlier contributors, <a href=\"/A052187/b052187.txt\">First-occurrence balanced prime triples (lower endpoints)</a>."
    },
    {
     "field": "Comment",
     "code": "%C",
     "action": "add",
     "text": "There is no further term below 2.6*10^16: an exhaustive scan from 0 to 26099160246699733 finds none. - ~~~~"
    },
    {
     "field": "Link",
     "code": "%H",
     "action": "add",
     "text": "Mike Koss, <a href=\"/A058867/a058867.txt\">Table of the first 34 records with both bounding primes and both gaps</a>"
    }
   ],
   "uploads": [
    {
     "kind": "b-file",
     "name": "b058867.txt",
     "slot": 0,
     "rows": 34,
     "published": false,
     "purpose": "The b-file: 34 terms, uploaded with the b-file box ticked. OEIS then rewrites the b-file %H line itself; after saving, check it reads n = 1..34.",
     "desc": "",
     "content": "# A058867, 34 terms.\n#\n# Terms 1..30 as previously published.\n# Terms 31..34 are new.\n# Every term independently rederived by an exhaustive scan from 0.\n#\n# Mike Koss. Data as of 2026-10-06, when the scan last advanced.\n# Searched all below 26,099,160,246,699,733: every record up to that\n# bound is present, and there is no further one below it.\n# Independently confirmed by an exhaustive scan; check_oeis.py passes.\n# Source: https://github.com/mckoss/prime-scanner\n# OEIS data CC BY-SA 4.0\n1 5\n2 53\n3 211\n4 16787\n5 69623\n6 247141\n7 3565979\n8 4911311\n9 12012743\n10 23346809\n11 34346287\n12 36598607\n13 51042053\n14 383204683\n15 4470608101\n16 5007182863\n17 5558570491\n18 48287689717\n19 50284155289\n20 178796541817\n21 264860525507\n22 374787490919\n23 1521870804107\n24 2093308790851\n25 4228611064537\n26 6537587646671\n27 17432065861517\n28 22546768250359\n29 26923643849953\n30 187891466722913\n31 2422627449334097\n32 2848704456458411\n33 3955678819752329\n34 4685407635944059\n"
    },
    {
     "kind": "a-file",
     "name": "a058867.txt",
     "slot": 1,
     "rows": 34,
     "published": false,
     "purpose": "The a-file: 34 rows, each record with its bounding primes and gaps. A new %H line links it as a058867.txt; if OEIS stores it under another name, such as a058867_1.txt, make the link match.",
     "desc": "",
     "content": "# a058867.txt -- equidistant prime records with bounding primes\n#\n# n    index\n# p    the balanced prime (A058867)\n# d    p - pp = np - p, the record (A058868)\n# pp   previous prime\n# np   next prime\n#\n# Mike Koss. Data as of 2026-10-06, when the scan last advanced.\n# Searched all below 26,099,160,246,699,733: every record up to that\n# bound is present, and there is no further one below it.\n# Independently confirmed by an exhaustive scan; check_oeis.py passes.\n# Source: https://github.com/mckoss/prime-scanner\n# OEIS data CC BY-SA 4.0\n#\n#  n                 p    d                pp                np\n   1                 5    2                 3                 7\n   2                53    6                47                59\n   3               211   12               199               223\n   4             16787   24             16763             16811\n   5             69623   30             69593             69653\n   6            247141   42            247099            247183\n   7           3565979   48           3565931           3566027\n   8           4911311   60           4911251           4911371\n   9          12012743   66          12012677          12012809\n  10          23346809   72          23346737          23346881\n  11          34346287   84          34346203          34346371\n  12          36598607   90          36598517          36598697\n  13          51042053   96          51041957          51042149\n  14         383204683  144         383204539         383204827\n  15        4470608101  150        4470607951        4470608251\n  16        5007182863  156        5007182707        5007183019\n  17        5558570491  168        5558570323        5558570659\n  18       48287689717  186       48287689531       48287689903\n  19       50284155289  198       50284155091       50284155487\n  20      178796541817  204      178796541613      178796542021\n  21      264860525507  210      264860525297      264860525717\n  22      374787490919  228      374787490691      374787491147\n  23     1521870804107  240     1521870803867     1521870804347\n  24     2093308790851  258     2093308790593     2093308791109\n  25     4228611064537  276     4228611064261     4228611064813\n  26     6537587646671  300     6537587646371     6537587646971\n  27    17432065861517  306    17432065861211    17432065861823\n  28    22546768250359  348    22546768250011    22546768250707\n  29    26923643849953  390    26923643849563    26923643850343\n  30   187891466722913  420   187891466722493   187891466723333\n  31  2422627449334097  426  2422627449333671  2422627449334523\n  32  2848704456458411  438  2848704456457973  2848704456458849\n  33  3955678819752329  468  3955678819751861  3955678819752797\n  34  4685407635944059  510  4685407635943549  4685407635944569\n# Prior published triples: https://oeis.org/A052187/b052187.txt\n# Table credited to Jerry M. Lagrou and earlier contributors;\n# these triples were independently rederived by this scan.\n# a(1) = A052187(1) + 2.\n# a(2) = A052187(2) + 6.\n# a(3) = A052187(3) + 12.\n# a(4) = A052187(5) + 24.\n# a(5) = A052187(6) + 30.\n# a(6) = A052187(8) + 42.\n# a(7) = A052187(9) + 48.\n# a(8) = A052187(11) + 60.\n# a(9) = A052187(12) + 66.\n# a(10) = A052187(13) + 72.\n# a(11) = A052187(15) + 84.\n# a(12) = A052187(16) + 90.\n# a(13) = A052187(17) + 96.\n# a(14) = A052187(25) + 144.\n# a(15) = A052187(26) + 150.\n# a(16) = A052187(27) + 156.\n# a(17) = A052187(29) + 168.\n# a(18) = A052187(32) + 186.\n# a(19) = A052187(34) + 198.\n# a(20) = A052187(35) + 204.\n# a(21) = A052187(36) + 210.\n# a(22) = A052187(39) + 228.\n# a(23) = A052187(41) + 240.\n# a(24) = A052187(44) + 258.\n# a(25) = A052187(47) + 276.\n# a(26) = A052187(51) + 300.\n# a(27) = A052187(52) + 306.\n# a(28) = A052187(59) + 348.\n# a(29) = A052187(66) + 390.\n# a(30) = A052187(71) + 420.\n# a(31) = A052187(72) + 426.\n"
    }
   ]
  },
  {
   "aid": "A087770",
   "role": "the pairwise lonely prime",
   "what": "b-file 41 terms, bound comment, a-file 40 rows, Xref +A096265",
   "summary": "Extend the b-file to 41 terms; add a search-bound comment; add an a-file with the bounding primes; add cross-references to A096265.",
   "blocked_on": null,
   "edits": [
    {
     "field": "Ext",
     "code": "%E",
     "action": "add",
     "text": "a(30)-a(41) from ~~~~"
    },
    {
     "field": "Comment",
     "code": "%C",
     "action": "add",
     "text": "There is no further term below 2.6*10^16: an exhaustive scan from 0 to 26099160246699733 finds none. - ~~~~"
    },
    {
     "field": "Link",
     "code": "%H",
     "action": "add",
     "text": "Mike Koss, <a href=\"/A087770/a087770.txt\">Table of the first 40 records with both bounding primes and both gaps</a>"
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
     ]
    }
   ],
   "uploads": [
    {
     "kind": "b-file",
     "name": "b087770.txt",
     "slot": 0,
     "rows": 41,
     "published": false,
     "purpose": "The b-file: 41 terms, uploaded with the b-file box ticked. OEIS then rewrites the b-file %H line itself; after saving, check it reads n = 1..41.",
     "desc": "",
     "content": "# A087770, 41 terms.\n#\n# Terms 1..29 as previously published.\n# Terms 30..41 are new.\n# Every term independently rederived by an exhaustive scan from 0.\n#\n# Mike Koss. Data as of 2026-10-06, when the scan last advanced.\n# Searched all below 26,099,160,246,699,733: every record up to that\n# bound is present, and there is no further one below it.\n# Independently confirmed by an exhaustive scan; check_oeis.py passes.\n# Source: https://github.com/mckoss/prime-scanner\n# OEIS data CC BY-SA 4.0\n1 2\n2 3\n3 7\n4 23\n5 89\n6 211\n7 1847\n8 2179\n9 14107\n10 33247\n11 38501\n12 58831\n13 268343\n14 1272749\n15 2198981\n16 10938023\n17 72546283\n18 162821917\n19 325737821\n20 2888688863\n21 6613941601\n22 11179888193\n23 24016237123\n24 96155166493\n25 179474021633\n26 215686840471\n27 633880576177\n28 1480975873513\n29 9156364643509\n30 26459479056379\n31 64293760159177\n32 201355244997631\n33 203521339456733\n34 366981966368659\n35 630279877844621\n36 1244134359040121\n37 1527008871568883\n38 2662972908869401\n39 4911417538051463\n40 10991084454046573\n41 23771684406473771\n"
    },
    {
     "kind": "a-file",
     "name": "a087770.txt",
     "slot": 1,
     "rows": 40,
     "published": false,
     "purpose": "The a-file: 40 rows, each record with its bounding primes and gaps. A new %H line links it as a087770.txt; if OEIS stores it under another name, such as a087770_1.txt, make the link match.",
     "desc": "",
     "content": "# a087770.txt -- pairwise lonely prime records with bounding primes\n#\n# n    index\n# p    the pairwise lonely prime (A087770)\n# gb   p - pp\n# ga   np - p\n# pp   previous prime\n# np   next prime\n#\n# Mike Koss. Data as of 2026-10-06, when the scan last advanced.\n# Searched all below 26,099,160,246,699,733: every record up to that\n# bound is present, and there is no further one below it.\n# Independently confirmed by an exhaustive scan; check_oeis.py passes.\n# Source: https://github.com/mckoss/prime-scanner\n# OEIS data CC BY-SA 4.0\n#\n#  n                  p   gb   ga                 pp                 np\n   2                  3    1    2                  2                  5\n   3                  7    2    4                  5                 11\n   4                 23    4    6                 19                 29\n   5                 89    6    8                 83                 97\n   6                211   12   12                199                223\n   7               1847   16   14               1831               1861\n   8               2179   18   24               2161               2203\n   9              14107   20   36              14087              14143\n  10              33247   24   40              33223              33287\n  11              38501   40   42              38461              38543\n  12              58831   42   58              58789              58889\n  13             268343   46   60             268297             268403\n  14            1272749   70   62            1272679            1272811\n  15            2198981   72   80            2198909            2199061\n  16           10938023  102   96           10937921           10938119\n  17           72546283  140  108           72546143           72546391\n  18          162821917  164  124          162821753          162822041\n  19          325737821  172  156          325737649          325737977\n  20         2888688863  204  158         2888688659         2888689021\n  21         6613941601  224  166         6613941377         6613941767\n  22        11179888193  226  194        11179887967        11179888387\n  23        24016237123  246  196        24016236877        24016237319\n  24        96155166493  272  198        96155166221        96155166691\n  25       179474021633  274  200       179474021359       179474021833\n  26       215686840471  314  232       215686840157       215686840703\n  27       633880576177  318  270       633880575859       633880576447\n  28      1480975873513  324  334      1480975873189      1480975873847\n  29      9156364643509  372  340      9156364643137      9156364643849\n  30     26459479056379  426  348     26459479055953     26459479056727\n  31     64293760159177  434  372     64293760158743     64293760159549\n  32    201355244997631  440  390    201355244997191    201355244998021\n  33    203521339456733  456  398    203521339456277    203521339457131\n  34    366981966368659  458  412    366981966368201    366981966369071\n  35    630279877844621  490  422    630279877844131    630279877845043\n  36   1244134359040121  502  462   1244134359039619   1244134359040583\n  37   1527008871568883  504  470   1527008871568379   1527008871569353\n  38   2662972908869401  510  508   2662972908868891   2662972908869909\n  39   4911417538051463  520  566   4911417538050943   4911417538052029\n  40  10991084454046573  546  570  10991084454046027  10991084454047143\n  41  23771684406473771  550  602  23771684406473221  23771684406474373\n"
    }
   ]
  },
  {
   "aid": "A096265",
   "role": "the aloof prime",
   "what": "b-file 72 terms, bound comment, a-file 71 rows, Xref +A031133, Xref +A031134, Xref +A122412, Xref +A122413",
   "summary": "Extend the b-file to 72 terms; add a search-bound comment; add an a-file with the bounding primes; add cross-references to A031133, A031134, A122412, A122413.",
   "blocked_on": null,
   "edits": [
    {
     "field": "Ext",
     "code": "%E",
     "action": "add",
     "text": "a(57)-a(72) from ~~~~"
    },
    {
     "field": "Comment",
     "code": "%C",
     "action": "add",
     "text": "There is no further term below 2.6*10^16: an exhaustive scan from 0 to 26099160246699733 finds none. - ~~~~"
    },
    {
     "field": "Link",
     "code": "%H",
     "action": "add",
     "text": "Mike Koss, <a href=\"/A096265/a096265.txt\">Table of the first 71 records with both bounding primes and both gaps</a>"
    },
    {
     "field": "Xref",
     "code": "%Y",
     "action": "add",
     "add": [
      [
       "A031133",
       "the lower neighbour"
      ],
      [
       "A031134",
       "the upper neighbour"
      ],
      [
       "A122412",
       "index of the lower prime"
      ],
      [
       "A122413",
       "index of the upper prime"
      ]
     ]
    }
   ],
   "uploads": [
    {
     "kind": "b-file",
     "name": "b096265.txt",
     "slot": 0,
     "rows": 72,
     "published": true,
     "purpose": "The b-file: 72 terms, uploaded with the b-file box ticked. OEIS then rewrites the b-file %H line itself; after saving, check it reads n = 1..72.",
     "desc": "",
     "content": "# A096265, 72 terms.\n#\n# Terms 1..55 as previously published.\n# Terms 56..68 are the prime between A031133(k) and A031134(k),\n# whose b-files reach 67 terms (A096265 index 68).\n# Every term independently rederived by an exhaustive scan.\n#\n# Mike Koss. Data as of 2026-10-06, when the scan last advanced.\n# Searched all below 26,099,160,246,699,733: every record up to that\n# bound is present, and there is no further one below it.\n# Independently confirmed by an exhaustive scan; check_oeis.py passes.\n# Source: https://github.com/mckoss/prime-scanner\n# OEIS data CC BY-SA 4.0\n1 2\n2 3\n3 5\n4 7\n5 23\n6 53\n7 89\n8 113\n9 211\n10 1129\n11 1327\n12 2179\n13 2503\n14 5623\n15 9587\n16 14107\n17 19609\n18 19661\n19 31397\n20 31469\n21 38501\n22 58831\n23 155921\n24 360749\n25 370261\n26 396833\n27 1357201\n28 1561919\n29 4652353\n30 8917523\n31 20831323\n32 38089277\n33 70396393\n34 72546283\n35 102765683\n36 142414669\n37 325737821\n38 436273009\n39 476956933\n40 1346350763\n41 1453168141\n42 2949347131\n43 3367207801\n44 9085929179\n45 10726905041\n46 20678048681\n47 25056082087\n48 31587561361\n49 42652618343\n50 50949283459\n51 122787888851\n52 215686840471\n53 220578150113\n54 724200190631\n55 929156727137\n56 1032148488557\n57 3605572653889\n58 4079970755417\n59 5061226833937\n60 12772332382939\n61 19535748743177\n62 21185697626267\n63 117102787055963\n64 471911699384963\n65 528459528876647\n66 543684371469929\n67 811782668945987\n68 1693182318746371\n69 12099132127787501\n70 12568891238650091\n71 14878430907698893\n72 16020873778857163\n"
    },
    {
     "kind": "a-file",
     "name": "a096265.txt",
     "slot": 1,
     "rows": 71,
     "published": false,
     "purpose": "The a-file: 71 rows, each record with its bounding primes and gaps. A new %H line links it as a096265.txt; if OEIS stores it under another name, such as a096265_1.txt, make the link match.",
     "desc": "",
     "content": "# a096265.txt -- aloof prime records with bounding primes\n#\n# n    index\n# p    the aloof prime (A096265)\n# span np - pp, the record (A031132)\n# pp   previous prime (A031133)\n# np   next prime (A031134)\n#\n# Mike Koss. Data as of 2026-10-06, when the scan last advanced.\n# Searched all below 26,099,160,246,699,733: every record up to that\n# bound is present, and there is no further one below it.\n# Independently confirmed by an exhaustive scan; check_oeis.py passes.\n# Source: https://github.com/mckoss/prime-scanner\n# OEIS data CC BY-SA 4.0\n#\n#  n                  p  span                 pp                 np\n   2                  3     3                  2                  5\n   3                  5     4                  3                  7\n   4                  7     6                  5                 11\n   5                 23    10                 19                 29\n   6                 53    12                 47                 59\n   7                 89    14                 83                 97\n   8                113    18                109                127\n   9                211    24                199                223\n  10               1129    28               1123               1151\n  11               1327    40               1321               1361\n  12               2179    42               2161               2203\n  13               2503    44               2477               2521\n  14               5623    48               5591               5639\n  15               9587    50               9551               9601\n  16              14107    56              14087              14143\n  17              19609    58              19603              19661\n  18              19661    72              19609              19681\n  19              31397    76              31393              31469\n  20              31469    80              31397              31477\n  21              38501    82              38461              38543\n  22              58831   100              58789              58889\n  23             155921   114             155893             156007\n  24             360749   116             360653             360769\n  25             370261   126             370247             370373\n  26             396833   138             396733             396871\n  27            1357201   140            1357193            1357333\n  28            1561919   160            1561891            1562051\n  29            4652353   190            4652317            4652507\n  30            8917523   200            8917463            8917663\n  31           20831323   234           20831299           20831533\n  32           38089277   236           38089217           38089453\n  33           70396393   246           70396343           70396589\n  34           72546283   248           72546143           72546391\n  35          102765683   270          102765577          102765847\n  36          142414669   306          142414553          142414859\n  37          325737821   328          325737649          325737977\n  38          436273009   330          436272961          436273291\n  39          476956933   336          476956801          476957137\n  40         1346350763   340         1346350651         1346350991\n  41         1453168141   372         1453168061         1453168433\n  42         2949347131   376         2949346891         2949347267\n  43         3367207801   410         3367207667         3367208077\n  44         9085929179   436         9085929037         9085929473\n  45        10726905041   438        10726904659        10726905097\n  46        20678048681   450        20678048297        20678048747\n  47        25056082087   476        25056082067        25056082543\n  48        31587561361   502        31587561139        31587561641\n  49        42652618343   506        42652618301        42652618807\n  50        50949283459   524        50949283109        50949283633\n  51       122787888851   540       122787888679       122787889219\n  52       215686840471   546       215686840157       215686840703\n  53       220578150113   594       220578149899       220578150493\n  54       724200190631   600       724200190201       724200190801\n  55       929156727137   624       929156727013       929156727637\n  56      1032148488557   678      1032148488143      1032148488821\n  57      3605572653889   690      3605572653481      3605572654171\n  58      4079970755417   700      4079970755221      4079970755921\n  59      5061226833937   760      5061226833427      5061226834187\n  60     12772332382939   780     12772332382321     12772332383101\n  61     19535748743177   838     19535748742639     19535748743477\n  62     21185697626267   900     21185697626083     21185697626983\n  63    117102787055963   944    117102787055687    117102787056631\n  64    471911699384963   972    471911699384771    471911699385743\n  65    528459528876647  1014    528459528876289    528459528877303\n  66    543684371469929  1016    543684371469023    543684371470039\n  67    811782668945987  1032    811782668945159    811782668946191\n  68   1693182318746371  1152   1693182318746351   1693182318747503\n  69  12099132127787501  1168  12099132127786609  12099132127787777\n  70  12568891238650091  1170  12568891238649583  12568891238650753\n  71  14878430907698893  1182  14878430907698447  14878430907699629\n  72  16020873778857163  1220  16020873778856279  16020873778857499\n"
    }
   ]
  },
  {
   "aid": "A107578",
   "role": "index of the upper prime",
   "what": "b-file 85 terms",
   "summary": "Extend the b-file to 85 terms.",
   "blocked_on": null,
   "edits": [],
   "uploads": [
    {
     "kind": "b-file",
     "name": "b107578.txt",
     "slot": 0,
     "rows": 85,
     "published": true,
     "purpose": "The b-file: 85 terms, uploaded with the b-file box ticked. OEIS then rewrites the b-file %H line itself; after saving, check it reads n = 1..85.",
     "desc": "",
     "content": "# A107578, 85 terms.\n#\n# pi(q) for the prime at the upper end of the n-th maximal gap.\n# A107578(n) = A005669(n) + 1, which holds at all 80 terms both\n# sequences publish today.\n#\n# Mike Koss. From Andersen and Luhn's table, retrieved 2026-09-16.\n# Source: https://github.com/mckoss/prime-scanner\n# OEIS data CC BY-SA 4.0\n1 2\n2 3\n3 5\n4 10\n5 25\n6 31\n7 100\n8 155\n9 190\n10 218\n11 1184\n12 1832\n13 2226\n14 3386\n15 14358\n16 30803\n17 31546\n18 40934\n19 103521\n20 104072\n21 149690\n22 325853\n23 1094422\n24 1319946\n25 2850175\n26 6957877\n27 10539433\n28 10655463\n29 20684333\n30 23163299\n31 64955635\n32 72507381\n33 112228684\n34 182837805\n35 203615629\n36 486570088\n37 910774005\n38 981765348\n39 1094330260\n40 1820471369\n41 5217031688\n42 7322882473\n43 9583057668\n44 11723859928\n45 11945986787\n46 11992433551\n47 16202238657\n48 17883926782\n49 23541455084\n50 28106444831\n51 50070452578\n52 52302956124\n53 72178455401\n54 94906079601\n55 251265078336\n56 473258870472\n57 662221289044\n58 1411461642344\n59 2921439731021\n60 5394763455326\n61 6822667965941\n62 35315870460456\n63 49573167413484\n64 49749629143527\n65 1175661926421599\n66 1475067052906946\n67 2133658100875639\n68 5253374014230871\n69 5605544222945292\n70 7784313111002703\n71 8952449214971383\n72 10160960128667333\n73 10570355884548335\n74 20004097201301080\n75 34952141021660496\n76 135962332505694895\n77 160332893561542067\n78 360701908268316581\n79 408333670434942093\n80 423731791997205042\n81 426181820436140030\n82 428472240920394478\n83 477141032543986018\n84 1524717378371224129\n85 2251483061895611800\n"
    }
   ]
  }
 ]
};
