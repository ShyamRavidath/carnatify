# Saraga ASR Trainset Feasibility Report

Generated deterministically from local Saraga metadata, manual section annotations, the composition registry, lyric corpus, and reviewed link overrides. No audio was decoded.

## Feasibility read

**Promising but small.** The set is suitable for a tightly monitored pilot or adapter experiment, not yet a robust general-purpose sung-Carnatic ASR fine-tune. Expand coverage before a large GPU run.

These are weak section-level labels: every ≤30-second window inherits its whole section text. Pallavi/anupallavi windows are marked high; all charanam/verse windows are marked low.

## Headline numbers

| Metric | Count |
|---|---:|
| Total Saraga tracks walked | 249 |
| Kept as fixed-sahitya forms | 173 |
| Excluded by form | 76 |
| Kept tracks matched to local lyrics | 78 |
| Matched tracks with emitted segments | 26 |
| Matched tracks lacking manual sections | 52 |
| Unmatched kept tracks | 95 |
| Unmatched kept tracks with manual sections (highest-value gaps) | 36 |
| Total emitted segments | 354 |

## Aligned audio by confidence

| Confidence | Sections represented | Tracks | Segments | Minutes |
|---|---|---:|---:|---:|
| high | pallavi + anupallavi | 26 | 186 | 80.31 |
| low | charanam / numbered verse | 25 | 168 | 77.21 |
| **total** |  | 26 | 354 | **157.51** |

Duration is the sum of emitted window spans, not track duration. Saraga manual section files store `start`, annotation level, and **duration** in their first three columns; the builder converts duration to an end time and clamps it to the track metadata length.

## Form decisions

Inclusion is allowlisted to forms that denote fixed sahitya. Empty/unknown forms, Saraga `Pallavi` (Rāgam–Tānam–Pallavi), and Thillana are excluded.

| Decision | Form | Tracks |
|---|---|---:|
| kept | Kriti | 140 |
| kept | Mangalam | 10 |
| kept | Varnam - Tana Varnam | 9 |
| kept | Viruttham | 5 |
| kept | Shloka | 4 |
| kept | Bhajan | 1 |
| kept | Javali | 1 |
| kept | Keertana (Devara nama) | 1 |
| kept | Thiruppavai | 1 |
| kept | Thiruppugazh | 1 |
| excluded | (none) | 67 |
| excluded | Thillana | 6 |
| excluded | Pallavi | 3 |

## Match resolution

| Resolution | Tracks |
|---|---:|
| unique exact title+raga+lyrics | 78 |

## Skipped manual section labels

Instrumental/improvised labels are intentionally not assigned lyric text. A core lyric label can also be skipped when the selected local page does not contain that section.

| Reason | Label | Spans |
|---|---|---:|
| non-core / non-lyrical | vocal_alap | 13 |
| non-core / non-lyrical | violin_alap | 8 |
| non-core / non-lyrical | kalpana_svaram | 7 |
| non-core / non-lyrical | nereval | 4 |
| non-core / non-lyrical | mukthayi_svara | 3 |
| non-core / non-lyrical | chittai_svaram | 2 |
| non-core / non-lyrical | tani_avartana | 2 |
| non-core / non-lyrical | chittai_svara | 1 |
| non-core / non-lyrical | kalpana_svara | 1 |
| non-core / non-lyrical | mukthayi_svaram | 1 |
| non-core / non-lyrical | tani_avartanam | 1 |
| lyric section absent | charanam | 1 |

## Unmatched fixed-sahitya tracks

Tracks with manual section annotations are listed first because filling their registry/lyric gaps can immediately create training segments. All other unmatched kept tracks follow, so every skipped lyrical track is accounted for.

