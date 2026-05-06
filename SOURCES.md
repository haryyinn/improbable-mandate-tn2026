# Credible Data Sources for TN 2026 Election Analysis
**No Wikipedia. No secondary aggregators. Only primary, citable sources suitable for an IIM-grade research paper.**

---

## 1. Election Commission of India (Primary Source)

### 1.1 ECI Statistical Reports — Historical Election Results
Direct PDF downloads of constituency-wise results published by the ECI itself.

| Year | Direct URL |
|---|---|
| 2021 TN | https://eci.gov.in/files/file/13145-tamil-nadu-2021/ |
| 2016 TN | https://eci.gov.in/files/file/4124-tamil-nadu-2016/ |
| 2011 TN | https://eci.gov.in/files/file/4123-tamil-nadu-2011/ |
| 2006 TN | https://eci.gov.in/files/file/4122-tamil-nadu-2006/ |
| 2001 TN | https://eci.gov.in/files/file/4121-tamil-nadu-2001/ |

If the direct links don't load, navigate via:
- **Browse all reports:** https://eci.gov.in/statistical-report/statistical-reports/
- Filter dropdown: "State Legislative Assembly Election" → "Tamil Nadu"

### 1.2 ECI 2026 Results
- **Main page:** https://results.eci.gov.in/
- **Archive (after data freezes):** https://eci.gov.in/election/elections/

### 1.3 ECI Electoral Roll Statistics (for SIR data)
- **Electoral roll pages:** https://eci.gov.in/electoral-rolls/electoral-roll-statistics/
- **ECI Annual Report (contains aggregated SSR/SIR stats):** https://eci.gov.in/eci-publications/

---

## 2. Chief Electoral Officer, Tamil Nadu

If `elections.tn.gov.in` doesn't load, try the alternate CEO data portal:
- **CEO TN press releases:** https://ceotamilnadu.nic.in/
- **Voter services portal (NVSP):** https://www.nvsp.in/

---

## 3. Academic & Think-Tank Sources

### 3.1 Lokniti — CSDS (Centre for the Study of Developing Societies)
The single most credible source for Indian post-poll surveys.
- **Main:** https://www.lokniti.org/
- **TN 2021 Post-Poll Survey:** https://www.lokniti.org/post-poll-2021-tamil-nadu
- They publish age-wise, caste-wise, gender-wise vote breakdowns

### 3.2 Trivedi Centre for Political Data (TCPD), Ashoka University
- **TCPD main site:** https://tcpd.ashoka.edu.in/
- **Lok Dhaba (data portal):** https://lokdhaba.ashoka.edu.in/
  *(If site loads slow, try a direct mirror or contact tcpd@ashoka.edu.in)*

### 3.3 Association for Democratic Reforms (ADR)
Candidate affidavits, asset declarations, criminal cases — all primary data.
- **ADR main:** https://adrindia.org/
- **MyNeta (candidate-level):** https://myneta.info/
- **TN 2021 candidate analysis:** https://adrindia.org/content/tamil-nadu-elections-2021

### 3.4 PRS Legislative Research
- **Tamil Nadu page:** https://prsindia.org/state/tamil-nadu

### 3.5 Economic & Political Weekly (EPW)
Most respected Indian academic journal for political analysis.
- **TN elections tag:** https://www.epw.in/tags/tamil-nadu-elections
- **Search:** https://www.epw.in/search/google?keys=Tamil+Nadu+elections

### 3.6 The Hindu Centre for Politics & Public Policy
- **Main:** https://www.thehinducentre.com/
- Publishes long-form election analyses by senior journalists

---

## 4. Google Scholar — Targeted Search Queries

