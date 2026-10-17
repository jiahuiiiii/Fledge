# Research supporting Thesis sentiment analysis

9 October 2026. Current pitch approach: use published research to explain the rationale for sentiment analysis. The owner deferred running the proposed experiment for now. This material supports the method's motivation; it supplies no measured Thesis accuracy, investment return or user benefit.

## Three papers for the main slide

| Part of Thesis | Research and finding | Connection to our approach |
| --- | --- | --- |
| Company news | Tetlock, Saar-Tsechansky and Macskassy (2008), *More Than Words: Quantifying Language to Measure Firms' Fundamentals*, Journal of Finance 63, 1437–1467. Negative language in company news forecast weaker earnings and related to brief price underreaction, particularly in stories about fundamentals. [Author institution](https://business.columbia.edu/faculty/research/more-words-quantifying-language-measure-firms-fundamentals) | Financial language can contain information worth extracting alongside numerical company data. This study used quantitative text measures, not Thesis's model or prompt. |
| Investor discussion | Chen, De, Hu and Hwang (2014), *Wisdom of Crowds: The Value of Stock Opinions Transmitted Through Social Media*, Review of Financial Studies 27, 1367–1403. Opinions in investment articles and reader comments predicted subsequent returns and earnings surprises in the studied community. [Publisher abstract](https://academic.oup.com/rfs/article-abstract/27/5/1367/1581938) | Supports examining investor discussion as an additional information source. Results from that community do not establish equivalent performance on Reddit or Hacker News. |
| Language model analysis | Lopez-Lira and Tang (2026), *Can ChatGPT Forecast Stock Price Movements? Return Predictability and Large Language Models*, Journal of Financial Economics 184, 104335. Assessments of post-training-cutoff headlines predicted market reactions and subsequent drift, with stronger effects for smaller stocks and negative news. [Publisher](https://www.sciencedirect.com/science/article/pii/S0304405X26001066), [full author version revised in 2025](https://arxiv.org/html/2304.07619v6) | Supports using an LLM to extract financial meaning from news. Its price-impact task differs from Thesis's source-tone task; the result does not validate our exact pipeline. |

These connections are an application of the research to Thesis's design, not findings made by the papers about Thesis. Published evidence supports the relevance of the inputs and the plausibility of the analysis approach. It does not guarantee an investment advantage.

## Slide copy

### A research backed approach to reading financial sentiment

- **News contains useful signals.** Research links company-specific news language with subsequent earnings and market reactions. [Tetlock et al., 2008](https://business.columbia.edu/faculty/research/more-words-quantifying-language-measure-firms-fundamentals)
- **Investor discussion can add information.** Research finds predictive information in investment articles and reader comments. [Chen et al., 2014](https://academic.oup.com/rfs/article-abstract/27/5/1367/1581938)
- **Language models can interpret financial news.** Research demonstrates predictive information in LLM assessments of headlines. [Lopez-Lira and Tang, 2026](https://www.sciencedirect.com/science/article/pii/S0304405X26001066)

Thesis builds on this research to organise company-specific sentiment from news and discussion, with inspectable source evidence.

Footer: Published findings support the approach. Thesis-specific effectiveness has not yet been independently validated.

## Speaker note

Our premise has empirical support: company news and investor opinions can contain financially relevant information, and language models can help interpret it. Thesis brings these ideas into a research workflow where users can inspect the original evidence. We have not yet measured our own predictive performance or user benefit.

## Additional method reference for the appendix

[Tang et al. (2023), *FinEntity: Entity-level Sentiment Classification for Financial Texts*, EMNLP](https://aclanthology.org/2023.emnlp-main.956/) provides company/entity-level financial sentiment annotations and model benchmarks. It is particularly relevant to judging the attitude toward the researched company when a text mentions several companies. Its positive/neutral/negative task does not independently validate Thesis's mixed/unclear handling, evidence guards or five-group threshold.

### Aspect- and entity-level references (checked 16 October 2026)

Followed up from a vendor round-up ([AIMultiple, updated June 2026](https://aimultiple.com/open-source-sentiment-analysis)). That article reports no accuracy figures, so it is not itself cited. Only the primary sources below were read. Nothing was downloaded or run.

| Reference | What it offers Thesis | Limitations found |
| --- | --- | --- |
| [SEntFiN 1.0](https://arxiv.org/abs/2305.12257) — Sinha, Kedas, Kumar and Malo, *Journal of the Association for Information Science and Technology* (2023) | 10,753 human-annotated financial news headlines with sentiment labelled per entity. 2,847 headlines name several entities, often with conflicting sentiment. Directly relevant to the Meta-versus-Microsoft attribution error in the [local model comparison](local-sentiment-models.md). The authors report about 94% accuracy for RoBERTa/FinBERT on their own dataset. | Headlines only, no Reddit/HN discussion. Positive/neutral/negative only, with no mixed or unclear label. Dataset licence and download terms not yet checked. Its accuracy figure is on SEntFiN, not Thesis sources. |
| [Arctic-ABSA](https://arxiv.org/abs/2601.03940) — Liskowski and Jankowski (Snowflake), arXiv preprint, January 2026 | Aspect-based sentiment with five labels: positive, negative, neutral, mixed and unknown. This is close to Thesis's mixed/unclear handling. Training data (ABSA-mix: 17 public datasets, 92 domains) includes SEntFiN and a Twitter set. Its 8B model reports 93.0% accuracy on ABSA-mix, against 83.7% for Claude 3.5 Sonnet and 82.2% for GPT-4o. | Not peer-reviewed. "Mixed" mostly comes from merging conflicting duplicate labels and from synthetic data. "Unknown" means the aspect is absent from the text, not unclear sentiment. No model weights or code release found. ABSA-mix is described as released, but no link or licence is given. Aspects are free-form (e.g. "battery life"), and company targets are not evaluated. The authors note neutral versus weak-polarity labelling is inconsistent and long texts are untested. The comparison models predate the current OpenAI profile. |
| [AnnoABSA](https://arxiv.org/abs/2603.01773) — Hellwig, Fehle, Kruschwitz and Wolff, LREC 2026 ([code](https://github.com/NilsHellwig/AnnoABSA), MIT licence) | Local web tool for annotating aspect sentiment. Polarity and category lists are configurable, so mixed/unclear labels and company targets could be defined. Optional LLM suggestions (OpenAI or local Ollama) are off by default. JSON/CSV input. A possible tool for building the independently labelled sample that the local model comparison recommends. | No inter-annotator agreement features. In its eight-person user study, suggestions cut annotation time by 30.5%, but only on restaurant reviews. Suggestion quality was only tested with Gemma-3-27B. Using OpenAI suggestions would send source text to OpenAI and draw on the same API ledger, and would make the labels less independent. Suggestions should stay off for any independent evaluation sample. |

SEntFiN is the strongest addition for the appendix, alongside FinEntity. Arctic-ABSA can be mentioned as recent supporting work on explicit mixed/unknown labels, not as a validated or available model. AnnoABSA is evaluation tooling, not a slide citation.

## Claims to keep separate

“Research-backed approach” describes the evidence above. “Thesis predicts stock prices accurately,” “Thesis improves returns,” “Thesis saves research time” and a numerical accuracy claim require our own suitable evaluation. The approximately 90% result in the LLM paper concerns portfolio-days for the non-tradable initial reaction; do not present it as individual-stock prediction accuracy or a Thesis metric.

Thesis's differentiation is a product proposition: connecting news and discussion readings to inspectable evidence and saved company research. These citations do not establish product uniqueness, commercial demand or a proprietary scientific discovery. The existing developer-reference checks remain engineering evidence with their recorded limitations.

The earlier [experiment protocol](sentiment-effectiveness-study.md) remains available for future validation. No experiment, paid Thesis model run, source acquisition, watch activation or pitch-deck file edit accompanies this literature-based change.
