# Source licenses

Checked 2026-11-22. Re-check before each release.

Status: **ok** = can be used and redistributed in course packs (with the listed attribution),
**unclear** = do not import until a maintainer decision is recorded here, **blocked** = do not use.

## Content sources (end up in course packs)

| Source | License | URL | Redistributable? | Attribution requirements | Status |
|---|---|---|---|---|---|
| 한국어기초사전 / krdict (NIKL) — text | CC BY-SA 2.0 KR | https://krdict.korean.go.kr/kor/kboardPolicy/copyRightTermsInfo | Yes, incl. commercial; adaptations must be share-alike | Credit 국립국어원 한국어기초사전 (National Institute of Korean Language, Basic Korean Dictionary) + link + license | ok |
| krdict — multimedia (images, video, pronunciation audio) | Per-file CC settings | same page | Per file only | Per file | blocked (not needed: we generate our own audio) |
| CC-CEDICT | CC BY-SA 4.0 | https://cc-cedict.org/wiki/ | Yes | Credit CC-CEDICT + link + license | ok |
| Tatoeba — sentences | CC BY 2.0 FR (default); some sentences CC0 | https://tatoeba.org/en/terms_of_use (§6.2), https://en.wiki.tatoeba.org/articles/show/faq | Yes | Terms §6.2: reuse "is only allowed if the name of the author is cited" → keep sentence ID (`source_ref`) + author username (`author`) per sentence; also general credit + link to tatoeba.org + license | ok |
| Tatoeba — audio | Per contributor (CC BY, BY-SA, BY-NC, other) | https://en.wiki.tatoeba.org/articles/show/faq | Varies | Username + license per recording | blocked (not planned; NC licenses are incompatible) |
| Make Me a Hanzi | `dictionary.txt`: LGPL-3.0+; `graphics.txt` (stroke data): Arphic Public License | https://github.com/skishore/makemeahanzi/blob/master/COPYING | Yes, but under LGPL / APL, not CC | Keep license texts with the files | unclear (see below; only needed later for stroke order) |
| HSK 2.0 word lists | No open license found; repos are MIT but copy official Hanban/CLEC lists | e.g. https://github.com/glxxyz/hskhsk.com, https://github.com/clem109/hsk-vocabulary | Unclear | — | unclear (see below) |
| HSK 3.0 word lists (GF0025-2021) | Original: PRC Ministry of Education (`版权所有：中华人民共和国教育部`). Derived repos MIT | http://www.moe.gov.cn/jyb_xwfb/gzdt_gzdt/s5987/202103/t20210329_523304.html, https://github.com/ivankra/hsk30 | Unclear | — | unclear (see below) |

## Tools and models (build time only, not shipped in packs)

| Source | License | URL | Redistributable? | Attribution requirements | Status |
|---|---|---|---|---|---|
| MeloTTS (code) | MIT | https://github.com/myshell-ai/MeloTTS | Yes | Keep MIT notice if redistributed (we don't) | ok |
| MeloTTS-Korean / MeloTTS-Chinese (weights) | MIT (model card) | https://huggingface.co/myshell-ai/MeloTTS-Korean, https://huggingface.co/myshell-ai/MeloTTS-Chinese | Yes | None for generated audio | ok |
| ↳ KR BERT `kykim/bert-kor-base` (used by MeloTTS KR) | Apache-2.0 (per upstream repo; HF card has no license tag) | https://github.com/kiyoungkim1/LMkor | Yes | None for generated audio | ok |
| ↳ ZH BERT `hfl/chinese-roberta-wwm-ext-large` | Apache-2.0 | https://huggingface.co/hfl/chinese-roberta-wwm-ext-large | Yes | None for generated audio | ok |
| kiwipiepy + kiwipiepy_model | Apache-2.0 | https://github.com/bab2min/kiwipiepy, https://pypi.org/project/kiwipiepy-model/ | Yes | None for output | ok |
| jieba | MIT | https://github.com/fxsjy/jieba | Yes | None for output | ok |
| pypinyin | MIT | https://github.com/mozillazg/python-pinyin | Yes | None for output | ok |

## Notes

- **krdict Indonesian glosses:** yes. The Open API has `translated=y` + `trans_lang=9` (인도네시아어),
  see https://krdict.korean.go.kr/kor/openApi/openApiInfo. A Korean–Indonesian learner dictionary edition
  exists (https://krdict.korean.go.kr/ind/). The site footer also offers a full dictionary download
  (사전 전체 내려받기). The Open API key is free (email registration); its registration page shows the same
  CC BY-SA 2.0 KR copyright policy, no extra redistribution restriction was found.
- **CC BY-SA 2.0 KR → CC BY-SA 4.0:** BY-SA 2.0 lets adaptations be released under "a later version of this
  License with the same License Elements", so krdict-derived content can go into our CC BY-SA 4.0 packs.
  CC BY 2.0 FR (Tatoeba) has no share-alike, so it can be included in BY-SA 4.0 as long as authors are credited.
- **MeloTTS voice training data** is not documented on the model cards. MIT on the weights is what we rely on.

## Open decisions (maintainer)

1. **HSK lists (2.0 and 3.0).** No list with an explicit open license from the copyright holder.
   All GitHub lists are MIT-labelled copies of official Hanban / MoE documents. Options:
   - a) Use only the HSK *level number* per word as a fact (word → level tag), not ship the list as such,
     with entries/glosses from CC-CEDICT. Lowest risk, still gives HSK ordering.
   - b) Import `ivankra/hsk30` (MIT) and accept the upstream copyright ambiguity.
   - c) Skip HSK; order by frequency from an openly licensed corpus (e.g. Tatoeba cmn token counts) and
     label levels `zh-1…zh-6` instead of `hsk1…`.
2. **Make Me a Hanzi** (later milestone). LGPL / Arphic are not CC licenses. Options: ship stroke data as a
   separate file in the pack under its own license (aggregation, with license texts), or load it in the app
   from a separate, separately-licensed asset. Not needed before stroke-order exercises.