Copy these into [scholar.google.com](https://scholar.google.com):

```
"Tamil Nadu" elections Dravidian politics
"Tamil Nadu" "voter behaviour" OR "voter behavior"
"Indian elections" "Monte Carlo" forecasting
"AIADMK" "DMK" coalition politics
"caste" "Tamil Nadu" voter
"first-past-the-post" India seat-vote
"electoral volatility" India state elections
"new political parties" India breakthrough
"Vijay" actor politics OR "TVK"
"voter roll" "deletion" India ECI
```

### 4.1 Recommended foundational papers
- **Wyatt, A. (2015).** *Combining clientelist and programmatic politics in Tamil Nadu.* Commonwealth & Comparative Politics, 51(1).
- **Subramanian, N. (1999).** *Ethnicity and Populist Mobilisation: Political Parties, Citizens and Democracy in South India.* Oxford University Press.
- **Vaishnav, M. (2017).** *When Crime Pays: Money and Muscle in Indian Politics.* Yale University Press.
- **Chhibber, P. & Verma, R. (2018).** *Ideology and Identity: The Changing Party Systems of India.* Oxford University Press.
- **Banerjee, A. & Pande, R. (2007).** *Parochial Politics: Ethnic Preferences and Politician Corruption.* NBER Working Paper 12381.
- **Stokes et al. (2013).** *Brokers, Voters, and Clientelism.* Cambridge University Press.

---

## 5. SSRN (Free Working Papers)

- **Main:** https://www.ssrn.com/
- **India Politics network:** https://www.ssrn.com/index.cfm/en/india-political-economy/

Search terms:
- "Tamil Nadu elections"
- "Indian state elections"
- "Dravidian politics"

---

## 6. NBER Working Papers (Free)

- **Main:** https://www.nber.org/papers
- Search: https://www.nber.org/papers?q=India+elections

---

## 7. News Archives (For pre-election signals & event timeline)

### Mainstream English
- **The Hindu archive:** https://www.thehindu.com/elections/tamil-nadu-assembly/
- **Indian Express archive:** https://indianexpress.com/about/tamil-nadu-elections/
- **Frontline (in-depth):** https://frontline.thehindu.com/

### Tamil-language (for cultural/youth signals)
- **Dinamalar:** https://www.dinamalar.com/
- **Dinamani:** https://www.dinamani.com/

### Election-specific reporting
- **Scroll.in:** https://scroll.in/topic/tamil-nadu-elections
- **The Wire:** https://thewire.in/category/politics

---

## 8. IIMK Library Resources (Free Through Your Login)

Through the IIMK library portal, you have free access to:
- **JSTOR:** https://www.jstor.org/
- **EBSCOhost** (political science database)
- **ProQuest Central**
- **Sage Journals** (political research)
- **Cambridge Core** (political studies)
- **Web of Science / Scopus** (citation analysis)

Login via: https://library.iimk.ac.in/

---

## 9. Data Format Tips

- **PDFs from ECI:** Use `tabula-py` to extract tables — `pip install tabula-py` (requires Java)
- **Excel from ECI:** Direct `pandas.read_excel()` works
- **For interview/qualitative data:** CSDS Lokniti publishes survey microdata on request — email them

---

## 10. Direct Replacement Files for This Project

Once you obtain real data, save them as:

```
data/raw/tn_results_2001.csv     ← from ECI Statistical Report 2001
data/raw/tn_results_2006.csv     ← from ECI Statistical Report 2006
data/raw/tn_results_2011.csv     ← from ECI Statistical Report 2011
data/raw/tn_results_2016.csv     ← from ECI Statistical Report 2016
data/raw/tn_results_2021.csv     ← from ECI Statistical Report 2021
data/raw/tn2026_constituency_results.csv  ← from results.eci.gov.in
data/raw/tn_sir_2026.csv         ← from ECI Electoral Roll Stats / CEO TN
data/raw/tn_cash_seizures_2026.csv ← from CEO TN press releases / ADR
```

Required columns are documented at the top of each script in `scripts/`.

---

## 11. What to Do If a Site is Genuinely Blocked

Some Indian government sites block international IPs or rate-limit aggressively. If you face this:

1. **Try at different times of day** (late night IST tends to work)
2. **Use IIMK campus network / VPN** — institutional IPs are usually whitelisted
3. **Use the Internet Archive Wayback Machine:** https://web.archive.org/
   - Append the URL to: `https://web.archive.org/web/*/`
4. **Email the institution directly** — TCPD, CSDS, and ADR all respond to academic data requests within 1–2 working days. Mention you're an IIMK student writing a research paper.