| Priority | Track | Form | Raga | Work/title tried | Duration min | Reason |
|---|---|---|---|---|---:|---|
| manual sections | saraga1.5_carnatic/Live at Vani Mahal by Sanjay Subrahmanyan/Sarasadalanayana/Sanjay Subrahmanyan - Sarasadalanayana.json | Kriti | Kamās | Sarasadala Nayana | 46.08 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| manual sections | saraga1.5_carnatic/Live at Kamarajar Hall by Sanjay Subrahmanyan/Entara Nitana/Sanjay Subrahmanyan - Entara Nitana.json | Kriti | Harikāmbhōji | Entara Neetana | 43.82 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| manual sections | saraga1.5_carnatic/Ashwath Narayanan at Arkay by Ashwath Narayanan/Aparadhamula/Ashwath Narayanan - Aparadhamula.json | Kriti | Latāngi | Aparadhamulanniyu manninchi; Aparadhamula | 25.40 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| manual sections | saraga1.5_carnatic/Rithvik Raja at Arkay by Rithvik Raja/Chintayama Kanda/Rithvik Raja - Chintayama Kanda.json | Kriti | Bhairavi | chintayama kanda | 19.71 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| manual sections | saraga1.5_carnatic/Sanjay at Sastri Hall by Sanjay Subrahmanyan/Deenarakshaka/Sanjay Subrahmanyan - Deenarakshaka.json | Kriti | Āhiri | Deenarakshaka | 15.37 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| manual sections | saraga1.5_carnatic/Live at Vani Mahal by Sanjay Subrahmanyan/Aru marundu/Sanjay Subrahmanyan - Aru marundu.json | Kriti | Kāṁbhōji | Arumarundhoru; Aru marundu | 14.18 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| manual sections | saraga1.5_carnatic/Sanjay at Sastri Hall by Sanjay Subrahmanyan/Sama geeta priyan/Sanjay Subrahmanyan - Sama geeta priyan.json | Kriti | Gauḷa | Sama Geeta Priyan | 12.42 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| manual sections | saraga1.5_carnatic/Rithvik Raja at Arkay by Rithvik Raja/Seetapati Namanasuna/Rithvik Raja - Seetapati Namanasuna.json | Kriti | Kamās | Sitapate na manasuna; Seetapati Namanasuna | 11.48 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| manual sections | saraga1.5_carnatic/Live at Kamarajar Hall by Sanjay Subrahmanyan/Shatre Vilagi Irum/Sanjay Subrahmanyan - Shatre Vilagi Irum.json | Kriti | Pūrvīkaḷyāṇi | Shatre vilagi irum pillai sannidhanam; Shatre Vilagi Irum | 10.18 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| manual sections | saraga1.5_carnatic/Live at Kamarajar Hall by Sanjay Subrahmanyan/Undan Paada Pankayam/Sanjay Subrahmanyan - Undan Paada Pankayam.json | Varnam - Tana Varnam | Śankarābharaṇaṁ | Undan Paada Pankayam | 8.98 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| manual sections | saraga1.5_carnatic/Live at Vani Mahal by Sanjay Subrahmanyan/Karuvutranaal Mudalaaga/Sanjay Subrahmanyan - Karuvutranaal Mudalaaga.json | Viruttham | Rāgamālika | Karuvutranaal Mudalaaga | 8.13 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| manual sections | saraga1.5_carnatic/Live at Kamarajar Hall by Sanjay Subrahmanyan/Maname Ramanai Paada/Sanjay Subrahmanyan - Maname Ramanai Paada.json | Kriti | Sindhubhairavi | Maname Ramani Paada; Maname Ramanai Paada | 7.53 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| manual sections | saraga1.5_carnatic/Live at Vani Mahal by Sanjay Subrahmanyan/Pullum Silambena Kan/Sanjay Subrahmanyan - Pullum Silambena Kan.json | Kriti | Śankarābharaṇaṁ | Pullum Silambena; Pullum Silambena Kan | 6.05 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| manual sections | saraga1.5_carnatic/Sanjay at Sastri Hall by Sanjay Subrahmanyan/Ninnaiye rathi/Sanjay Subrahmanyan - Ninnaiye rathi.json | Kriti | Bāgēśrī | Ninnaye; Ninnaiye rathi | 6.05 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| manual sections | saraga1.5_carnatic/Live at Vani Mahal by Sanjay Subrahmanyan/Paarengum/Sanjay Subrahmanyan - Paarengum.json | Kriti | Kalyāṇi | Parengum Paarthaalum; Paarengum | 5.85 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| manual sections | saraga1.5_carnatic/Vignesh Ishwar at Nada Inbam by Vignesh Ishwar/Idhuthaano Thillai Sthalam/Vignesh Ishwar - Idhuthaano Thillai Sthalam.json | Kriti | Behāg | Idhu Thaano Thillai Sthalam | 5.64 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| manual sections | saraga1.5_carnatic/Rithvik Raja at Arkay by Rithvik Raja/Karunimpa Idi/Rithvik Raja - Karunimpa Idi.json | Varnam - Tana Varnam | Sahānā | Karunimpa; Karunimpa Idi | 5.15 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| manual sections | saraga1.5_carnatic/Live at Kamarajar Hall by Sanjay Subrahmanyan/Ozhukkam Uyirinum/Sanjay Subrahmanyan - Ozhukkam Uyirinum.json | Kriti | Kuntalavarāḷi | Ozhukkam Uyirinum | 5.13 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| manual sections | saraga1.5_carnatic/Live at Kamarajar Hall by Sanjay Subrahmanyan/Payum Oli Nee Yenakku/Sanjay Subrahmanyan - Payum Oli Nee Yenakku.json | Kriti | Kamās | Payum Oli Nee Enakku; Payum Oli Nee Yenakku | 5.10 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| manual sections | saraga1.5_carnatic/Sanjay at Sastri Hall by Sanjay Subrahmanyan/Innamum Oru thalam/Sanjay Subrahmanyan - Innamum Oru thalam.json | Kriti | Behāg | Innamum Oru Thalam | 5.03 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| manual sections | saraga1.5_carnatic/Rithvik Raja at Arkay by Rithvik Raja/Sapasyat Kausalya/Rithvik Raja - Sapasyat Kausalya.json | Kriti | Jōnpuri | Sapashyat; Sapasyat Kausalya | 4.85 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| manual sections | saraga1.5_carnatic/Ashwath Narayanan at Arkay by Ashwath Narayanan/Marubari/Ashwath Narayanan - Marubari.json | Javali | Kamās | Marubari | 4.52 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| manual sections | saraga1.5_carnatic/Ashwath Narayanan at Arkay by Ashwath Narayanan/Parama Purusham/Ashwath Narayanan - Parama Purusham.json | Kriti | Lalita pancamaṁ | Parama purusham hrudaya; Parama Purusham | 4.45 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| manual sections | saraga1.5_carnatic/Sanjay at Sastri Hall by Sanjay Subrahmanyan/Ganta mani aadudhu/Sanjay Subrahmanyan - Ganta mani aadudhu.json | Kriti | Kānaḍa | Gantamani Aadudhey; Ganta mani aadudhu | 4.05 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| manual sections | saraga1.5_carnatic/Sanjay at Sastri Hall by Sanjay Subrahmanyan/Chalamelara Saketha Rama/Sanjay Subrahmanyan - Chalamelara Saketha Rama.json | Kriti | Mārgahindōḷaṁ | Chalamelara Saketa; Chalamelara Saketha Rama | 3.88 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| manual sections | saraga1.5_carnatic/Sanjay at Sastri Hall by Sanjay Subrahmanyan/Kalilo Hari Smrana/Sanjay Subrahmanyan - Kalilo Hari Smrana.json | Kriti | Kāpi | Kalilo Hari Smaranam; Kalilo Hari Smrana | 2.83 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| manual sections | saraga1.5_carnatic/Live at Kamarajar Hall by Sanjay Subrahmanyan/Teerthakarayinile/Sanjay Subrahmanyan - Teerthakarayinile.json | Viruttham | Kamās | Viruttham; Teerthakarayinile | 1.88 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| manual sections | saraga1.5_carnatic/Sanjay at Sastri Hall by Sanjay Subrahmanyan/Teerthakarayinile/Sanjay Subrahmanyan - Teerthakarayinile.json | Viruttham | (none) | Teertha Karaiyinile; Teerthakarayinile | 1.85 | missing track raga: no raaga name in metadata |
| manual sections | saraga1.5_carnatic/Sanjay at Sastri Hall by Sanjay Subrahmanyan/Uppum karpuramum/Sanjay Subrahmanyan - Uppum karpuramum.json | Viruttham | Kānaḍa | Uppum Karpooramum | 1.53 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| manual sections | saraga1.5_carnatic/Rithvik Raja at Arkay by Rithvik Raja/Ramachandraya Mangalam/Rithvik Raja - Ramachandraya Mangalam.json | Mangalam | Navrōj | Ramachandraya; Ramachandraya Mangalam | 1.51 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| manual sections | saraga1.5_carnatic/Vignesh Ishwar at Nada Inbam by Vignesh Ishwar/Niraimadi Mugam Thiruppugazh/Vignesh Ishwar - Niraimadi Mugam Thiruppugazh.json | Thiruppugazh | Haṁsānandi | Niraimadimugam(Thirupugazh); Niraimadi Mugam Thiruppugazh | 1.42 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| manual sections | saraga1.5_carnatic/Vignesh Ishwar at Nada Inbam by Vignesh Ishwar/Pavamana Suthudu Mangalam/Vignesh Ishwar - Pavamana Suthudu Mangalam.json | Mangalam | Saurāṣtraṁ | Pavamana Suthudu; Pavamana Suthudu Mangalam | 1.30 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| manual sections | saraga1.5_carnatic/Sanjay at Sastri Hall by Sanjay Subrahmanyan/Mangalam/Sanjay Subrahmanyan - Mangalam.json | Mangalam | Saurāṣtraṁ | Pavamana Suthudu; Mangalam | 1.03 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| manual sections | saraga1.5_carnatic/Sanjay at Sastri Hall by Sanjay Subrahmanyan/Oorilen Kaani Illai/Sanjay Subrahmanyan - Oorilen Kaani Illai.json | Viruttham | Behāg | Oorilen Kaani Illai | 0.80 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| manual sections | saraga1.5_carnatic/Live at Kamarajar Hall by Sanjay Subrahmanyan/Pavamana Suthudu/Sanjay Subrahmanyan - Pavamana Suthudu.json | Mangalam | Saurāṣtraṁ | Pavamana Suthudu | 0.77 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| manual sections | saraga1.5_carnatic/Live at Vani Mahal by Sanjay Subrahmanyan/Pavamaana Suthudu Pattu/Sanjay Subrahmanyan - Pavamaana Suthudu Pattu.json | Kriti | Saurāṣtraṁ | Pavamana Suthudu; Pavamaana Suthudu Pattu | 0.70 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Dr S Sundar at Arkay by S Sundar/Geetha Vaadya Natana/Geetha Vaadya Natana.json | Kriti | Nāṭakapriya | Geetha Vaadya Natana | 49.35 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Chaitra Sairam at Arkay by Chaitra Sairam/Shri Subramanyaya Namaste/Chaitra Sairam - Shri Subramanyaya Namaste.json | Kriti | Kāṁbhōji | Shri subrahmanyaya namaste manasija koti lavanya; Shri Subramanyaya Namaste | 42.95 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/KP Nandini at Arkay by KP Nandini/Janakipathe Jaya Karunya Jaladhe/Janakipathe Jaya Karunya Jaladhe.json | Kriti | Karaharapriya | Janakipathe Jaya; Janakipathe Jaya Karunya Jaladhe | 42.37 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Vasundara Rajagopal at Arkay by Vasundara Rajagopal/Shlokham/Shlokham.json | Shloka | (none) | Malmaruga Shanmukha; Shlokham | 39.28 | missing track raga: no raaga name in metadata |
| no sections | saraga1.5_carnatic/Kuldeep Pai at Arkay by Kuldeep Pai/Thappi Bratikipova/Thappi Bratikipova.json | Kriti | Tōḍi | Thappi Bratikipova | 37.26 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Srividya Janakiraman at Arkay by Srividya Janakiraman/Gnanamosaga Rada/Gnanamosaga Rada.json | Kriti | Gamakakriyā | Gnanamosaga Rada | 28.87 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Dr S Sundar at Arkay by S Sundar/Sudhaamayee/Sudhaamayee.json | Kriti | Amṛtavarṣiṇi | Sudhamayi | 26.70 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Kuldeep Pai at Arkay by Kuldeep Pai/Arul Seya Vendum Ayya/Arul Seya Vendum Ayya.json | Kriti | Rasikapriya | Arul Seiya Vendum Ayya; Arul Seya Vendum Ayya | 26.50 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Mahati at Arkay by Mahati/Hiranmayeem/Hiranmayeem.json | Kriti | Lalita | Hiranmayi; Hiranmayeem | 24.90 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Modhumudi Sudhakar at Arkay by Modhumudi Sudhakar/Paramatmudu/Paramatmudu.json | Kriti | Vāgadīśvari | Paramathmudu | 14.88 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Modhumudi Sudhakar at Arkay by Modhumudi Sudhakar/Dudukugala/Dudukugala.json | Kriti | Gauḷa | Duduku Gala | 13.36 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Dr S Sundar at Arkay by S Sundar/Paahi Maam Sri/Paahi Maam Sri.json | Kriti | Janaranjani | Paahi Maam Sri | 13.23 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Kuldeep Pai at Arkay by Kuldeep Pai/Kaalaharanamelara/Kaalaharanamelara.json | Kriti | Śuddadhanyāsi | Kalaharanamelara | 13.23 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Kanakadurga Venkatesh at Arkay by Kanakadurga Venkatesh/Rama Neepai/Rama Neepai.json | Kriti | Kedāraṁ | Rama Neepai | 12.89 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Akkarai Sisters at Arkay by Akkarai Sisters/Siddhi Vinayakam/Siddhi Vinayakam.json | Kriti | Ṣanmukhapriya | Siddhi Vinayakam | 12.58 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Cherthala Ranganatha Sharma at Arkay by Cherthala Ranganatha Sharma/Velum Mayilume/Velum Mayilume.json | Kriti | Sucaritra | Velum Mayilume | 12.23 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Chaitra Sairam at Arkay by Chaitra Sairam/Kamalamba Samrakshatu/Chaitra Sairam - Kamalamba Samrakshatu.json | Kriti | Ānandabhairavi | Kamalamba; Kamalamba Samrakshatu | 11.05 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Cherthala Ranganatha Sharma at Arkay by Cherthala Ranganatha Sharma/Varashiki Vahana/Varashiki Vahana.json | Kriti | (none) | Varashiki Vahana | 9.08 | missing track raga: no raaga name in metadata |
| no sections | saraga1.5_carnatic/Akkarai Sisters at Arkay by Akkarai Sisters/Koti Janmani/Koti Janmani.json | Kriti | Rītigauḷa | Koti Janmani | 8.78 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Mahati at Arkay by Mahati/Gopi Gopala Bala/Gopi Gopala Bala.json | Bhajan | (none) | Gopi Gopala Bala | 7.97 | missing track raga: no raaga name in metadata |
| no sections | saraga1.5_carnatic/Dr S Sundar at Arkay by S Sundar/Eppadi Manam Thunindhadho/Eppadi Manam Thunindhadho.json | Kriti | Hussēnī | Eppadi Manam; Eppadi Manam Thunindhadho | 7.70 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Kanakadurga Venkatesh at Arkay by Kanakadurga Venkatesh/Enthavedukonthu Raghava/Enthavedukonthu Raghava.json | Kriti | Sarasvatī manōhari | Entha Vedukondu Raghava; Enthavedukonthu Raghava | 7.58 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Modhumudi Sudhakar at Arkay by Modhumudi Sudhakar/Entha Muddo/Entha Muddo.json | Kriti | (none) | Enta Muddu; Entha Muddo | 7.36 | missing track raga: no raaga name in metadata |
| no sections | saraga1.5_carnatic/Mahati at Arkay by Mahati/Vandu Ketpaar Illayo/Vandu Ketpaar Illayo.json | Kriti | Rāgamālika | Vandu Ketpaar Illayo | 7.03 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Chaitra Sairam at Arkay by Chaitra Sairam/Rakta Ganapatim/Chaitra Sairam - Rakta Ganapatim.json | Kriti | Mōhanaṁ | Rakta Ganapatim | 7.00 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Chaitra Sairam at Arkay by Chaitra Sairam/Anandaamrutakarshini/Chaitra Sairam - Anandaamrutakarshini.json | Kriti | Amṛtavarṣiṇi | Anandamruta Karshini | 6.80 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Dr S Sundar at Arkay by S Sundar/Enadhu Manam Kavalai/Enadhu Manam Kavalai.json | Kriti | Harikāmbhōji | Enadu Manam; Enadhu Manam Kavalai | 6.57 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Akkarai Sisters at Arkay by Akkarai Sisters/Geeta Nayakan/Geeta Nayakan.json | Kriti | Rāgamālika | Geeta Nayakan | 6.28 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Dr S Sundar at Arkay by S Sundar/Kannanai Paadu Maname/Kannanai Paadu Maname.json | Kriti | Kalyāṇi | Kannanai Padu Maname | 6.20 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Dr S Sundar at Arkay by S Sundar/Nera Nammiti/Nera Nammiti.json | Kriti | Rāgamālika | Nere nambide ninna charana; Nera Nammiti | 5.95 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Cherthala Ranganatha Sharma at Arkay by Cherthala Ranganatha Sharma/Idhu Thaano Thillai Sthalam/Idhu Thaano Thillai Sthalam.json | Kriti | Behāg | Idhu Thaano Thillai Sthalam | 5.70 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Vasundara Rajagopal at Arkay by Vasundara Rajagopal/Ni Ninaindhal Aagadhadhu/Ni Ninaindhal Aagadhadhu.json | Kriti | Jōnpuri | Nee Ninaindal; Ni Ninaindhal Aagadhadhu | 5.68 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Dr S Sundar at Arkay by S Sundar/Vanajaksha Ninne Nammiti/Vanajaksha Ninne Nammiti.json | Varnam - Tana Varnam | Behāg | Vanajaksha Ninne Nammitti; Vanajaksha Ninne Nammiti | 5.65 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Akkarai Sisters at Arkay by Akkarai Sisters/Karunimpa Idi/Karunimpa Idi.json | Varnam - Tana Varnam | Sahānā | Karunimpa; Karunimpa Idi | 5.63 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Srividya Janakiraman at Arkay by Srividya Janakiraman/Santhamu leka Sowkyamu ledu/Santhamu leka Sowkyamu ledu.json | Kriti | Sāma | Santhamu leka Sowkyamu ledu | 5.35 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Mahati at Arkay by Mahati/Chinnanchiru Kiliye/Chinnanchiru Kiliye.json | Kriti | Rāgamālika | Chinnajirukiliye Kannama; Chinnanchiru Kiliye | 5.27 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Modhumudi Sudhakar at Arkay by Modhumudi Sudhakar/Edari Sancharintura/Edari Sancharintura.json | Kriti | (none) | E Dari Sancharintura | 5.18 | missing track raga: no raaga name in metadata |
| no sections | saraga1.5_carnatic/Srividya Janakiraman at Arkay by Srividya Janakiraman/Sri Dundurge Siva Samsaare/Sri Dundurge Siva Samsaare.json | Kriti | Śrīranjani | Sri Dundurge Siva Samsaare | 5.08 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Modhumudi Sudhakar at Arkay by Modhumudi Sudhakar/Koluvaiyunnade/Koluvaiyunnade.json | Kriti | Dēvagāndhāri | Koluvaiyunnade | 5.04 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Sumithra Vasudev at Arkay by Sumithra Vasudev/Aaniraimekkani/Aaniraimekkani.json | Kriti | Rāgamālika | Aaniraimekkani (Viruttham); Aaniraimekkani | 4.79 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Dr S Sundar at Arkay by S Sundar/Shloka Namaste Sarvalokaanam/Shloka Namaste Sarvalokaanam.json | Shloka | (none) | Namaste Sarvalokaanam; Shloka Namaste Sarvalokaanam | 4.75 | missing track raga: no raaga name in metadata |
| no sections | saraga1.5_carnatic/Sumithra Vasudev at Arkay by Sumithra Vasudev/Thoomani Madatthu/Thoomani Madatthu.json | Thiruppavai | Hamīr kaḷyaṇi | Thoomani Madatthu | 4.53 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Dr S Sundar at Arkay by S Sundar/Parvathi Ninnu Neranammiti/Parvathi Ninnu Neranammiti.json | Kriti | Kalgaḍa | Parvathi Ninnu; Parvathi Ninnu Neranammiti | 4.52 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Srividya Janakiraman at Arkay by Srividya Janakiraman/Parvathi Ninu Ne Nera Nammithi/Parvathi Ninu Ne Nera Nammithi.json | Kriti | Kalgaḍa | Parvathi Ninnu; Parvathi Ninu Ne Nera Nammithi | 4.33 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Kuldeep Pai at Arkay by Kuldeep Pai/Gange Maam Pahi/Gange Maam Pahi.json | Kriti | (none) | Gange Mampahi | 4.15 | missing track raga: no raaga name in metadata |
| no sections | saraga1.5_carnatic/Chaitra Sairam at Arkay by Chaitra Sairam/Ardhanareeshwaram/Chaitra Sairam - Ardhanareeshwaram.json | Kriti | (none) | Ardhanarishwaram | 3.97 | missing track raga: no raaga name in metadata |
| no sections | saraga1.5_carnatic/Sumithra Vasudev at Arkay by Sumithra Vasudev/Va Va Brindavana/Va Va Brindavana.json | Kriti | Sindhubhairavi | Va Va Brindavana | 3.71 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Srividya Janakiraman at Arkay by Srividya Janakiraman/Nenindal Agaadadu undo/Nenindal Agaadadu undo.json | Kriti | Jōnpuri | Nee Ninaindal; Nenindal Agaadadu undo | 3.50 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Modhumudi Sudhakar at Arkay by Modhumudi Sudhakar/Rama Namam Bhajare/Rama Namam Bhajare.json | Kriti | Madhyamāvati | Rama Namam Bhajare | 3.48 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Modhumudi Sudhakar at Arkay by Modhumudi Sudhakar/Giriraja Suta/Giriraja Suta.json | Kriti | (none) | Giriraja suta tanaya sadaya; Giriraja Suta | 3.13 | missing track raga: no raaga name in metadata |
| no sections | saraga1.5_carnatic/Chaitra Sairam at Arkay by Chaitra Sairam/Gange Maampahi/Chaitra Sairam - Gange Maampahi.json | Kriti | (none) | Gange Mampahi | 2.70 | missing track raga: no raaga name in metadata |
| no sections | saraga1.5_carnatic/Dr S Sundar at Arkay by S Sundar/Devadi Devanukku Jaya Mangalam/Devadi Devanukku Jaya Mangalam.json | Mangalam | Suraṭi | Devadidevanukku Mangalam; Devadi Devanukku Jaya Mangalam | 2.10 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Modhumudi Sudhakar at Arkay by Modhumudi Sudhakar/Mangalam Avanisutanatha/Mangalam Avanisutanatha.json | Mangalam | Nādanāmakriya | Avani suta natha; Mangalam Avanisutanatha | 2.05 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Cherthala Ranganatha Sharma at Arkay by Cherthala Ranganatha Sharma/Shlokam - Shivah Shaktyayukto/Shlokam - Shivah Shaktyayukto.json | Shloka | Madhyamāvati | Shlokam - Shivah Shaktyayukto | 1.53 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Akkarai Sisters at Arkay by Akkarai Sisters/Pavamana Suthudu Mangalam/Pavamana Suthudu Mangalam.json | Mangalam | Saurāṣtraṁ | Pavamana Suthudu; Pavamana Suthudu Mangalam | 1.42 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Vasundara Rajagopal at Arkay by Vasundara Rajagopal/Avani Sutha/Avani Sutha.json | Mangalam | Nādanāmakriya | Avani suta natha; Avani Sutha | 1.42 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Mahati at Arkay by Mahati/Pavamana Suttudu Pattu/Pavamana Suttudu Pattu.json | Mangalam | Saurāṣtraṁ | Pavamana Suthudu; Pavamana Suttudu Pattu | 1.33 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
| no sections | saraga1.5_carnatic/Kuldeep Pai at Arkay by Kuldeep Pai/Vasudeva Sutam Devam/Vasudeva Sutam Devam.json | Shloka | (none) | Vasudeva Sutam Devam | 1.31 | missing track raga: no raaga name in metadata |
| no sections | saraga1.5_carnatic/Sumithra Vasudev at Arkay by Sumithra Vasudev/Mangalam Kosalendraya/Mangalam Kosalendraya.json | Mangalam | Suraṭi | Kosalendraya; Mangalam Kosalendraya | 0.51 | no unambiguous linked lyrics: title+raga matched, but no single usable local lyric page |
