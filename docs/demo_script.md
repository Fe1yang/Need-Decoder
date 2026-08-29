# Demo recording script

The required video can be a terminal walkthrough because Track 4 is a backend/NLP challenge. Aim for
about two and a half minutes. Record at 1080p, keep the terminal text large, and do not add copyrighted
music, product images, or third-party logos.

## Before recording

```bash
python3 -m unittest discover -s tests -v
python3 demo.py --scenario hidden-needs
python3 demo.py --scenario intent-override
```

Clear the terminal, open the GitHub README in a second window, and close any tab or notification that
could expose personal information.

## Suggested walkthrough

| Time | Screen | Narration |
| --- | --- | --- |
| 0:00–0:20 | Project name and README | Hi, I'm Yu Feiyang, and this is Need Decoder. Shopping search usually expects people to know the right keywords. My project starts from the situation the customer describes and makes the missing requirements visible. |
| 0:20–0:45 | README architecture section | The agent keeps explicit requirements separate from inferred needs. It routes the session as Buying or Browsing, searches a 50,000-product catalog with SQLite FTS5, and reranks the results offline. It uses no API key or hosted model. |
| 0:45–1:25 | Run `python3 demo.py --scenario hidden-needs` | Here the customer asks for walking shoes for a company retreat. Need Decoder infers comfort and durability from extended wear, and a professional style from the setting. When outdoor activities and dinner are added, it also considers grip, weather resistance, and versatility. Every inference shows its confidence and evidence. |
| 1:25–1:55 | Run `python3 demo.py --scenario intent-override` | The second example starts with leather. The customer then changes direction and asks for breathable mesh. The old preference is removed, the new one is stored, and the clarification plan is reopened instead of forcing the customer to repeat everything. |
| 1:55–2:20 | README results table | On the 200 public development sessions, the final agent reaches 99 percent Hit Rate at 10, 0.610 MRR, and 2.06 mean turns to conversion. The official BM25 starter reaches 12.5 percent Hit Rate at 10. |
| 2:20–2:40 | Evaluation notes or repository layout | The whole run costs zero model tokens and takes about 30 to 35 seconds. The main limitation is that hidden-need inference uses a small auditable rule set. A production version should compare it with a calibrated semantic model while keeping explicit customer requirements in control. |
| 2:40–2:50 | Project name | Need Decoder helps customers search with the situation they understand, instead of the catalog vocabulary they may not know. Thank you. |

## Upload settings

- Upload to YouTube.
- Set visibility to **Public**, not Unlisted or Private.
- Suggested title: `Need Decoder — TikTok TechJam 2026 Track 4 Demo`
- Put the public GitHub URL in the description.
- Paste the YouTube URL into the Devpost submission before submitting.
